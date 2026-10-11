"""Extrato individual de leitura: domínio novo, sem inferir caixa ou legado."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy import func, case, select, literal, cast, String, union_all, true
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import need
from ..models import (Pessoa, User, NotaObrigacao, NotaAbatimento, NotaAbatimentoEstorno,
    Pagamento, PagamentoAplicacao, CreditoConta, CreditoAplicacao, CreditoReversao,
    Acerto, AcertoItem, AcertoEvento, AuditLog)
from . import notas, pagamentos, creditos, acertos

r = APIRouter(prefix="/extratos", tags=["extratos"])
LEITURA = need("admin", "financeiro", "operador", "consulta")


def _conta(db, pid, relacao, response):
    response.headers["Cache-Control"] = "private, no-store"
    if relacao not in ("cliente", "fornecedor"):
        raise HTTPException(422, "Relação inválida")
    p = db.get(Pessoa, pid)
    if not p:
        raise HTTPException(404, "Cadastro não encontrado")
    return p


def _periodo(de, ate):
    if de and ate and de > ate:
        raise HTTPException(422, "Data inicial deve anteceder ou igualar a final")


def _pag_query(db, pid, relacao):
    q = pagamentos._query(db)
    coluna = Pagamento.cliente_id if relacao == "cliente" else Pagamento.fornecedor_id
    tipos = ("cliente_loja", "cliente_fornecedor") if relacao == "cliente" else ("cliente_fornecedor", "repasse_fornecedor")
    return q.filter(coluna == pid, Pagamento.tipo.in_(tipos))


def _page(q, formatar, limit, offset, de=None, ate=None, status=None):
    limit, offset = min(max(limit, 1), 500), max(offset, 0)
    total = q.order_by(None).count()
    rows = q.offset(offset).limit(limit).all()
    return {"itens": [formatar(row) for row in rows], "total_filtrado": total, "offset": offset,
        "limit": limit, "tem_mais": offset + len(rows) < total,
        "filtros": {"data_de": de, "data_ate": ate, "status": status}, "escopo": "lista_filtrada"}


def _filtrar(q, coluna, de, ate):
    _periodo(de, ate)
    if de:
        q = q.filter(coluna >= de)
    if ate:
        q = q.filter(coluna <= ate)
    return q


def _sum(expr):
    return func.coalesce(func.sum(expr), 0)


@r.get("/{pid}")
def resumo(pid: int, relacao: str, response: Response, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    p = _conta(db, pid, relacao, response)
    from ..visao_geral import contas_statement, totais
    row = db.execute(contas_statement(db, relacao, pid)).mappings().one()
    return {"pessoa": {"id": p.id, "nome": p.nome, "tipo": p.tipo, "ativo": p.ativo}, "relacao": relacao,
        "escopo": "dominio_novo", "totais_globais": totais(row)}


@r.get("/{pid}/notas")
def listar_notas(pid: int, relacao: str, response: Response, data_de: date | None = None, data_ate: date | None = None,
                 status: str | None = None, limit: int = Query(default=100, ge=1, le=100), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    _conta(db, pid, relacao, response)
    q, estado, _ = notas._consulta_notas(db)
    q = q.filter(NotaObrigacao.pessoa_id == pid, NotaObrigacao.relacao == relacao)
    if status:
        if status not in ("aberto", "parcial", "quitado", "cancelado"):
            raise HTTPException(422, "Status de nota inválido")
        q = q.filter(estado == status)
    q = _filtrar(q, NotaObrigacao.data_emissao, data_de, data_ate).order_by(NotaObrigacao.id.desc())
    return _page(q, lambda row: notas._out(db, *row), limit, offset, data_de, data_ate, status)


@r.get("/{pid}/pagamentos")
def listar_pagamentos(pid: int, relacao: str, response: Response, data_de: date | None = None, data_ate: date | None = None,
                      status: str | None = None, limit: int = Query(default=100, ge=1, le=100), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    _conta(db, pid, relacao, response)
    q = _pag_query(db, pid, relacao)
    applied = q.column_descriptions[1 if relacao == "cliente" else 2]["expr"]
    destinado = q.column_descriptions[6 if relacao == "cliente" else 7]["expr"]
    saldo = func.round(Pagamento.valor - applied - destinado, 2)
    estado = case((Pagamento.cancelado == True, "cancelado"), (saldo == 0, "utilizado"),
        (applied + destinado > 0, "parcial"), else_="disponivel")
    if status:
        if status not in ("disponivel", "parcial", "utilizado", "cancelado", "inelegivel"):
            raise HTTPException(422, "Status de pagamento inválido")
        q = q.filter(estado == status)
    q = _filtrar(q, Pagamento.data, data_de, data_ate).order_by(Pagamento.id.desc())
    return _page(q, pagamentos._out, limit, offset, data_de, data_ate, status)


@r.get("/{pid}/creditos")
def listar_creditos(pid: int, relacao: str, response: Response, data_de: date | None = None, data_ate: date | None = None,
                    status: str | None = None, limit: int = Query(default=100, ge=1, le=100), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    _conta(db, pid, relacao, response)
    q, estado = creditos._query(db)
    q = q.filter(CreditoConta.pessoa_id == pid, CreditoConta.relacao == relacao)
    if status:
        if status not in ("disponivel", "parcial", "utilizado", "revertido"):
            raise HTTPException(422, "Status de crédito inválido")
        q = q.filter(estado == status)
    q = _filtrar(q, CreditoConta.data, data_de, data_ate).order_by(CreditoConta.id.desc())
    return _page(q, creditos._out, limit, offset, data_de, data_ate, status)


@r.get("/{pid}/acertos")
def listar_acertos(pid: int, relacao: str, response: Response, data_de: date | None = None, data_ate: date | None = None,
                   status: str | None = None, limit: int = Query(default=100, ge=1, le=100), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    _conta(db, pid, relacao, response)
    total = db.query(AcertoItem.acerto_id.label("aid"), func.sum(AcertoItem.valor).label("total")).group_by(AcertoItem.acerto_id).subquery()
    q = db.query(Acerto, total.c.total, Pessoa.nome).join(Pessoa, Pessoa.id == Acerto.pessoa_id).join(total, total.c.aid == Acerto.id)\
        .filter(Acerto.pessoa_id == pid, Acerto.relacao == relacao)
    if status:
        if status not in acertos.ESTADOS:
            raise HTTPException(422, "Status de acerto inválido")
        q = q.filter(Acerto.status == status)
    q = _filtrar(q, Acerto.data, data_de, data_ate).order_by(Acerto.id.desc())
    return _page(q, lambda row: acertos._out(db, row[0], total=row[1], nome=row[2]), limit, offset, data_de, data_ate, status)


def _event(tipo, eid, quando, data_op, valor, referencia, descricao,
           nota_id=None, pagamento_id=None, credito_id=None, acerto_id=None):
    n = nota_id if nota_id is not None else literal(None)
    p = pagamento_id if pagamento_id is not None else literal(None)
    c = credito_id if credito_id is not None else literal(None)
    a = acerto_id if acerto_id is not None else literal(None)
    url = case((a.isnot(None), literal("/acertos/") + cast(a, String)),
        (c.isnot(None), literal("/creditos/") + cast(c, String)),
        (p.isnot(None), literal("/pagamentos/") + cast(p, String)),
        else_=literal("/notas/") + cast(n, String))
    return select((literal(tipo + ":") + cast(eid, String)).label("id"), literal(tipo).label("tipo"),
        quando.label("data_hora"), data_op.label("data_operacao"), valor.label("valor"),
        referencia.label("referencia"), descricao.label("descricao"), n.label("nota_id"),
        p.label("pagamento_id"), c.label("credito_id"), a.label("acerto_id"), url.label("url"))


def _timeline_query(db, pid, relacao):
    pscope = Pagamento.cliente_id == pid if relacao == "cliente" else Pagamento.fornecedor_id == pid
    nscope = (NotaObrigacao.pessoa_id == pid) & (NotaObrigacao.relacao == relacao)
    cscope = (CreditoConta.pessoa_id == pid) & (CreditoConta.relacao == relacao)
    ascope = (Acerto.pessoa_id == pid) & (Acerto.relacao == relacao)
    queries = [
        _event("pagamento_registrado", Pagamento.id, Pagamento.created_at, Pagamento.data, Pagamento.valor,
            Pagamento.referencia_externa, Pagamento.observacao, pagamento_id=Pagamento.id).where(pscope),
        _event("nota_criada", NotaObrigacao.id, NotaObrigacao.created_at, NotaObrigacao.data_emissao,
            NotaObrigacao.valor_original, NotaObrigacao.numero_documento, NotaObrigacao.descricao,
            nota_id=NotaObrigacao.id).where(nscope),
        _event("credito_reconhecido", CreditoConta.id, CreditoConta.created_at, CreditoConta.data,
            CreditoConta.valor_original, CreditoConta.referencia, CreditoConta.observacao,
            credito_id=CreditoConta.id).where(cscope),
        _event("credito_revertido", CreditoReversao.id, CreditoReversao.created_at, literal(None),
            CreditoConta.valor_original, CreditoConta.referencia, CreditoReversao.motivo,
            credito_id=CreditoConta.id).select_from(CreditoReversao).join(CreditoConta,
                CreditoConta.id == CreditoReversao.credito_id).where(cscope)]
    aid = func.coalesce(PagamentoAplicacao.acerto_id, CreditoAplicacao.acerto_id)
    def vincular(q):
        return q.join(NotaObrigacao, NotaObrigacao.id == NotaAbatimento.nota_id)\
            .outerjoin(PagamentoAplicacao, PagamentoAplicacao.id == NotaAbatimento.pagamento_aplicacao_id)\
            .outerjoin(CreditoAplicacao, CreditoAplicacao.id == NotaAbatimento.credito_aplicacao_id).where(nscope)
    queries.append(vincular(_event("nota_abatida", NotaAbatimento.id, NotaAbatimento.created_at,
        NotaAbatimento.data, NotaAbatimento.valor, NotaAbatimento.referencia, NotaAbatimento.observacao,
        nota_id=NotaAbatimento.nota_id, pagamento_id=PagamentoAplicacao.pagamento_id,
        credito_id=CreditoAplicacao.credito_id, acerto_id=aid).select_from(NotaAbatimento)))
    queries.append(vincular(_event("nota_abatimento_estornado", NotaAbatimentoEstorno.id,
        NotaAbatimentoEstorno.created_at, literal(None), NotaAbatimento.valor, NotaAbatimento.referencia,
        NotaAbatimentoEstorno.motivo, nota_id=NotaAbatimento.nota_id, pagamento_id=PagamentoAplicacao.pagamento_id,
        credito_id=CreditoAplicacao.credito_id, acerto_id=aid).select_from(NotaAbatimentoEstorno)
            .join(NotaAbatimento, NotaAbatimento.id == NotaAbatimentoEstorno.abatimento_id)))
    # Cancelamentos são eventos auditados; updated_at não reconstrói quando ocorreram.
    queries.append(_event("nota_cancelada", AuditLog.id, AuditLog.created_at, literal(None), literal(None),
        NotaObrigacao.numero_documento, NotaObrigacao.motivo_cancelamento, nota_id=NotaObrigacao.id)
        .select_from(AuditLog).join(NotaObrigacao, NotaObrigacao.id == AuditLog.entidade_id)
        .where(nscope, AuditLog.entidade == "notas_obrigacoes", AuditLog.acao == "nota_cancelada"))
    queries.append(_event("pagamento_cancelado", AuditLog.id, AuditLog.created_at, literal(None), literal(None),
        Pagamento.referencia_externa, Pagamento.motivo_cancelamento, pagamento_id=Pagamento.id)
        .select_from(AuditLog).join(Pagamento, Pagamento.id == AuditLog.entidade_id)
        .where(pscope, AuditLog.entidade == "pagamentos", AuditLog.acao == "pagamento_cancelado"))
    # Eventos do lote são informativos: os abatimentos aparecem somente pelos itens de nota.
    for acao in ("criado", "enviado", "confirmado", "efetivado", "estornado", "cancelado"):
        queries.append(_event("acerto_" + acao, AcertoEvento.id, AcertoEvento.created_at, Acerto.data,
            literal(None), AcertoEvento.referencia, AcertoEvento.observacao, acerto_id=Acerto.id)
            .select_from(AcertoEvento).join(Acerto, Acerto.id == AcertoEvento.acerto_id)
            .where(ascope, AcertoEvento.acao == acao))
    combined = union_all(*queries).subquery()
    return db.query(combined)


@r.get("/{pid}/timeline")
def timeline(pid: int, relacao: str, response: Response, data_de: date | None = None, data_ate: date | None = None,
             limit: int = Query(default=100, ge=1, le=100), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    _conta(db, pid, relacao, response)
    _periodo(data_de, data_ate)
    q = _timeline_query(db, pid, relacao)
    coluna = q.column_descriptions[2]["expr"]
    sp = ZoneInfo("America/Sao_Paulo")
    if data_de:
        inicio = datetime.combine(data_de, time.min, tzinfo=sp).astimezone(timezone.utc).replace(tzinfo=None)
        q = q.filter(coluna >= inicio)
    if data_ate:
        try:
            final = datetime.combine(data_ate + timedelta(days=1), time.min, tzinfo=sp).astimezone(timezone.utc).replace(tzinfo=None)
        except OverflowError:
            raise HTTPException(422, "Data final excede o limite do calendário")
        q = q.filter(coluna < final)
    q = q.order_by(coluna.desc(), q.column_descriptions[0]["expr"].desc())
    def formatar(row):
        out = dict(row._mapping)
        momento = out["data_hora"]
        if momento is not None:
            out["data_hora"] = momento.replace(tzinfo=timezone.utc).isoformat()
        if out["valor"] is not None:
            out["valor"] = round(float(out["valor"]), 2)
        return out
    return _page(q, formatar, limit, offset, data_de, data_ate)
