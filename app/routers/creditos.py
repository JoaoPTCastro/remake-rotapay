"""Reconhecimento explícito de sobras e aplicações de crédito, sem novo dinheiro."""
from decimal import Decimal
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update, func, case
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (CreditoConta, CreditoAplicacao, CreditoAplicacaoEstorno, CreditoReversao,
    Acerto, AcertoItem, Pagamento, PagamentoAplicacao, Pessoa, User, NotaObrigacao, NotaAbatimento, NotaAbatimentoEstorno)
from ..auth import need, confere_senha
from ..audit import audit
from ..cadastros import hoje
from ..creditos_schemas import ReconhecimentoIn, CreditoAplicacaoIn
from ..notas_schemas import DesfazerIn
from ..referencias_financeiras import bloquear_referencia, chave_referencia
from . import pagamentos, notas, acertos

r = APIRouter(prefix="/creditos", tags=["creditos"])
LEITURA = need("admin", "financeiro", "operador", "consulta")
ESCRITA = need("admin", "financeiro")


def _credito(db, cid):
    c = db.get(CreditoConta, cid)
    if not c:
        raise HTTPException(404, "Crédito não encontrado")
    return c


def _cas(db, c):
    try:
        res = db.execute(update(CreditoConta).where(CreditoConta.id == c.id, CreditoConta.version == c.version)
            .values(version=c.version + 1), execution_options={"synchronize_session": False})
    except OperationalError:
        db.rollback()
        raise HTTPException(409, "Crédito em atualização. Recarregue")
    if res.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Crédito alterado em outra sessão. Recarregue")


def _locks(db, c, nota=None):
    a, p = acertos._acerto(db, c.acerto_id), pagamentos._pagamento(db, c.pagamento_id)
    acertos._cas(db, a)
    pagamentos._cas(db, p)
    _cas(db, c)
    if nota is not None:
        notas._cas(db, nota)
    return a, p


def _prova(relacao, body):
    if relacao == "fornecedor" and (not body.fornecedor_confirmou or not body.referencia_confirmacao):
        raise HTTPException(422, "Fornecedor deve ter concordado externamente: informe a confirmação")
    if relacao == "cliente" and (body.fornecedor_confirmou or body.referencia_confirmacao is not None):
        raise HTTPException(422, "Confirmação do fornecedor pertence somente à relação fornecedor")


def _ativo(db, c):
    pagamentos._titular(db, c.pessoa_id, "representante" if c.relacao == "cliente" else "fornecedor")


def _query(db):
    used = db.query(CreditoAplicacao.credito_id.label("cid"), func.sum(CreditoAplicacao.valor).label("usado"))\
        .filter_by(estornada=False).group_by(CreditoAplicacao.credito_id).subquery()
    total = func.coalesce(used.c.usado, 0)
    saldo = func.round(CreditoConta.valor_original - total, 2)
    estado = case((CreditoConta.revertido == True, "revertido"), (saldo == 0, "utilizado"),
        (total > 0, "parcial"), else_="disponivel")
    q = db.query(CreditoConta, total, Pessoa.nome, Acerto.codigo, Pagamento.codigo)\
        .outerjoin(used, used.c.cid == CreditoConta.id).join(Pessoa, Pessoa.id == CreditoConta.pessoa_id)\
        .join(Acerto, Acerto.id == CreditoConta.acerto_id).join(Pagamento, Pagamento.id == CreditoConta.pagamento_id)
    return q, estado


def _out(row):
    c, total, nome, acode, pcode = row
    total = round(float(total), 2)
    saldo = 0.0 if c.revertido else round(c.valor_original - total, 2)
    return {"id": c.id, "codigo": c.codigo, "pessoa_id": c.pessoa_id, "pessoa_nome": nome,
        "relacao": c.relacao, "acerto_id": c.acerto_id, "codigo_acerto": acode,
        "pagamento_id": c.pagamento_id, "codigo_pagamento": pcode, "valor_original": c.valor_original,
        "valor_aplicado": total, "saldo_disponivel": saldo,
        "status": "revertido" if c.revertido else "utilizado" if saldo == 0 else "parcial" if total else "disponivel",
        "data": c.data, "referencia": c.referencia, "observacao": c.observacao,
        "fornecedor_confirmou": c.fornecedor_confirmou, "referencia_confirmacao": c.referencia_confirmacao,
        "chave_idempotencia": c.chave_idempotencia, "created_at": c.created_at}


def _summary(db, cid):
    q, _ = _query(db)
    return _out(q.filter(CreditoConta.id == cid).one())


