"""Pagamentos novos, orçamento independente por relação e repasses reais."""
from decimal import Decimal
from datetime import timezone
from pathlib import Path
from uuid import uuid4
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy import update, func, case
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.orm import Session, aliased
from ..database import get_db
from ..ambientes import upload_root
from ..models import (Pagamento, PagamentoAplicacao, PagamentoAplicacaoEstorno, PagamentoAnexo,
    Pessoa, User, CreditoConta, NotaObrigacao, NotaAbatimento, NotaAbatimentoEstorno, Movimentacao, Comprovante)
from ..auth import need, confere_senha
from ..audit import audit
from ..rastreabilidade import horario_utc
from ..anexos_privados import mime_privado, resposta_arquivo
from ..cadastros import hoje
from ..catalogos import resolver_catalogos
from ..ordenacao_tabelas import ordenar
from ..config import UPLOAD_DIR, MAX_UPLOAD_MB
from ..pagamentos_schemas import PagamentoIn, AplicacaoIn
from ..notas_schemas import DesfazerIn
from ..referencias_financeiras import bloquear_referencia, chave_referencia
from .notas import _cas as nota_cas, _total as nota_total

r = APIRouter(prefix="/pagamentos", tags=["pagamentos"])
LEITURA = need("admin", "financeiro", "operador", "consulta")
ESCRITA = need("admin", "financeiro")


def _pagamento(db, pid):
    p = db.get(Pagamento, pid)
    if not p:
        raise HTTPException(404, "Pagamento não encontrado")
    return p


def _cas(db, p):
    try:
        result = db.execute(update(Pagamento).where(Pagamento.id == p.id,
            Pagamento.version == p.version).values(version=p.version + 1),
            execution_options={"synchronize_session": False})
    except OperationalError:
        db.rollback()
        raise HTTPException(409, "Pagamento em atualização. Recarregue e tente novamente")
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Pagamento alterado em outra sessão. Recarregue")


def _query(db):
    apps = db.query(PagamentoAplicacao.pagamento_id.label("pid"),
        func.sum(case((PagamentoAplicacao.relacao == "cliente", PagamentoAplicacao.valor), else_=0)).label("cli"),
        func.sum(case((PagamentoAplicacao.relacao == "fornecedor", PagamentoAplicacao.valor), else_=0)).label("forn"))\
        .filter_by(estornada=False).group_by(PagamentoAplicacao.pagamento_id).subquery()
    reps = db.query(Pagamento.pagamento_origem_id.label("pid"), func.sum(Pagamento.valor).label("total"))\
        .filter(Pagamento.tipo == "repasse_fornecedor", Pagamento.cancelado == False)\
        .group_by(Pagamento.pagamento_origem_id).subquery()
    credits = db.query(CreditoConta.pagamento_id.label("pid"),
        func.sum(case((CreditoConta.relacao == "cliente", CreditoConta.valor_original), else_=0)).label("cli"),
        func.sum(case((CreditoConta.relacao == "fornecedor", CreditoConta.valor_original), else_=0)).label("forn"))        .filter_by(revertido=False).group_by(CreditoConta.pagamento_id).subquery()
    cli, forn = aliased(Pessoa), aliased(Pessoa)
    return db.query(Pagamento, func.coalesce(apps.c.cli, 0), func.coalesce(apps.c.forn, 0),
        func.coalesce(reps.c.total, 0), cli.nome, forn.nome,
        func.coalesce(credits.c.cli, 0), func.coalesce(credits.c.forn, 0))\
        .outerjoin(apps, apps.c.pid == Pagamento.id).outerjoin(reps, reps.c.pid == Pagamento.id)\
        .outerjoin(credits, credits.c.pid == Pagamento.id)\
        .outerjoin(cli, cli.id == Pagamento.cliente_id).outerjoin(forn, forn.id == Pagamento.fornecedor_id)


