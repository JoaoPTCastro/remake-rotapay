"""Alertas e consulta autenticada dos destinos históricos de links."""
from typing import Literal
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, or_, func, select, literal, union_all
from sqlalchemy.orm import Session, aliased
from ..auth import need
from ..database import get_db
from ..models import Pessoa, PessoaChavePix, LinkPagamento, Movimentacao, NotaObrigacao
from ..cadastros import hoje, SNAPSHOT_FIELDS
from .notas import _consulta_notas
from .links import _out

r = APIRouter(prefix="/cadastros", tags=["cadastros-consulta"])
LEITURA = need("admin", "financeiro", "operador", "consulta")


@r.get("/alertas")
def alertas(response: Response, tipo: Literal["divida_sem_chave", "chave_expirada", "chave_a_vencer"] | None = None,
    limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), u=Depends(LEITURA)):
    response.headers["Cache-Control"] = "private, no-store"
    nq, _, _ = _consulta_notas(db)
    abatido = nq.column_descriptions[1]["expr"]
    debts = nq.with_entities(NotaObrigacao.pessoa_id.label("pid"),
        func.sum(func.round(NotaObrigacao.valor_original - abatido, 2)).label("divida")).filter(
        NotaObrigacao.relacao == "fornecedor", NotaObrigacao.cancelada == False,
        func.round(NotaObrigacao.valor_original - abatido, 2) > 0).group_by(NotaObrigacao.pessoa_id).subquery()
    validkey = select(PessoaChavePix.id).where(PessoaChavePix.pessoa_id == Pessoa.id,
        PessoaChavePix.principal == True, PessoaChavePix.ativo == True, PessoaChavePix.chave != "",
        or_(PessoaChavePix.validade == None, PessoaChavePix.validade >= hoje())).exists()
    anykey = select(PessoaChavePix.id).where(PessoaChavePix.pessoa_id == Pessoa.id).exists()
    # Usa o mesmo fallback do cadastro legado somente enquanto não existem chaves filhas.
    valid = and_(Pessoa.ativo == True, or_(validkey, and_(~anykey, Pessoa.chave_pix != "")))
    debtsq = select(literal("divida_sem_chave").label("tipo"), Pessoa.id.label("pessoa_id"), Pessoa.nome.label("pessoa_nome"),
        literal("fornecedor").label("relacao"), literal(None).label("chave_id"), literal(None).label("validade"), debts.c.divida.label("divida_aberta")).join(debts, debts.c.pid == Pessoa.id).where(~valid)
    def keyquery(kind, condition):
        return select(literal(kind).label("tipo"), Pessoa.id.label("pessoa_id"), Pessoa.nome.label("pessoa_nome"),
            literal(None).label("relacao"), PessoaChavePix.id.label("chave_id"), PessoaChavePix.validade.label("validade"), literal(None).label("divida_aberta")).join(
            PessoaChavePix, PessoaChavePix.pessoa_id == Pessoa.id).where(PessoaChavePix.ativo == True,
            PessoaChavePix.categoria == "temporaria", condition)
    combined = union_all(debtsq, keyquery("chave_expirada", PessoaChavePix.validade < hoje()),
        keyquery("chave_a_vencer", and_(PessoaChavePix.validade >= hoje(), PessoaChavePix.validade <= hoje() + timedelta(days=30)))).subquery()
    q = db.query(combined)
    if tipo:
        q = q.filter(combined.c.tipo == tipo)
    total = q.count()
    items = []
    for row in q.order_by(combined.c.pessoa_id, combined.c.tipo, combined.c.chave_id).offset(offset).limit(limit).all():
        d = dict(row._mapping)
        validity = d["validade"]
        if isinstance(validity, str):
            from datetime import date
            validity = date.fromisoformat(validity)
        d["dias"] = (validity - hoje()).days if validity else None
        d["id"] = f'{d["tipo"]}:{d["pessoa_id"]}:{d["chave_id"] or 0}'
        d["divida_aberta"] = round(float(d["divida_aberta"]), 2) if d["divida_aberta"] is not None else None
        items.append(d)
    return {"itens": items, "total": total, "limit": limit, "offset": offset, "tem_mais": offset + len(items) < total}


@r.get("/{pid}/links")
def links(pid: int, response: Response, status: Literal["ativo", "revogado", "usado", "semuso", "bloqueado_destino"] | None = None,
    limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), u=Depends(LEITURA)):
    response.headers["Cache-Control"] = "private, no-store"
    if not db.get(Pessoa, pid):
        raise HTTPException(404, "Cadastro não encontrado")
    key = aliased(PessoaChavePix)
    supplier = aliased(Pessoa)
    countmov = select(func.count(Movimentacao.id)).where(Movimentacao.link_token == LinkPagamento.token).correlate(LinkPagamento).scalar_subquery()
    valid = and_(LinkPagamento.destino_fixado == True, key.id != None, key.pessoa_id == LinkPagamento.fornecedor_id,
        key.ativo == True, supplier.ativo == True,
        or_(key.validade == None, key.validade >= hoje()),
        *(func.coalesce(getattr(key, field), "") == getattr(LinkPagamento, snapshot) for field, snapshot in SNAPSHOT_FIELDS))
    q = db.query(LinkPagamento, countmov.label("usos"), valid.label("valido")).outerjoin(key, key.id == LinkPagamento.chave_pix_id).outerjoin(supplier, supplier.id == LinkPagamento.fornecedor_id).filter(
        or_(LinkPagamento.representante_id == pid, LinkPagamento.fornecedor_id == pid))
    if status == "ativo": q = q.filter(LinkPagamento.ativo == True)
    if status == "revogado": q = q.filter(LinkPagamento.ativo == False)
    if status == "usado": q = q.filter(countmov > 0)
    if status == "semuso": q = q.filter(countmov == 0)
    if status == "bloqueado_destino": q = q.filter(or_(~valid, valid == None))
    total = q.count()
    rows = q.order_by(LinkPagamento.id.desc()).offset(offset).limit(limit).all()
    items = []
    for l, count, okay in rows:
        items.append({**_out(l, db), "usado": count > 0, "movimentacoes_quantidade": count,
            "destino_bloqueado": not bool(okay), "destino_fixado": l.destino_fixado,
            "chave_destino": l.chave_snapshot, "titular_destino": l.titular_snapshot,
            "banco_destino": l.banco_snapshot, "conta_destino": l.conta_snapshot})
    return {"itens": items, "total": total, "limit": limit, "offset": offset, "tem_mais": offset + len(items) < total}
