"""Acertos imutáveis em lote, conferência externa e efetivação atômica."""
import hashlib
import hmac
import json
from decimal import Decimal
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update, func
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (Acerto, AcertoItem, AcertoEvento, CreditoConta, CreditoAplicacao, CreditoAplicacaoEstorno, Pessoa, User, Pagamento, PagamentoAplicacao,
    PagamentoAplicacaoEstorno, NotaObrigacao, NotaAbatimento, NotaAbatimentoEstorno, PagamentoAnexo)
from ..auth import need, confere_senha
from ..audit import audit
from ..cadastros import hoje
from ..config import SECRET_KEY
from ..acertos_schemas import AcertoPreviaIn, AcertoIn, EnvioIn, ConfirmacaoIn, EfetivarIn
from ..notas_schemas import DesfazerIn
from ..referencias_financeiras import bloquear_referencia, chave_referencia
from . import pagamentos, notas

r = APIRouter(prefix="/acertos", tags=["acertos"])
LEITURA = need("admin", "financeiro", "operador", "consulta")
ESCRITA = need("admin", "financeiro")
ESTADOS = {"rascunho", "enviado", "confirmado", "efetivado", "estornado", "cancelado"}


def _acerto(db, aid):
    a = db.get(Acerto, aid)
    if not a:
        raise HTTPException(404, "Acerto não encontrado")
    return a


def _cas(db, a):
    try:
        result = db.execute(update(Acerto).where(Acerto.id == a.id, Acerto.version == a.version)
            .values(version=a.version + 1), execution_options={"synchronize_session": False})
    except OperationalError:
        db.rollback()
        raise HTTPException(409, "Acerto em atualização. Recarregue")
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Acerto alterado em outra sessão. Recarregue")


def _payload(body):
    data = body.model_dump(mode="json", exclude={"chave_idempotencia", "token_previa"}, exclude_none=True)
    for item in data["itens"]:
        item["valor"] = format(Decimal(item["valor"]).normalize(), "f")
    data["itens"] = sorted(data["itens"], key=lambda i: ("credito" if "credito_id" in i else "pagamento", i.get("pagamento_id") or i.get("credito_id"), i["nota_id"]))
    return data


