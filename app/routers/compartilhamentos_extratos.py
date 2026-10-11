"""Extrato compartilhado restrito: segredo só no header, nenhum efeito financeiro."""
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import update
from sqlalchemy.orm import Session
from ..auth import need
from ..audit import audit
from ..database import get_db
from ..ambientes import autor_financeiro_ativo
from ..models import CompartilhamentoExtrato, Pessoa, User, NotaObrigacao
from . import extratos, notas, pagamentos

r = APIRouter(tags=["compartilhamentos_extratos"])
GESTAO = need("admin", "financeiro")


class CompartilhamentoIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    relacao: Literal["cliente", "fornecedor"]
    destinatario: str = Field(min_length=2, max_length=160)
    validade_dias: int = Field(default=7, ge=1, le=30, strict=True)


class RevogarIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    motivo: str = Field(min_length=3, max_length=500)


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _utc(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


def _tipo_compativel(pessoa, relacao):
    # Cadastros de cliente usam o tipo legado normalizado representante.
    esperado = "representante" if relacao == "cliente" else "fornecedor"
    return pessoa.tipo in (esperado, "ambos")


def _status(link, pessoa, autor, db=None):
    if link.revogado:
        return "revogado"
    if link.expira_em <= _now():
        return "expirado"
    if not pessoa or not pessoa.ativo or not _tipo_compativel(pessoa, link.relacao) or not autor or not autor.ativo or autor.perfil not in ("admin", "financeiro"):
        return "indisponivel"
    if db is not None and not autor_financeiro_ativo(db, link.created_by):
        return "indisponivel"
    return "ativo"


def _out(link, pessoa, autor, db=None):
    return {"id": link.id, "relacao": link.relacao, "destinatario": link.destinatario,
            "created_by": link.created_by, "criado_por_nome": autor.nome if autor else None,
            "created_at": _utc(link.created_at), "expira_em": _utc(link.expira_em),
            "revogado": link.revogado, "revogado_em": _utc(link.revogado_em),
            "motivo_revogacao": link.motivo_revogacao, "status": _status(link, pessoa, autor, db)}


def _pessoa(db, pid):
    p = db.get(Pessoa, pid)
    if not p:
        raise HTTPException(404, "Cadastro não encontrado")
    return p


@r.post("/extratos/{pid}/compartilhamentos", status_code=201)
def criar(pid: int, body: CompartilhamentoIn, response: Response, db: Session = Depends(get_db), u: User = Depends(GESTAO)):
    response.headers["Cache-Control"] = "private, no-store"
    p = _pessoa(db, pid)
    if not p.ativo:
        raise HTTPException(422, "Cadastro inativo não permite compartilhar extrato")
    if not _tipo_compativel(p, body.relacao):
        raise HTTPException(422, "Relação incompatível com o cadastro")
    token = secrets.token_urlsafe(32)
    link = CompartilhamentoExtrato(pessoa_id=pid, relacao=body.relacao, destinatario=body.destinatario,
        token_hash=hashlib.sha256(token.encode()).hexdigest(), created_by=u.id,
        expira_em=_now() + timedelta(days=body.validade_dias))
    db.add(link)
    db.flush()
    audit(db, u.id, "extrato_compartilhamento_criado", link.__tablename__, link.id,
          depois={"pessoa_id": pid, "relacao": body.relacao, "validade_dias": body.validade_dias})
    db.commit()
    db.refresh(link)
    return {**_out(link, p, u, db), "token": token, "organizacao_id": db.info.get("organizacao_id", 1)}


@r.get("/extratos/{pid}/compartilhamentos")
def listar(pid: int, response: Response, relacao: Literal["cliente", "fornecedor"] | None = None,
           limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
           db: Session = Depends(get_db), u: User = Depends(GESTAO)):
    response.headers["Cache-Control"] = "private, no-store"
    p = _pessoa(db, pid)
    q = db.query(CompartilhamentoExtrato).filter_by(pessoa_id=pid)
    if relacao:
        q = q.filter_by(relacao=relacao)
    total = q.count()
    rows = q.order_by(CompartilhamentoExtrato.id.desc()).offset(offset).limit(limit).all()
    creators = {a.id: a for a in db.query(User).filter(User.id.in_({l.created_by for l in rows})).all()}
    return {"itens": [_out(l, p, creators.get(l.created_by), db) for l in rows], "total": total,
            "limit": limit, "offset": offset, "tem_mais": offset + len(rows) < total}


@r.post("/extratos/{pid}/compartilhamentos/{cid}/revogar")
def revogar(pid: int, cid: int, body: RevogarIn, response: Response, db: Session = Depends(get_db), u: User = Depends(GESTAO)):
    response.headers["Cache-Control"] = "private, no-store"
    p = _pessoa(db, pid)
    now = _now()
    result = db.execute(update(CompartilhamentoExtrato).where(CompartilhamentoExtrato.id == cid,
        CompartilhamentoExtrato.pessoa_id == pid, CompartilhamentoExtrato.revogado.is_(False))
        .values(revogado=True, revogado_em=now, revogado_por=u.id, motivo_revogacao=body.motivo))
    link = db.query(CompartilhamentoExtrato).filter_by(id=cid, pessoa_id=pid).first()
    if not link:
        db.rollback()
        raise HTTPException(404, "Compartilhamento não encontrado")
    if result.rowcount:
        audit(db, u.id, "extrato_compartilhamento_revogado", link.__tablename__, link.id,
              depois={"pessoa_id": pid, "relacao": link.relacao, "motivo": body.motivo})
    db.commit()
    db.refresh(link)
    return _out(link, p, db.get(User, link.created_by), db)


def _page(items, total, limit, offset):
    return {"itens": items, "total": total, "limit": limit, "offset": offset, "tem_mais": offset + len(items) < total}


@r.get("/publico/extratos")
def publico(request: Request, response: Response,
            notas_limit: int = Query(50, ge=1, le=100), notas_offset: int = Query(0, ge=0, le=100000),
            pagamentos_limit: int = Query(50, ge=1, le=100), pagamentos_offset: int = Query(0, ge=0, le=100000),
            db: Session = Depends(get_db)):
    allowed = {"notas_limit", "notas_offset", "pagamentos_limit", "pagamentos_offset"}
    if any(k not in allowed for k in request.query_params) or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params):
        raise HTTPException(422, "Parâmetros inválidos")
    authorization = request.headers.get("authorization", "")
    if not re.fullmatch(r"Bearer [A-Za-z0-9_-]{43}", authorization):
        raise HTTPException(404, "Extrato indisponível")
    token = authorization[7:]
    link = db.query(CompartilhamentoExtrato).filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).first()
    if not link:
        raise HTTPException(404, "Extrato indisponível")
    p, autor = db.get(Pessoa, link.pessoa_id), db.get(User, link.created_by)
    if _status(link, p, autor, db) != "ativo":
        raise HTTPException(404, "Extrato indisponível")
    pid, relation = link.pessoa_id, link.relacao
    internal = extratos.resumo(pid, relation, response, db, autor)["totais_globais"]
    totals = {"notas": internal["notas"], "pagamentos": internal["pagamentos"]}
    nq, state, late = notas._consulta_notas(db)
    nq = nq.filter(NotaObrigacao.pessoa_id == pid, NotaObrigacao.relacao == relation)
    n_total = nq.count()
    n_items = []
    for n, applied, _, status, overdue in nq.add_columns(state, late).order_by(NotaObrigacao.id.desc()).offset(notas_offset).limit(notas_limit).all():
        n_items.append({"numero_documento": n.numero_documento, "data_emissao": n.data_emissao,
            "vencimento": n.vencimento, "valor_original": n.valor_original, "valor_abatido": round(float(applied), 2),
            "saldo_aberto": round(n.valor_original - float(applied), 2), "status": status, "em_atraso": bool(overdue)})
    pq = extratos._pag_query(db, pid, relation)
    p_total = pq.count()
    p_items = []
    for row in pq.order_by(pagamentos.Pagamento.id.desc()).offset(pagamentos_offset).limit(pagamentos_limit).all():
        payment = row[0]
        applied, credit = row[1 if relation == "cliente" else 2], row[6 if relation == "cliente" else 7]
        budget = pagamentos._orcamento(payment, relation, applied, credit)
        p_items.append({"data": payment.data, "forma": payment.forma, "valor": payment.valor,
            "valor_aplicado": budget["aplicado"], "destinado_credito": budget["destinado_credito"],
            "saldo_disponivel": budget["saldo_disponivel"], "status": budget["status"]})
    return {"relacao": relation, "escopo": "compartilhado_restrito", "expira_em": _utc(link.expira_em),
            "totais_globais": totals, "notas": _page(n_items, n_total, notas_limit, notas_offset),
            "pagamentos": _page(p_items, p_total, pagamentos_limit, pagamentos_offset)}