def _orcamento(p, relacao, aplicado, destinado_credito=0):
    elegivel = p.valor if ((relacao == "cliente" and p.tipo in ("cliente_loja", "cliente_fornecedor"))
               or (relacao == "fornecedor" and p.tipo in ("cliente_fornecedor", "repasse_fornecedor"))) else 0.0
    aplicado = round(float(aplicado), 2)
    destinado_credito = round(float(destinado_credito), 2)
    saldo = round(elegivel - aplicado - destinado_credito, 2)
    status = "cancelado" if p.cancelado else "inelegivel" if not elegivel else "utilizado" if saldo == 0 else "parcial" if aplicado or destinado_credito else "disponivel"
    return {"elegivel": elegivel, "aplicado": aplicado, "destinado_credito": destinado_credito,
            "saldo_disponivel": 0.0 if p.cancelado else saldo, "status": status}


def _out(row):
    p, cli, forn, reps, cli_nome, forn_nome, credito_cli, credito_forn = row
    reps = round(float(reps), 2)
    return {"forma_id": p.forma_id, "forma_nome_snapshot": p.forma_nome_snapshot,
        "operacao_id": p.operacao_id, "operacao_nome_snapshot": p.operacao_nome_snapshot,
        "id": p.id, "codigo": p.codigo, "tipo": p.tipo, "forma": p.forma,
        "valor": p.valor, "data": p.data, "cliente_id": p.cliente_id, "cliente_nome": cli_nome,
        "fornecedor_id": p.fornecedor_id, "fornecedor_nome": forn_nome,
        "pagamento_origem_id": p.pagamento_origem_id, "referencia_externa": p.referencia_externa,
        "observacao": p.observacao, "chave_idempotencia": p.chave_idempotencia,
        "cancelado": p.cancelado, "motivo_cancelamento": p.motivo_cancelamento,
        "origem_registro": p.origem_registro or "nao_informada", "created_by": p.created_by, "autor_nome": p.autor_nome,
        "created_at": horario_utc(p.created_at), "updated_at": horario_utc(p.updated_at),
        "data_hora_transacao": horario_utc(p.data_hora_transacao), "remetente": p.remetente,
        "favorecido": p.favorecido, "intermediador": p.intermediador,
        "orcamentos": {"cliente": _orcamento(p, "cliente", cli, credito_cli), "fornecedor": _orcamento(p, "fornecedor", forn, credito_forn)},
        "valor_repassado": reps, "saldo_para_repasse": round(p.valor - reps, 2) if p.tipo == "cliente_loja" and not p.cancelado else 0.0}


def _summary(db, pid):
    return _out(_query(db).filter(Pagamento.id == pid).one())


def _app_out(db, a):
    n = db.get(NotaObrigacao, a.nota_id)
    ab = db.query(NotaAbatimento).filter_by(pagamento_aplicacao_id=a.id).one()
    e = db.query(PagamentoAplicacaoEstorno).filter_by(aplicacao_id=a.id).first()
    return {"id": a.id, "pagamento_id": a.pagamento_id, "nota_id": a.nota_id,
        "numero_documento": n.numero_documento, "acerto_id": a.acerto_id, "relacao": a.relacao, "valor": a.valor,
        "data": a.data, "referencia": a.referencia, "observacao": a.observacao,
        "chave_idempotencia": a.chave_idempotencia, "estornada": a.estornada,
        "fornecedor_confirmou": a.fornecedor_confirmou, "referencia_confirmacao": a.referencia_confirmacao,
        "nota_abatimento_id": ab.id, "created_at": a.created_at,
        "estorno": {"id": e.id, "motivo": e.motivo, "created_by": e.created_by,
                    "created_at": e.created_at} if e else None}