def _app_out(db, app):
    n = db.get(NotaObrigacao, app.nota_id)
    ab = db.query(NotaAbatimento).filter_by(credito_aplicacao_id=app.id).one()
    e = db.query(CreditoAplicacaoEstorno).filter_by(aplicacao_id=app.id).first()
    return {"id": app.id, "credito_id": app.credito_id, "nota_id": app.nota_id,
        "numero_documento": n.numero_documento, "acerto_id": app.acerto_id, "valor": app.valor, "data": app.data,
        "referencia": app.referencia, "observacao": app.observacao,
        "chave_idempotencia": app.chave_idempotencia, "fornecedor_confirmou": app.fornecedor_confirmou,
        "referencia_confirmacao": app.referencia_confirmacao, "nota_abatimento_id": ab.id,
        "estornada": app.estornada, "created_at": app.created_at,
        "estorno": {"id": e.id, "motivo": e.motivo, "created_by": e.created_by, "created_at": e.created_at} if e else None}


def _origens_query(db, a):
    snapshot = db.query(AcertoItem.pagamento_id.label("pid"),
        (func.min(AcertoItem.saldo_pagamento_snapshot) - func.sum(AcertoItem.valor)).label("sobra"))\
        .filter(AcertoItem.acerto_id == a.id, AcertoItem.pagamento_id.isnot(None)).group_by(AcertoItem.pagamento_id).subquery()
    credits = db.query(CreditoConta.pagamento_id.label("pid"), func.sum(CreditoConta.valor_original).label("total"))\
        .filter_by(acerto_id=a.id, revertido=False).group_by(CreditoConta.pagamento_id).subquery()
    used = db.query(CreditoConta.pagamento_id.label("pid"), func.sum(CreditoConta.valor_original).label("total"))\
        .filter_by(relacao=a.relacao, revertido=False).group_by(CreditoConta.pagamento_id).subquery()
    apps = db.query(PagamentoAplicacao.pagamento_id.label("pid"), func.sum(PagamentoAplicacao.valor).label("total"))\
        .filter_by(relacao=a.relacao, estornada=False).group_by(PagamentoAplicacao.pagamento_id).subquery()
    saldo = func.round(Pagamento.valor - func.coalesce(apps.c.total, 0) - func.coalesce(used.c.total, 0), 2)
    resto = func.round(snapshot.c.sobra - func.coalesce(credits.c.total, 0), 2)
    maximo = case((saldo < resto, saldo), else_=resto)
    q = db.query(Pagamento, snapshot.c.sobra, func.coalesce(credits.c.total, 0), saldo, maximo)\
        .join(snapshot, snapshot.c.pid == Pagamento.id).outerjoin(credits, credits.c.pid == Pagamento.id)\
        .outerjoin(used, used.c.pid == Pagamento.id).outerjoin(apps, apps.c.pid == Pagamento.id)
    return q, maximo


def _origem_out(row):
    p, sobra, ativo, saldo, maximo = row
    return {"pagamento_id": p.id, "codigo_pagamento": p.codigo, "valor_original": p.valor,
        "sobra_snapshot": round(float(sobra), 2), "credito_ativo_origem": round(float(ativo), 2),
        "saldo_pagamento": round(float(saldo), 2), "maximo_reconhecivel": max(round(float(maximo), 2), 0.0)}