def _digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _context(db, body, exigir_ativo=True):
    from . import creditos
    p = db.get(Pessoa, body.pessoa_id)
    role = "representante" if body.relacao == "cliente" else "fornecedor"
    if not p or (exigir_ativo and (not p.ativo or p.tipo not in (role, "ambos"))):
        raise HTTPException(422, "Titular ativo com o papel da relação é obrigatório")
    if body.data > hoje():
        raise HTTPException(422, "Acerto não pode ter data futura")
    fontes, fontes_credito, destinos = {}, {}, {}
    pgids = {i.pagamento_id for i in body.itens if i.pagamento_id is not None}
    crids = {i.credito_id for i in body.itens if i.credito_id is not None}
    ntids = {i.nota_id for i in body.itens}
    pgs = {pg.id: pg for pg in db.query(Pagamento).filter(Pagamento.id.in_(pgids))}
    crs = {c.id: c for c in db.query(CreditoConta).filter(CreditoConta.id.in_(crids))}
    origens = {a.id: a for a in db.query(Acerto).filter(Acerto.id.in_({c.acerto_id for c in crs.values()}))}
    nts = {n.id: n for n in db.query(NotaObrigacao).filter(NotaObrigacao.id.in_(ntids))}
    budgets = {row[0].id: pagamentos._out(row)["orcamentos"][body.relacao] for row in pagamentos._query(db).filter(Pagamento.id.in_(pgids))}
    cq, _ = creditos._query(db)
    saldo_cr = {row[0].id: creditos._out(row)["saldo_disponivel"] for row in cq.filter(CreditoConta.id.in_(crids))}
    nq, _, _ = notas._consulta_notas(db)
    saldos_nt = {n.id: round(n.valor_original - float(total), 2) for n, total, _ in nq.filter(NotaObrigacao.id.in_(ntids))}
    for item in body.itens:
        n = nts.get(item.nota_id)
        if n is None:
            raise HTTPException(404, "Nota não encontrada")
        if n.cancelada or n.relacao != body.relacao or n.pessoa_id != body.pessoa_id:
            raise HTTPException(422, "Nota deve estar ativa e pertencer ao titular/relação")
        if item.pagamento_id is not None:
            pg = pgs.get(item.pagamento_id)
            if pg is None:
                raise HTTPException(404, "Pagamento não encontrado")
            titular = pg.cliente_id if body.relacao == "cliente" else pg.fornecedor_id
            if pg.cancelado or titular != body.pessoa_id:
                raise HTTPException(422, "Pagamento deve estar ativo e pertencer ao titular/relação")
            data_fonte = pg.data
            if pg.id not in fontes:
                fontes[pg.id] = {"pagamento_id": pg.id, "codigo": pg.codigo, "version": pg.version,
                    "saldo_antes": budgets[pg.id]["saldo_disponivel"], "valor_aplicar": Decimal("0")}
            fontes[pg.id]["valor_aplicar"] += item.valor
        else:
            c = crs.get(item.credito_id)
            if c is None:
                raise HTTPException(404, "Crédito não encontrado")
            if c.revertido or c.pessoa_id != body.pessoa_id or c.relacao != body.relacao or origens[c.acerto_id].status != "efetivado":
                raise HTTPException(422, "Crédito deve estar ativo, com origem efetivada e mesmo titular/relação")
            data_fonte = c.data
            if c.id not in fontes_credito:
                fontes_credito[c.id] = {"credito_id": c.id, "codigo": c.codigo, "version": c.version,
                    "saldo_antes": saldo_cr[c.id], "valor_aplicar": Decimal("0"),
                    "acerto_origem_id": c.acerto_id, "pagamento_origem_id": c.pagamento_id}
            fontes_credito[c.id]["valor_aplicar"] += item.valor
        if body.data < max(data_fonte, n.data_emissao):
            raise HTTPException(422, "Data do acerto antecede fonte ou emissão da nota")
        if n.id not in destinos:
            destinos[n.id] = {"nota_id": n.id, "numero_documento": n.numero_documento, "version": n.version,
                "saldo_antes": saldos_nt[n.id], "valor_aplicar": Decimal("0")}
        destinos[n.id]["valor_aplicar"] += item.valor
    for row in list(fontes.values()) + list(fontes_credito.values()) + list(destinos.values()):
        if row["valor_aplicar"] > Decimal(str(row["saldo_antes"])):
            raise HTTPException(422, "Proposta excede saldo da fonte ou da nota; nenhum item aplicado")
        row["valor_aplicar"] = float(row["valor_aplicar"])
        row["saldo_depois"] = round(row["saldo_antes"] - row["valor_aplicar"], 2)
    snapshot = {"fontes": [fontes[k] for k in sorted(fontes)], "notas": [destinos[k] for k in sorted(destinos)]}
    # Mantém o HMAC dos rascunhos anteriores que só continham pagamentos.
    if fontes_credito:
        snapshot["creditos"] = [fontes_credito[k] for k in sorted(fontes_credito)]
    payload = {"proposta": _payload(body), "snapshot": snapshot}
    token = hmac.new(SECRET_KEY.encode(), json.dumps(payload, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
    return {"token_previa": token, "total_aplicar": float(sum((i.valor for i in body.itens), Decimal("0"))),
            **snapshot, "creditos": [fontes_credito[k] for k in sorted(fontes_credito)], "sem_reserva": True}


def _evento(db, a, u, acao, referencia="", observacao=""):
    db.add(AcertoEvento(acerto_id=a.id, acao=acao, referencia=referencia, observacao=observacao, created_by=u.id))
    audit(db, u.id, "acerto_" + acao, "acertos", a.id, depois={"referencia": referencia, "observacao": observacao})


def _itens(db, aid):
    return db.query(AcertoItem).filter_by(acerto_id=aid).order_by(AcertoItem.id).all()


def _out(db, a, detalhar=False, total=None, nome=None):
    total = round(float(db.query(func.coalesce(func.sum(AcertoItem.valor), 0)).filter_by(acerto_id=a.id).scalar()), 2) if total is None else round(float(total), 2)
    out = {"id": a.id, "codigo": a.codigo, "pessoa_id": a.pessoa_id,
        "pessoa_nome": nome if nome is not None else db.get(Pessoa, a.pessoa_id).nome,
        "relacao": a.relacao, "data": a.data, "referencia": a.referencia, "observacao": a.observacao,
        "status": a.status, "token_previa": a.token_previa, "chave_idempotencia": a.chave_idempotencia,
        "total_aplicar": total, "referencia_envio": a.referencia_envio, "observacao_envio": a.observacao_envio,
        "referencia_confirmacao": a.referencia_confirmacao, "observacao_confirmacao": a.observacao_confirmacao,
        "motivo_cancelamento": a.motivo_cancelamento, "motivo_estorno": a.motivo_estorno, "created_at": a.created_at}
    if detalhar:
        usados = db.query(CreditoAplicacao.credito_id.label("cid"), func.sum(CreditoAplicacao.valor).label("total"))            .filter_by(estornada=False).group_by(CreditoAplicacao.credito_id).subquery()
        out["creditos"] = [{"id": c.id, "codigo": c.codigo, "pagamento_id": c.pagamento_id,
            "valor_original": c.valor_original, "status": "revertido" if c.revertido else "utilizado"
                if round(c.valor_original - float(total), 2) == 0 else "parcial" if total else "disponivel"}
            for c, total in db.query(CreditoConta, func.coalesce(usados.c.total, 0)).outerjoin(usados, usados.c.cid == CreditoConta.id)
                .filter(CreditoConta.acerto_id == a.id).order_by(CreditoConta.id)]
        items = _itens(db, a.id)
        pgs = {pg.id: pg for pg in db.query(Pagamento).filter(Pagamento.id.in_({i.pagamento_id for i in items}))}
        nts = {n.id: n for n in db.query(NotaObrigacao).filter(NotaObrigacao.id.in_({i.nota_id for i in items}))}
        crs = {c.id: c for c in db.query(CreditoConta).filter(CreditoConta.id.in_({i.credito_id for i in items if i.credito_id is not None}))}
        apps = {("pagamento", x.pagamento_id, x.nota_id): x.id for x in db.query(PagamentoAplicacao).filter_by(acerto_id=a.id)}
        apps.update({("credito", x.credito_id, x.nota_id): x.id for x in db.query(CreditoAplicacao).filter_by(acerto_id=a.id)})
        out["itens"] = [{"id": i.id, "tipo_fonte": "pagamento" if i.pagamento_id is not None else "credito",
            "pagamento_id": i.pagamento_id, "credito_id": i.credito_id,
            "codigo_fonte": pgs[i.pagamento_id].codigo if i.pagamento_id is not None else crs[i.credito_id].codigo,
            "codigo_pagamento": pgs[i.pagamento_id].codigo if i.pagamento_id is not None else None,
            "codigo_credito": crs[i.credito_id].codigo if i.credito_id is not None else None,
            "nota_id": i.nota_id, "numero_documento": nts[i.nota_id].numero_documento, "valor": i.valor,
            "aplicacao_id": apps.get(("pagamento" if i.pagamento_id is not None else "credito", i.pagamento_id or i.credito_id, i.nota_id))} for i in items]
        out["eventos"] = [{"id": e.id, "acao": e.acao, "referencia": e.referencia,
            "observacao": e.observacao, "created_by": e.created_by, "created_at": e.created_at}
            for e in db.query(AcertoEvento).filter_by(acerto_id=a.id).order_by(AcertoEvento.id)]
    return out


def _body(db, a):
    return AcertoPreviaIn(pessoa_id=a.pessoa_id, relacao=a.relacao, data=a.data,
        referencia=a.referencia, observacao=a.observacao,
        itens=[{"pagamento_id": i.pagamento_id, "credito_id": i.credito_id, "nota_id": i.nota_id, "valor": Decimal(str(i.valor))} for i in _itens(db, a.id)])


def _locks(db, a):
    from . import creditos
    items = _itens(db, a.id)
    crids = {i.credito_id for i in items if i.credito_id is not None}
    crs = {c.id: c for c in db.query(CreditoConta).filter(CreditoConta.id.in_(crids)).order_by(CreditoConta.id)}
    acerto_ids = {a.id} | {c.acerto_id for c in crs.values()}
    pgids = {i.pagamento_id for i in items if i.pagamento_id is not None} | {c.pagamento_id for c in crs.values()}
    ntsids = {i.nota_id for i in items}
    acts = {x.id: x for x in db.query(Acerto).filter(Acerto.id.in_(acerto_ids)).order_by(Acerto.id)}
    pgs = {pg.id: pg for pg in db.query(Pagamento).filter(Pagamento.id.in_(pgids)).order_by(Pagamento.id)}
    nts = {n.id: n for n in db.query(NotaObrigacao).filter(NotaObrigacao.id.in_(ntsids)).order_by(NotaObrigacao.id)}
    if len(crs) != len(crids) or len(acts) != len(acerto_ids) or len(pgs) != len(pgids) or len(nts) != len(ntsids):
        raise HTTPException(409, "Recursos do acerto indisponíveis")
    for x in acts.values():
        _cas(db, x)
    for pg in pgs.values():
        pagamentos._cas(db, pg)
    for c in crs.values():
        creditos._cas(db, c)
    for n in nts.values():
        notas._cas(db, n)
    return pgs, crs, nts


@r.get("/recursos")
def recursos(pessoa_id: int, relacao: str, pagamentos_offset: int = 0, notas_offset: int = 0, creditos_offset: int = 0,
             limit: int = 50, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    if relacao not in ("cliente", "fornecedor"):
        raise HTTPException(422, "Relação inválida")
    if not db.get(Pessoa, pessoa_id):
        raise HTTPException(404, "Titular não encontrado")
    limit = min(max(limit, 1), 100)
    pagamentos_offset, notas_offset = max(pagamentos_offset, 0), max(notas_offset, 0)
    soma = db.query(PagamentoAplicacao.pagamento_id.label("pid"), func.sum(PagamentoAplicacao.valor).label("usado"))\
        .filter_by(relacao=relacao, estornada=False).group_by(PagamentoAplicacao.pagamento_id).subquery()
    coluna = Pagamento.cliente_id if relacao == "cliente" else Pagamento.fornecedor_id
    tipos = ("cliente_loja", "cliente_fornecedor") if relacao == "cliente" else ("cliente_fornecedor", "repasse_fornecedor")
    credits = db.query(CreditoConta.pagamento_id.label("pid"), func.sum(CreditoConta.valor_original).label("total"))        .filter_by(relacao=relacao, revertido=False).group_by(CreditoConta.pagamento_id).subquery()
    elegiveis = db.query(Pagamento.id).outerjoin(soma, soma.c.pid == Pagamento.id).outerjoin(credits, credits.c.pid == Pagamento.id).filter(
        coluna == pessoa_id, Pagamento.tipo.in_(tipos), Pagamento.cancelado == False,
        func.round(Pagamento.valor - func.coalesce(soma.c.usado, 0) - func.coalesce(credits.c.total, 0), 2) > 0)
    pgs = pagamentos._query(db).filter(Pagamento.id.in_(elegiveis)).order_by(Pagamento.id.desc())\
        .offset(pagamentos_offset).limit(limit + 1).all()
    q, estado, _ = notas._consulta_notas(db)
    nts = q.filter(NotaObrigacao.pessoa_id == pessoa_id, NotaObrigacao.relacao == relacao,
        estado.in_(("aberto", "parcial"))).order_by(NotaObrigacao.id.desc()).offset(notas_offset).limit(limit + 1).all()
    from . import creditos
    cq, cestado = creditos._query(db)
    creditos_offset = max(creditos_offset, 0)
    crs = cq.filter(CreditoConta.pessoa_id == pessoa_id, CreditoConta.relacao == relacao,
        Acerto.status == "efetivado", cestado.in_(("disponivel", "parcial")))        .order_by(CreditoConta.id.desc()).offset(creditos_offset).limit(limit + 1).all()
    return {"creditos": [creditos._out(row) for row in crs[:limit]],
        "creditos_offset": creditos_offset, "creditos_tem_mais": len(crs) > limit,
        "pagamentos": [pagamentos._out(row) for row in pgs[:limit]],
        "notas": [notas._out(db, n, total, nome) for n, total, nome in nts[:limit]],
        "pagamentos_tem_mais": len(pgs) > limit, "notas_tem_mais": len(nts) > limit,
        "pagamentos_offset": pagamentos_offset, "notas_offset": notas_offset, "limit": limit}


@r.post("/previa")
def previa(body: AcertoPreviaIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    pagamentos._ref_livre(db, chave_referencia(body.referencia))
    return _context(db, body)


@r.post("", status_code=201)
def criar(body: AcertoIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    old = db.query(Acerto).filter_by(chave_idempotencia=body.chave_idempotencia).first()
    digest = _digest({"proposta": _payload(body), "token_previa": body.token_previa})
    if old:
        if old.payload_hash != digest:
            raise HTTPException(409, "Chave de requisição já usada com proposta diferente")
        return _out(db, old, True)
    pagamentos._ref_livre(db, chave_referencia(body.referencia))
    context = _context(db, body)
    if not hmac.compare_digest(context["token_previa"], body.token_previa):
        raise HTTPException(409, "Prévia desatualizada ou inválida. Revise antes de criar o acerto")
    a = Acerto(pessoa_id=body.pessoa_id, relacao=body.relacao, data=body.data, referencia=body.referencia,
        observacao=body.observacao, token_previa=body.token_previa, chave_idempotencia=body.chave_idempotencia,
        payload_hash=digest, codigo="ACE-TMP-" + uuid4().hex[:12], created_by=u.id)
    db.add(a)
    try:
        db.flush()
    except (IntegrityError, OperationalError):
        db.rollback()
        raise HTTPException(409, "Acerto já registrado ou em atualização")
    a.codigo = f"ACE-{a.id:06d}"
    fontes = {f["pagamento_id"]: f for f in context["fontes"]}
    nts = {n["nota_id"]: n for n in context["notas"]}
    crs = {c["credito_id"]: c for c in context["creditos"]}
    from . import creditos
    for i in body.itens:
        dados_credito = {}
        if i.credito_id is not None:
            c = creditos._credito(db, i.credito_id)
            cs = creditos._summary(db, c.id)
            dados_credito = {"credito_id": c.id, "codigo": c.codigo, "valor_original": c.valor_original,
                "data": str(c.data), "referencia": c.referencia, "pessoa_id": c.pessoa_id,
                "pessoa_nome": cs["pessoa_nome"], "relacao": c.relacao,
                "acerto_origem_id": c.acerto_id, "codigo_acerto_origem": cs["codigo_acerto"],
                "pagamento_origem_id": c.pagamento_id, "codigo_pagamento_origem": cs["codigo_pagamento"]}
        db.add(AcertoItem(acerto_id=a.id, pagamento_id=i.pagamento_id, credito_id=i.credito_id, nota_id=i.nota_id, valor=float(i.valor),
            pagamento_version=fontes[i.pagamento_id]["version"] if i.pagamento_id is not None else None,
            credito_version=crs[i.credito_id]["version"] if i.credito_id is not None else None,
            nota_version=nts[i.nota_id]["version"],
            saldo_pagamento_snapshot=fontes[i.pagamento_id]["saldo_antes"] if i.pagamento_id is not None else None,
            saldo_credito_snapshot=crs[i.credito_id]["saldo_antes"] if i.credito_id is not None else None,
            credito_dados_snapshot=json.dumps(dados_credito, ensure_ascii=False), saldo_nota_snapshot=nts[i.nota_id]["saldo_antes"]))
    _evento(db, a, u, "criado", body.referencia, body.observacao)
    pagamentos._commit(db)
    return _out(db, a, True)


@r.get("")
def listar(pessoa_id: int | None = None, relacao: str | None = None, status: str | None = None,
           limit: int = 100, offset: int = 0, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    if relacao and relacao not in ("cliente", "fornecedor"):
        raise HTTPException(422, "Relação inválida")
    if status and status not in ESTADOS:
        raise HTTPException(422, "Status inválido")
    total = db.query(AcertoItem.acerto_id.label("aid"), func.sum(AcertoItem.valor).label("total"))\
        .group_by(AcertoItem.acerto_id).subquery()
    q = db.query(Acerto, total.c.total, Pessoa.nome).join(Pessoa, Pessoa.id == Acerto.pessoa_id).join(total, total.c.aid == Acerto.id)
    if pessoa_id:
        q = q.filter(Acerto.pessoa_id == pessoa_id)
    if relacao:
        q = q.filter(Acerto.relacao == relacao)
    if status:
        q = q.filter(Acerto.status == status)
    return [_out(db, a, total=t, nome=nome) for a, t, nome in q.order_by(Acerto.id.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 500))]


@r.get("/{aid}")
def detalhe(aid: int, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    return _out(db, _acerto(db, aid), True)


@r.post("/{aid}/enviar")
def enviar(aid: int, body: EnvioIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    a = _acerto(db, aid)
    if a.relacao != "fornecedor":
        raise HTTPException(422, "Envio para conferência pertence ao acerto fornecedor")
    if a.status in ("enviado", "confirmado", "efetivado", "estornado"):
        if a.referencia_envio == body.referencia_envio and a.observacao_envio == body.observacao_envio:
            return _out(db, a, True)
        raise HTTPException(409, "Envio já documentado com outra evidência")
    _cas(db, a)
    if a.status != "rascunho":
        db.rollback()
        raise HTTPException(422, "Acerto não está em rascunho")
    a.status = "enviado"
    a.referencia_envio, a.observacao_envio = body.referencia_envio, body.observacao_envio
    _evento(db, a, u, "enviado", body.referencia_envio, body.observacao_envio)
    pagamentos._commit(db)
    return _out(db, a, True)


@r.post("/{aid}/confirmar")
def confirmar(aid: int, body: ConfirmacaoIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    a = _acerto(db, aid)
    if a.relacao != "fornecedor":
        raise HTTPException(422, "Confirmação externa pertence ao acerto fornecedor")
    if a.status in ("confirmado", "efetivado", "estornado"):
        if a.referencia_confirmacao == body.referencia_confirmacao and a.observacao_confirmacao == body.observacao_confirmacao:
            return _out(db, a, True)
        raise HTTPException(409, "Confirmação já documentada com outra evidência")
    _cas(db, a)
    if a.status != "enviado":
        db.rollback()
        raise HTTPException(422, "Documente o envio antes da confirmação")
    a.status = "confirmado"
    a.referencia_confirmacao, a.observacao_confirmacao = body.referencia_confirmacao, body.observacao_confirmacao
    _evento(db, a, u, "confirmado", body.referencia_confirmacao, body.observacao_confirmacao)
    pagamentos._commit(db)
    return _out(db, a, True)


@r.post("/{aid}/efetivar")
def efetivar(aid: int, body: EfetivarIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    a = _acerto(db, aid)
    if a.status == "efetivado":
        return _out(db, a, True)
    if a.status not in (("rascunho",) if a.relacao == "cliente" else ("confirmado",)):
        raise HTTPException(422, "Fornecedor exige envio e confirmação; cliente exige rascunho")
    ref = bloquear_referencia(db, a.referencia)
    pagamentos._ref_livre(db, ref)
    pgs, crs, nts = _locks(db, a)
    for item in _itens(db, aid):
        if (item.pagamento_id is not None and pgs[item.pagamento_id].version != item.pagamento_version) or (item.credito_id is not None and crs[item.credito_id].version != item.credito_version) or nts[item.nota_id].version != item.nota_version:
            db.rollback()
            raise HTTPException(409, "Proposta desatualizada. Crie novo acerto após revisar; nenhum item aplicado")
    proposta = _body(db, a)
    context = _context(db, proposta)
    if not hmac.compare_digest(a.token_previa, context["token_previa"]):
        db.rollback()
        raise HTTPException(409, "Proposta desatualizada. Crie novo acerto após revisar; nenhum item aplicado")
    for item in _itens(db, aid):
        comuns = dict(nota_id=item.nota_id, acerto_id=aid, valor=item.valor, data=a.data,
            referencia=a.referencia, observacao=a.observacao, chave_idempotencia=f"acerto:{aid}:item:{item.id}",
            fornecedor_confirmou=a.relacao == "fornecedor", referencia_confirmacao=a.referencia_confirmacao if a.relacao == "fornecedor" else "", created_by=u.id)
        if item.pagamento_id is not None:
            app = PagamentoAplicacao(pagamento_id=item.pagamento_id, relacao=a.relacao, **comuns)
        else:
            app = CreditoAplicacao(credito_id=item.credito_id, **comuns)
        db.add(app)
        db.flush()
        db.add(NotaAbatimento(nota_id=item.nota_id,
            pagamento_aplicacao_id=app.id if item.pagamento_id is not None else None,
            credito_aplicacao_id=app.id if item.credito_id is not None else None, valor=item.valor,
            data=a.data, referencia=a.referencia, referencia_chave=ref, observacao=a.observacao,
            origem="pagamento" if item.pagamento_id is not None else "credito",
            chave_idempotencia=("pagamento-aplicacao:" if item.pagamento_id is not None else "credito-aplicacao:") + str(app.id), created_by=u.id))
    a.status = "efetivado"
    _evento(db, a, u, "efetivado", a.referencia, a.observacao)
    pagamentos._commit(db)
    return _out(db, a, True)


@r.post("/{aid}/estornar")
def estornar(aid: int, body: DesfazerIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    confere_senha(u, body.senha)
    a = _acerto(db, aid)
    if a.status == "estornado":
        if a.motivo_estorno != body.motivo:
            raise HTTPException(409, "Estorno já registrado com motivo diferente")
        return _out(db, a, True)
    if a.status != "efetivado":
        db.rollback()
        raise HTTPException(422, "Somente acerto efetivado pode ser estornado")
    _locks(db, a)
    if db.query(CreditoConta.id).filter_by(acerto_id=aid, revertido=False).first():
        db.rollback()
        raise HTTPException(422, "Reverta os créditos da origem antes de estornar o acerto")
    apps = db.query(PagamentoAplicacao).filter_by(acerto_id=aid).order_by(PagamentoAplicacao.id).all()
    credit_apps = db.query(CreditoAplicacao).filter_by(acerto_id=aid).order_by(CreditoAplicacao.id).all()
    if len(apps) + len(credit_apps) != len(_itens(db, aid)) or any(app.estornada for app in apps + credit_apps):
        db.rollback()
        raise HTTPException(409, "Histórico do acerto inconsistente; nenhuma aplicação estornada")
    for app in apps + credit_apps:
        ab = db.query(NotaAbatimento).filter_by(**({"pagamento_aplicacao_id": app.id} if isinstance(app, PagamentoAplicacao) else {"credito_aplicacao_id": app.id})).one()
        if ab.estornado:
            db.rollback()
            raise HTTPException(409, "Histórico da nota inconsistente; nenhuma aplicação estornada")
        app.estornada, ab.estornado = True, True
        db.add((PagamentoAplicacaoEstorno if isinstance(app, PagamentoAplicacao) else CreditoAplicacaoEstorno)(aplicacao_id=app.id, motivo=body.motivo, created_by=u.id))
        db.add(NotaAbatimentoEstorno(abatimento_id=ab.id, motivo=body.motivo, created_by=u.id))
    a.status, a.motivo_estorno = "estornado", body.motivo
    _evento(db, a, u, "estornado", a.referencia, body.motivo)
    pagamentos._commit(db)
    return _out(db, a, True)


@r.post("/{aid}/cancelar")
def cancelar(aid: int, body: DesfazerIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    confere_senha(u, body.senha)
    a = _acerto(db, aid)
    if a.status == "cancelado":
        if a.motivo_cancelamento != body.motivo:
            raise HTTPException(409, "Cancelamento já registrado com motivo diferente")
        return _out(db, a, True)
    _cas(db, a)
    if a.status not in ("rascunho", "enviado", "confirmado"):
        db.rollback()
        raise HTTPException(422, "Acerto efetivado exige estorno integral")
    a.status, a.motivo_cancelamento = "cancelado", body.motivo
    _evento(db, a, u, "cancelado", a.referencia, body.motivo)
    pagamentos._commit(db)
    return _out(db, a, True)


@r.get("/{aid}/relacao")
def relacao_local(aid: int, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    a = _acerto(db, aid)
    out = _out(db, a, True)
    fontes, credits, nts = {}, {}, {}
    items = _itens(db, aid)
    pgs = {pg.id: pg for pg in db.query(Pagamento).filter(Pagamento.id.in_({i.pagamento_id for i in items if i.pagamento_id is not None}))}
    notas_map = {n.id: n for n in db.query(NotaObrigacao).filter(NotaObrigacao.id.in_({i.nota_id for i in items}))}
    anexos = {}
    for an in db.query(PagamentoAnexo).filter(PagamentoAnexo.pagamento_id.in_(pgs), PagamentoAnexo.ativo == True).order_by(PagamentoAnexo.id):
        anexos.setdefault(an.pagamento_id, []).append(pagamentos._anexo_out(an))
    for i in items:
        n = notas_map[i.nota_id]
        if i.pagamento_id is not None:
            pg = pgs[i.pagamento_id]
            if pg.id not in fontes:
                fontes[pg.id] = {"pagamento_id": pg.id, "codigo": pg.codigo, "valor_original": pg.valor,
                    "data": pg.data, "forma": pg.forma, "referencia_externa": pg.referencia_externa,
                    "saldo_antes": i.saldo_pagamento_snapshot, "valor_aplicar": 0.0,
                    "anexos": anexos.get(pg.id, [])}
            row = fontes[pg.id]
        else:
            if i.credito_id not in credits:
                credits[i.credito_id] = {**json.loads(i.credito_dados_snapshot),
                    "saldo_antes": i.saldo_credito_snapshot, "valor_aplicar": 0.0}
            row = credits[i.credito_id]
        row["valor_aplicar"] = round(row["valor_aplicar"] + i.valor, 2)
        if n.id not in nts:
            nts[n.id] = {"nota_id": n.id, "numero_documento": n.numero_documento,
                "valor_original": n.valor_original, "vencimento": n.vencimento,
                "saldo_antes": i.saldo_nota_snapshot, "valor_aplicar": 0.0}
        nts[n.id]["valor_aplicar"] = round(nts[n.id]["valor_aplicar"] + i.valor, 2)
    for row in list(fontes.values()) + list(credits.values()) + list(nts.values()):
        row["saldo_depois"] = round(row["saldo_antes"] - row["valor_aplicar"], 2)
    out.update(tipo_documento="relacao_local", nao_enviado_automaticamente=True,
        fontes=list(fontes.values()), creditos=list(credits.values()), notas=list(nts.values()))
    return out