def _anexo_out(a, db):
    return {"id": a.id, "pagamento_id": a.pagamento_id, "nome_original": a.nome_original,
        "tamanho": a.tamanho, "ativo": a.ativo, "created_by": a.created_by, "created_at": horario_utc(a.created_at),
        "tipo_mime": mime_privado(a.arquivo_path, upload_root(db, base=UPLOAD_DIR) / "pagamentos" / str(a.pagamento_id)),
        "url_visualizacao": f"/pagamentos/{a.pagamento_id}/anexos/{a.id}/arquivo?inline=true",
        "url_download": f"/pagamentos/{a.pagamento_id}/anexos/{a.id}/arquivo"}


def _titular(db, pid, role):
    p = db.get(Pessoa, pid)
    if not p or not p.ativo or p.tipo not in (role, "ambos"):
        raise HTTPException(422, "Titular ativo com o papel da relação é obrigatório")


def _ref_livre(db, ref):
    # Sem classificar legado/documentos como novo evento consumível.
    if db.query(Movimentacao.id).filter(func.lower(Movimentacao.codigo) == ref).first()\
        or db.query(Comprovante.id).filter(func.lower(Comprovante.arquivo_hash).in_((ref, "ckto:" + ref))).first()\
        or db.query(NotaAbatimento.id).filter(NotaAbatimento.origem == "registro_documental",
            NotaAbatimento.estornado == False, NotaAbatimento.referencia_chave == ref).first():
        raise HTTPException(409, "Referência já existe no histórico anterior. Classificação manual necessária")


def _igual_pagamento(p, body):
    return all(getattr(p, k) == getattr(body, k) for k in ("tipo", "forma", "data", "cliente_id", "fornecedor_id",
        "pagamento_origem_id", "referencia_externa", "observacao", "forma_id", "operacao_id", "remetente", "favorecido", "intermediador")) and Decimal(str(p.valor)) == body.valor and horario_utc(p.data_hora_transacao) == horario_utc(body.data_hora_transacao)


def _commit(db):
    try:
        db.commit()
    except (IntegrityError, OperationalError):
        db.rollback()
        raise HTTPException(409, "Dados já registrados ou alterados em outra sessão. Recarregue")