@r.get("/recursos-origem")
def recursos_origem(acerto_id: int, offset: int = 0, limit: int = 50, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    a = acertos._acerto(db, acerto_id)
    if a.status != "efetivado":
        raise HTTPException(422, "Crédito exige acerto efetivado")
    q, maximo = _origens_query(db, a)
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    rows = q.filter(Pagamento.cancelado == False, maximo > 0).order_by(Pagamento.id).offset(offset).limit(limit + 1).all()
    return {"acerto_id": a.id, "pessoa_id": a.pessoa_id, "pessoa_nome": db.get(Pessoa, a.pessoa_id).nome,
        "relacao": a.relacao, "data_acerto": a.data, "fontes": [_origem_out(row) for row in rows[:limit]],
        "tem_mais": len(rows) > limit, "offset": offset, "limit": limit}


@r.get("")
def listar(pessoa_id: int | None = None, relacao: str | None = None, status: str | None = None,
           limit: int = 100, offset: int = 0, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    if relacao and relacao not in ("cliente", "fornecedor"):
        raise HTTPException(422, "Relação inválida")
    if status and status not in ("disponivel", "parcial", "utilizado", "revertido"):
        raise HTTPException(422, "Status inválido")
    q, estado = _query(db)
    if pessoa_id:
        q = q.filter(CreditoConta.pessoa_id == pessoa_id)
    if relacao:
        q = q.filter(CreditoConta.relacao == relacao)
    if status:
        q = q.filter(estado == status)
    return [_out(row) for row in q.order_by(CreditoConta.id.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 500))]


@r.post("", status_code=201)
def reconhecer(body: ReconhecimentoIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    old = db.query(CreditoConta).filter_by(chave_idempotencia=body.chave_idempotencia).first()
    if old:
        campos = ("acerto_id", "pagamento_id", "data", "referencia", "observacao", "fornecedor_confirmou")
        if not all(getattr(old, k) == getattr(body, k) for k in campos) or Decimal(str(old.valor_original)) != body.valor or old.referencia_confirmacao != (body.referencia_confirmacao or ""):
            raise HTTPException(409, "Chave de requisição já usada com dados diferentes")
        return _summary(db, old.id)
    a = acertos._acerto(db, body.acerto_id)
    _prova(a.relacao, body)
    ref = bloquear_referencia(db, body.referencia)
    pagamentos._ref_livre(db, ref)
    acertos._cas(db, a)
    p = pagamentos._pagamento(db, body.pagamento_id)
    pagamentos._cas(db, p)
    pagamentos._titular(db, a.pessoa_id, "representante" if a.relacao == "cliente" else "fornecedor")
    if a.status != "efetivado" or p.cancelado or body.data < max(a.data, p.data) or body.data > hoje():
        db.rollback()
        raise HTTPException(422, "Origem deve estar efetivada e datas devem ser compatíveis")
    q, _ = _origens_query(db, a)
    row = q.filter(Pagamento.id == p.id).first()
    if row is None or body.valor > Decimal(str(_origem_out(row)["maximo_reconhecivel"])):
        db.rollback()
        raise HTTPException(422, "Valor excede a sobra fotografada ou a disponibilidade atual da fonte")
    c = CreditoConta(codigo="CRE-TMP-" + uuid4().hex[:12], pessoa_id=a.pessoa_id, relacao=a.relacao,
        acerto_id=a.id, pagamento_id=p.id, valor_original=float(body.valor), data=body.data,
        referencia=body.referencia, referencia_chave=ref, observacao=body.observacao,
        chave_idempotencia=body.chave_idempotencia, fornecedor_confirmou=body.fornecedor_confirmou,
        referencia_confirmacao=body.referencia_confirmacao or "", created_by=u.id)
    db.add(c)
    try:
        db.flush()
    except (IntegrityError, OperationalError):
        db.rollback()
        raise HTTPException(409, "Reconhecimento já registrado ou em atualização")
    c.codigo = f"CRE-{c.id:06d}"
    audit(db, u.id, "credito_reconhecido", "creditos_conta", c.id, depois=body.model_dump())
    pagamentos._commit(db)
    return _summary(db, c.id)


@r.get("/{cid}")
def detalhe(cid: int, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    c = _credito(db, cid)
    out = _summary(db, cid)
    e = db.query(CreditoReversao).filter_by(credito_id=cid).first()
    out["reversao"] = {"id": e.id, "motivo": e.motivo, "created_by": e.created_by, "created_at": e.created_at} if e else None
    out["aplicacoes"] = [_app_out(db, app) for app in db.query(CreditoAplicacao).filter_by(credito_id=cid).order_by(CreditoAplicacao.id)]
    return out


@r.get("/{cid}/notas-elegiveis")
def notas_elegiveis(cid: int, offset: int = 0, limit: int = 50, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    c = _credito(db, cid)
    q, estado, _ = notas._consulta_notas(db)
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    rows = [] if c.revertido else q.filter(NotaObrigacao.pessoa_id == c.pessoa_id, NotaObrigacao.relacao == c.relacao,
        estado.in_(("aberto", "parcial"))).order_by(NotaObrigacao.id.desc()).offset(offset).limit(limit + 1).all()
    return {"notas": [notas._out(db, n, total, nome) for n, total, nome in rows[:limit]],
            "tem_mais": len(rows) > limit, "offset": offset, "limit": limit}


@r.post("/{cid}/aplicacoes", status_code=201)
def aplicar(cid: int, body: CreditoAplicacaoIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    c = _credito(db, cid)
    old = db.query(CreditoAplicacao).filter_by(credito_id=cid, chave_idempotencia=body.chave_idempotencia).first()
    if old:
        if not all(getattr(old, k) == getattr(body, k) for k in ("nota_id", "data", "referencia", "observacao", "fornecedor_confirmou")) or Decimal(str(old.valor)) != body.valor or old.referencia_confirmacao != (body.referencia_confirmacao or ""):
            raise HTTPException(409, "Chave de requisição já usada com dados diferentes")
        return _app_out(db, old)
    _prova(c.relacao, body)
    ref = bloquear_referencia(db, body.referencia)
    pagamentos._ref_livre(db, ref)
    n = notas._nota(db, body.nota_id)
    a, p = _locks(db, c, n)
    _ativo(db, c)
    if c.revertido or a.status != "efetivado" or p.cancelado or n.cancelada or n.pessoa_id != c.pessoa_id or n.relacao != c.relacao:
        db.rollback()
        raise HTTPException(422, "Crédito e nota devem estar ativos e pertencer ao mesmo titular/relação")
    if body.data < max(c.data, n.data_emissao) or body.data > hoje():
        db.rollback()
        raise HTTPException(422, "Data da aplicação incompatível")
    saldo = _summary(db, cid)["saldo_disponivel"]
    saldo_nota = round(n.valor_original - notas._total(db, n.id), 2)
    if body.valor > Decimal(str(min(saldo, saldo_nota))):
        db.rollback()
        raise HTTPException(422, "Valor excede o saldo do crédito ou da nota")
    app = CreditoAplicacao(credito_id=cid, nota_id=n.id, valor=float(body.valor), data=body.data,
        referencia=body.referencia, observacao=body.observacao, chave_idempotencia=body.chave_idempotencia,
        fornecedor_confirmou=body.fornecedor_confirmou, referencia_confirmacao=body.referencia_confirmacao or "", created_by=u.id)
    db.add(app)
    db.flush()
    db.add(NotaAbatimento(nota_id=n.id, credito_aplicacao_id=app.id, valor=app.valor, data=app.data,
        referencia=app.referencia, referencia_chave=ref, observacao=app.observacao, origem="credito",
        chave_idempotencia=f"credito-aplicacao:{app.id}", created_by=u.id))
    audit(db, u.id, "credito_aplicado", "credito_aplicacoes", app.id, depois=body.model_dump())
    pagamentos._commit(db)
    return _app_out(db, app)


@r.post("/{cid}/aplicacoes/{aid}/estornar")
def estornar(cid: int, aid: int, body: DesfazerIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    confere_senha(u, body.senha)
    c = _credito(db, cid)
    app = db.query(CreditoAplicacao).filter_by(id=aid, credito_id=cid).first()
    if not app:
        raise HTTPException(404, "Aplicação de crédito não encontrada")
    if app.acerto_id is not None:
        raise HTTPException(422, "Aplicação pertence a acerto: estorne o acerto inteiro")
    if app.estornada:
        e = db.query(CreditoAplicacaoEstorno).filter_by(aplicacao_id=aid).one()
        if e.motivo != body.motivo:
            raise HTTPException(409, "Estorno já registrado com outro motivo")
        return _app_out(db, app)
    _locks(db, c, notas._nota(db, app.nota_id))
    if c.revertido:
        db.rollback()
        raise HTTPException(422, "Crédito revertido")
    ab = db.query(NotaAbatimento).filter_by(credito_aplicacao_id=aid).one()
    app.estornada, ab.estornado = True, True
    db.add(CreditoAplicacaoEstorno(aplicacao_id=aid, motivo=body.motivo, created_by=u.id))
    db.add(NotaAbatimentoEstorno(abatimento_id=ab.id, motivo=body.motivo, created_by=u.id))
    audit(db, u.id, "credito_aplicacao_estornada", "credito_aplicacoes", aid, depois={"motivo": body.motivo})
    pagamentos._commit(db)
    return _app_out(db, app)


@r.post("/{cid}/reverter")
def reverter(cid: int, body: DesfazerIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    confere_senha(u, body.senha)
    c = _credito(db, cid)
    if c.revertido:
        e = db.query(CreditoReversao).filter_by(credito_id=cid).one()
        if e.motivo != body.motivo:
            raise HTTPException(409, "Reversão já registrada com outro motivo")
        return _summary(db, cid)
    _locks(db, c)
    if db.query(CreditoAplicacao.id).filter_by(credito_id=cid, estornada=False).first():
        db.rollback()
        raise HTTPException(422, "Estorne todos os usos do crédito antes de reverter o reconhecimento")
    c.revertido = True
    db.add(CreditoReversao(credito_id=cid, motivo=body.motivo, created_by=u.id))
    audit(db, u.id, "credito_revertido", "creditos_conta", cid, depois={"motivo": body.motivo})
    pagamentos._commit(db)
    return _summary(db, cid)
