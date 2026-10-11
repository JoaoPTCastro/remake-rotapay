"""Exportação CSV (SHOULD HAVE do PRD).

Formato pensado para Excel PT-BR: separador `;`, BOM UTF-8 e datas ISO.
Toda exportação gera auditoria `relatorio_exportado` (§26 analytics).
"""
import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Movimentacao, Conciliacao, Lancamento, Projecao, Pessoa, User
from ..auth import need
from ..audit import audit

r = APIRouter(prefix="/export", tags=["export"])


def _csv(nome: str, header: list[str], rows: list[list]):
    buf = io.StringIO()
    buf.write("\ufeff")  # BOM: Excel abre UTF-8 direto
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    data = buf.getvalue().encode("utf-8")
    return StreamingResponse(iter([data]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{nome}"'})


def _nomes(db: Session) -> dict:
    return {p.id: p.nome for p in db.query(Pessoa).all()}


@r.get("/movimentacoes.csv")
def exp_mov(data_ini: str | None = None, data_fim: str | None = None,
            representante_id: int | None = None, fornecedor_id: int | None = None,
            status: str | None = None, q: str = "", chave: str = "",
            com_link: bool | None = None,
            db: Session = Depends(get_db),
            u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    query = db.query(Movimentacao).order_by(Movimentacao.id)
    if data_ini:
        query = query.filter(Movimentacao.data_pix >= data_ini)
    if data_fim:
        query = query.filter(Movimentacao.data_pix <= data_fim)
    if representante_id:
        query = query.filter(Movimentacao.representante_id == representante_id)
    if fornecedor_id:
        query = query.filter(Movimentacao.fornecedor_id == fornecedor_id)
    if status:
        query = query.filter(Movimentacao.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter((Movimentacao.codigo.ilike(like)) |
                             (Movimentacao.remetente.ilike(like)) |
                             (Movimentacao.destinatario.ilike(like)))
    if chave:
        like = f"%{chave}%"
        query = query.outerjoin(Pessoa, Pessoa.id == Movimentacao.fornecedor_id).filter(
            (Movimentacao.remetente.ilike(like)) |
            (Movimentacao.destinatario.ilike(like)) |
            (Pessoa.chave_pix.ilike(like)))
    if com_link is True:
        query = query.filter(Movimentacao.link_token != "")
    elif com_link is False:
        query = query.filter(Movimentacao.link_token == "")
    nomes = _nomes(db)
    rows = [[m.codigo, str(m.data_pix), f"{m.valor:.2f}", f"{m.saldo_disponivel:.2f}",
             m.remetente, nomes.get(m.representante_id or -1, ""), m.destinatario,
             nomes.get(m.fornecedor_id or -1, ""), m.status,
             m.autor, m.forma_pagamento, m.natureza,
             "sim" if m.comprovante_path else "não", m.observacao]
            for m in query.all()]
    audit(db, u.id, "relatorio_exportado", "movimentacoes", None,
          depois={"filtros": {"status": status, "q": q}, "linhas": len(rows)})
    db.commit()
    return _csv("movimentacoes.csv",
                ["codigo", "data_pix", "valor", "saldo_disponivel", "remetente",
                 "representante", "destinatario", "fornecedor", "status",
                 "autor", "forma_pagamento", "natureza",
                 "comprovante", "observacao"], rows)


@r.get("/conciliacoes.csv")
def exp_conc(db: Session = Depends(get_db),
             u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    rows = [[c.id, c.movimentacao_id, c.alvo_tipo, c.alvo_id, f"{c.valor:.2f}",
             str(c.data), "sim" if c.estornada else "não"]
            for c in db.query(Conciliacao).order_by(Conciliacao.id).all()]
    audit(db, u.id, "relatorio_exportado", "conciliacoes", None, depois={"linhas": len(rows)})
    db.commit()
    return _csv("conciliacoes.csv",
                ["id", "movimentacao_id", "alvo_tipo", "alvo_id", "valor", "data", "estornada"], rows)


@r.get("/lancamentos.csv")
def exp_lanc(tipo: str | None = None, status: str | None = None,
             db: Session = Depends(get_db),
             u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    query = db.query(Lancamento).order_by(Lancamento.id)
    if tipo:
        query = query.filter(Lancamento.tipo == tipo)
    if status:
        query = query.filter(Lancamento.status == status)
    nomes = _nomes(db)
    rows = [[l.id, l.tipo, l.natureza, f"{l.valor:.2f}", f"{l.saldo_aberto:.2f}",
             str(l.data), nomes.get(l.representante_id or -1, ""),
             nomes.get(l.fornecedor_id or -1, ""), l.descricao, l.origem, l.status]
            for l in query.all()]
    audit(db, u.id, "relatorio_exportado", "lancamentos", None, depois={"linhas": len(rows)})
    db.commit()
    return _csv("lancamentos.csv",
                ["id", "tipo", "natureza", "valor", "saldo_aberto", "data",
                 "representante", "fornecedor", "descricao", "origem", "status"], rows)


@r.get("/projecoes.csv")
def exp_proj(db: Session = Depends(get_db),
             u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    nomes = _nomes(db)
    rows = [[p.id, nomes.get(p.representante_id, ""), nomes.get(p.fornecedor_id, ""),
             f"{p.valor_projetado:.2f}", f"{p.valor_conciliado:.2f}", f"{p.saldo:.2f}",
             str(p.data_prevista) if p.data_prevista else "", p.status, p.observacao]
            for p in db.query(Projecao).order_by(Projecao.id).all()]
    audit(db, u.id, "relatorio_exportado", "projecoes", None, depois={"linhas": len(rows)})
    db.commit()
    return _csv("projecoes.csv",
                ["id", "representante", "fornecedor", "valor_projetado",
                 "valor_conciliado", "saldo", "data_prevista", "status", "observacao"], rows)


@r.get("/posicao-fornecedores.csv")
def exp_pos(db: Session = Depends(get_db),
            u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    """Relatório gerencial: quanto devemos por fornecedor (débitos em aberto)."""
    from sqlalchemy import func
    agg = db.query(Lancamento.fornecedor_id,
                   func.coalesce(func.sum(Lancamento.saldo_aberto), 0)).filter(
        Lancamento.status.in_(["aberto", "parcial"]),
        Lancamento.fornecedor_id.isnot(None)).group_by(Lancamento.fornecedor_id).all()
    nomes = _nomes(db)
    rows = [[f, nomes.get(f, ""), f"{float(s):.2f}"] for f, s in agg]
    audit(db, u.id, "relatorio_exportado", "relatorio", None, depois={"linhas": len(rows)})
    db.commit()
    return _csv("posicao-fornecedores.csv", ["fornecedor_id", "fornecedor", "saldo_aberto"], rows)


@r.get("/auditoria.csv")
def exp_audit(acao: str = "", entidade: str = "", usuario_id: int | None = None,
              db: Session = Depends(get_db),
              u: User = Depends(need("admin", "financeiro"))):
    from ..models import AuditLog
    q = db.query(AuditLog).order_by(AuditLog.id.desc())
    if acao:
        q = q.filter(AuditLog.acao.ilike(f"%{acao}%"))
    if entidade:
        q = q.filter(AuditLog.entidade == entidade)
    if usuario_id:
        q = q.filter(AuditLog.usuario_id == usuario_id)
    rows = [[a.id, a.acao, a.entidade, a.entidade_id or "", a.usuario_id or "",
             a.ip or "", str(a.created_at)] for a in q.limit(2000).all()]
    audit(db, u.id, "relatorio_exportado", "auditoria", None, depois={"linhas": len(rows)})
    db.commit()
    return _csv("auditoria.csv",
                ["id", "acao", "entidade", "entidade_id", "usuario_id", "ip", "quando"], rows)