@r.get("")
def listar(cliente_id: int | None = None, fornecedor_id: int | None = None,
           tipo: str | None = None, forma: str | None = None, limit: int = 100, offset: int = 0,
           ordenar_por: str | None = None, direcao: str = "asc",
           valor_min: Decimal | None = Query(None, ge=0, le=Decimal("9999999999.99"), max_digits=12, decimal_places=2, allow_inf_nan=False),
           valor_max: Decimal | None = Query(None, ge=0, le=Decimal("9999999999.99"), max_digits=12, decimal_places=2, allow_inf_nan=False),
           origem_registro: str | None = None,
           db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    if tipo and tipo not in ("cliente_loja", "cliente_fornecedor", "repasse_fornecedor"):
        raise HTTPException(422, "Tipo inválido")
    if forma and forma not in ("PIX", "dinheiro"):
        raise HTTPException(422, "Forma inválida")
    if valor_min is not None and valor_max is not None and valor_min > valor_max:
        raise HTTPException(422, "Valor máximo não pode ser menor que o mínimo")
    if origem_registro not in (None, "manual", "nao_informada"):
        raise HTTPException(422, "Origem de registro inválida")
    q = _query(db)
    if valor_min is not None: q = q.filter(Pagamento.valor >= valor_min)
    if valor_max is not None: q = q.filter(Pagamento.valor <= valor_max)
    if origem_registro == "manual": q = q.filter(Pagamento.origem_registro == "manual")
    if origem_registro == "nao_informada": q = q.filter(Pagamento.origem_registro.is_(None))
    if cliente_id:
        q = q.filter(Pagamento.cliente_id == cliente_id)
    if fornecedor_id:
        q = q.filter(Pagamento.fornecedor_id == fornecedor_id)
    if tipo:
        q = q.filter(Pagamento.tipo == tipo)
    if forma:
        q = q.filter(Pagamento.forma == forma)
    permitidos = {k: getattr(Pagamento, k) for k in ("codigo", "tipo", "forma", "valor", "data", "cancelado")}
    permitidos.update(cliente_nome=q.column_descriptions[4]["expr"], fornecedor_nome=q.column_descriptions[5]["expr"])
    q = ordenar(q, ordenar_por, direcao, permitidos, Pagamento.id, Pagamento.id.desc())
    return [_out(row) for row in q.offset(max(offset, 0)).limit(min(max(limit, 1), 500))]


@r.post("", status_code=201)
def criar(body: PagamentoIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    anterior = db.query(Pagamento).filter_by(chave_idempotencia=body.chave_idempotencia).first()
    if anterior:
        if not _igual_pagamento(anterior, body):
            raise HTTPException(409, "Chave de requisição já usada com dados diferentes")
        return _summary(db, anterior.id)
    if body.data > hoje():
        raise HTTPException(422, "Pagamento não pode ter data futura")
    ref = bloquear_referencia(db, body.referencia_externa)
    _ref_livre(db, ref)
    if db.query(Pagamento.id).filter_by(referencia_chave=body.referencia_externa.casefold()).first():
        raise HTTPException(409, "Referência externa já cadastrada")
    if body.cliente_id:
        _titular(db, body.cliente_id, "representante")
    if body.fornecedor_id:
        _titular(db, body.fornecedor_id, "fornecedor")
    if body.tipo == "repasse_fornecedor":
        fonte = _pagamento(db, body.pagamento_origem_id)
        _cas(db, fonte)
        if fonte.tipo != "cliente_loja" or fonte.cancelado or body.data < fonte.data:
            db.rollback()
            raise HTTPException(422, "Repasse exige recebimento na loja ativo e data posterior ou igual")
        saldo = _summary(db, fonte.id)["saldo_para_repasse"]
        if body.valor > Decimal(str(saldo)):
            db.rollback()
            raise HTTPException(422, "Repasse excede o saldo do recebimento")
    meta = resolver_catalogos(db, "pagamentos", operacao_id=body.operacao_id, forma_id=body.forma_id, forma=body.forma)
    dados = body.model_dump(exclude={"declaracao_novo_pagamento"})
    dados.update(meta)
    dados["valor"] = float(body.valor)
    dados["origem_registro"] = "manual"
    if body.data_hora_transacao is not None:
        dados["data_hora_transacao"] = body.data_hora_transacao.astimezone(timezone.utc).replace(tzinfo=None)
    dados["referencia_chave"] = body.referencia_externa.casefold()
    p = Pagamento(**dados, codigo="PAG-TMP-" + uuid4().hex[:12], created_by=u.id)
    db.add(p)
    try:
        db.flush()
    except (IntegrityError, OperationalError):
        db.rollback()
        raise HTTPException(409, "Pagamento já registrado ou alterado em outra sessão")
    p.codigo = f"PAG-{p.id:06d}"
    audit(db, u.id, "pagamento_novo_registrado", "pagamentos", p.id, depois=body.model_dump())
    _commit(db)
    return _summary(db, p.id)


@r.get("/{pid}")
def detalhe(pid: int, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    _pagamento(db, pid)
    out = _summary(db, pid)
    out["aplicacoes"] = [_app_out(db, a) for a in db.query(PagamentoAplicacao).filter_by(pagamento_id=pid).order_by(PagamentoAplicacao.id)]
    out["repasses"] = [{"id": p.id, "codigo": p.codigo, "valor": p.valor, "data": p.data, "cancelado": p.cancelado}
        for p in db.query(Pagamento).filter_by(pagamento_origem_id=pid).order_by(Pagamento.id)]
    out["anexos"] = [_anexo_out(a, db) for a in db.query(PagamentoAnexo).filter_by(pagamento_id=pid, ativo=True).order_by(PagamentoAnexo.id)]
    return out


@r.post("/{pid}/aplicacoes", status_code=201)
def aplicar(pid: int, body: AplicacaoIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    p = _pagamento(db, pid)
    anterior = db.query(PagamentoAplicacao).filter_by(pagamento_id=pid, chave_idempotencia=body.chave_idempotencia).first()
    if anterior:
        igual = all(getattr(anterior, k) == getattr(body, k) for k in ("nota_id", "relacao", "data", "referencia", "observacao", "fornecedor_confirmou")) and anterior.referencia_confirmacao == (body.referencia_confirmacao or "") and Decimal(str(anterior.valor)) == body.valor
        if not igual:
            raise HTTPException(409, "Chave de requisição já usada com dados diferentes")
        return _app_out(db, anterior)
    n = db.get(NotaObrigacao, body.nota_id)
    if not n:
        raise HTTPException(404, "Nota não encontrada")
    ref = bloquear_referencia(db, body.referencia)
    _ref_livre(db, ref)
    # Todas as operações conjuntas bloqueiam pagamento antes da nota.
    _cas(db, p)
    nota_cas(db, n)
    if p.cancelado or n.cancelada:
        db.rollback()
        raise HTTPException(422, "Pagamento ou nota cancelados")
    titular = p.cliente_id if body.relacao == "cliente" else p.fornecedor_id
    if n.relacao != body.relacao or n.pessoa_id != titular:
        db.rollback()
        raise HTTPException(422, "Nota e pagamento devem pertencer à mesma relação e titular")
    if body.data > hoje() or body.data < max(p.data, n.data_emissao):
        db.rollback()
        raise HTTPException(422, "Data da aplicação incompatível com nota ou pagamento")
    budget = _summary(db, pid)["orcamentos"][body.relacao]
    saldo_nota = round(n.valor_original - nota_total(db, n.id), 2)
    if body.valor > Decimal(str(budget["saldo_disponivel"])) or body.valor > Decimal(str(saldo_nota)):
        db.rollback()
        raise HTTPException(422, "Valor excede o saldo da relação ou da nota")
    a = PagamentoAplicacao(pagamento_id=pid, **body.model_dump(exclude={"valor", "referencia_confirmacao"}),
        referencia_confirmacao=body.referencia_confirmacao or "", valor=float(body.valor), created_by=u.id)
    db.add(a)
    db.flush()
    ab = NotaAbatimento(nota_id=n.id, pagamento_aplicacao_id=a.id, valor=a.valor, data=a.data,
        referencia=a.referencia, referencia_chave=chave_referencia(a.referencia),
        observacao=a.observacao, origem="pagamento",
        chave_idempotencia="pagamento-aplicacao:" + str(a.id), created_by=u.id)
    db.add(ab)
    audit(db, u.id, "pagamento_aplicado", "pagamento_aplicacoes", a.id, depois=body.model_dump())
    _commit(db)
    return _app_out(db, a)


@r.post("/{pid}/aplicacoes/{aid}/estornar")
def estornar(pid: int, aid: int, body: DesfazerIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    confere_senha(u, body.senha)
    p = _pagamento(db, pid)
    a = db.query(PagamentoAplicacao).filter_by(id=aid, pagamento_id=pid).first()
    if not a:
        raise HTTPException(404, "Aplicação não encontrada")
    if a.acerto_id is not None:
        raise HTTPException(422, "Aplicação pertence a acerto: estorne o acerto inteiro")
    n = db.get(NotaObrigacao, a.nota_id)
    _cas(db, p)
    nota_cas(db, n)
    if a.estornada or n.cancelada or p.cancelado:
        db.rollback()
        raise HTTPException(422, "Aplicação estornada ou registro cancelado")
    ab = db.query(NotaAbatimento).filter_by(pagamento_aplicacao_id=a.id).one()
    a.estornada, ab.estornado = True, True
    db.add(PagamentoAplicacaoEstorno(aplicacao_id=aid, motivo=body.motivo, created_by=u.id))
    db.add(NotaAbatimentoEstorno(abatimento_id=ab.id, motivo=body.motivo, created_by=u.id))
    audit(db, u.id, "pagamento_aplicacao_estornada", "pagamento_aplicacoes", aid, depois={"motivo": body.motivo})
    _commit(db)
    return _app_out(db, a)


@r.post("/{pid}/cancelar")
def cancelar(pid: int, body: DesfazerIn, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    confere_senha(u, body.senha)
    p = _pagamento(db, pid)
    # Repasse e recebimento precisam do mesmo lock para liberar/reusar saldo.
    if p.pagamento_origem_id:
        _cas(db, _pagamento(db, p.pagamento_origem_id))
    _cas(db, p)
    if p.cancelado or db.query(CreditoConta.id).filter_by(pagamento_id=pid, revertido=False).first() or db.query(PagamentoAplicacao.id).filter_by(pagamento_id=pid, estornada=False).first()\
        or db.query(Pagamento.id).filter_by(pagamento_origem_id=pid, cancelado=False).first():
        db.rollback()
        raise HTTPException(422, "Pagamento cancelado ou com aplicações/repasses ativos: desfaça antes")
    p.cancelado = True
    p.motivo_cancelamento = body.motivo
    audit(db, u.id, "pagamento_cancelado", "pagamentos", pid, depois={"motivo": body.motivo})
    _commit(db)
    return _summary(db, pid)


def _anexo(db, pid, aid):
    _pagamento(db, pid)
    a = db.query(PagamentoAnexo).filter_by(id=aid, pagamento_id=pid, ativo=True).first()
    if not a:
        raise HTTPException(404, "Anexo não encontrado")
    return a


@r.post("/{pid}/anexos", status_code=201)
async def anexar(pid: int, f: UploadFile = File(...), db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    p = _pagamento(db, pid)
    if p.cancelado:
        raise HTTPException(422, "Pagamento cancelado")
    data = await f.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    await f.close()
    if not data or len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(422, "Arquivo vazio ou maior que o limite permitido")
    nome = re.sub(r"[\x00-\x1f\x7f]", "", (f.filename or "anexo").replace("\\", "/").split("/")[-1])[:180]
    ext = Path(nome).suffix.lower()
    formato = ".pdf" if data.startswith(b"%PDF-") else ".png" if data.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg" if data.startswith(b"\xff\xd8\xff") else ".webp" if data[:4] == b"RIFF" and data[8:12] == b"WEBP" else None
    if not formato or ext not in ((".jpg", ".jpeg") if formato == ".jpg" else (formato,)):
        raise HTTPException(422, "Formato deve ser PDF, PNG, JPEG ou WebP válido e compatível com a extensão")
    _cas(db, p)
    path = upload_root(db, base=UPLOAD_DIR) / "pagamentos" / str(pid) / (uuid4().hex + formato)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.resolve() != path.parent:
        raise HTTPException(503, "Diretório de anexos indisponível")
    try:
        path.write_bytes(data)
        a = PagamentoAnexo(pagamento_id=pid, nome_original=nome, arquivo_path=str(path), tamanho=len(data), created_by=u.id)
        db.add(a)
        db.flush()
        audit(db, u.id, "pagamento_anexo_adicionado", "pagamento_anexos", a.id, depois={"nome": nome, "tamanho": len(data)})
        db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    return _anexo_out(a, db)


@r.get("/{pid}/anexos/{aid}/arquivo")
def baixar(pid: int, aid: int, inline: bool = False, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    a = _anexo(db, pid, aid)
    path = Path(a.arquivo_path).resolve()
    root = upload_root(db, base=UPLOAD_DIR) / "pagamentos" / str(pid)
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(404, "Arquivo indisponível")
    return resposta_arquivo(path, a.nome_original, inline)


@r.delete("/{pid}/anexos/{aid}")
def desativar(pid: int, aid: int, db: Session = Depends(get_db), u: User = Depends(ESCRITA)):
    a = _anexo(db, pid, aid)
    a.ativo = False
    audit(db, u.id, "pagamento_anexo_desativado", "pagamento_anexos", aid)
    _commit(db)
    return {"id": aid, "ativo": False}
