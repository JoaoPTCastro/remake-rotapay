import json
from datetime import date, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (AuditLog, Comprovante, Conciliacao, Lancamento,
                      Movimentacao, Projecao)
from ..auth import need
from ..intelligence import fila_pagamentos
from ..models import User

r = APIRouter(tags=["dashboard"])


@r.get("/dashboard")
def dashboard(db: Session = Depends(get_db),
              u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    hoje = date.today()
    limite_antigo = hoje - timedelta(days=7)
    inicio_recente = hoje - timedelta(days=6)
    limite_proximo = hoje + timedelta(days=7)

    obrigacoes_abertas, a_pagar = db.query(
        func.count(Lancamento.id),
        func.coalesce(func.sum(Lancamento.saldo_aberto), 0)).filter(
        Lancamento.tipo.in_(["debito", "despesa", "imposto", "salario"]),
        Lancamento.status.in_(["aberto", "parcial"])).one()
    pix_pend, disponivel, pix_antigos, saldo_pix_antigos = db.query(
        func.count(Movimentacao.id),
        func.coalesce(func.sum(Movimentacao.saldo_disponivel), 0),
        func.coalesce(func.sum(case(
            (Movimentacao.data_pix <= limite_antigo, 1), else_=0)), 0),
        func.coalesce(func.sum(case(
            (Movimentacao.data_pix <= limite_antigo,
             Movimentacao.saldo_disponivel), else_=0)), 0),
    ).filter(Movimentacao.status.in_(["disponivel", "parcial"])).one()
    pix_conc = db.query(func.count(Movimentacao.id)).filter(
        Movimentacao.status == "conciliada").scalar() or 0
    proj_abertas, obrigacoes_proximas, saldo_obrigacoes_proximas = db.query(
        func.count(Projecao.id),
        func.coalesce(func.sum(case(
            (Projecao.data_prevista.between(hoje, limite_proximo), 1),
            else_=0)), 0),
        func.coalesce(func.sum(case(
            (Projecao.data_prevista.between(hoje, limite_proximo),
             Projecao.valor_projetado - Projecao.valor_conciliado),
            else_=0)), 0),
    ).filter(Projecao.status.in_(["aberta", "parcial"])).one()
    por_forn = db.query(Lancamento.fornecedor_id,
                        func.coalesce(func.sum(Lancamento.saldo_aberto), 0)).filter(
        Lancamento.status.in_(["aberto", "parcial"]),
        Lancamento.fornecedor_id.isnot(None)).group_by(Lancamento.fornecedor_id).all()
    ultimas = db.query(Lancamento.fornecedor_id, Lancamento.data,
                       Lancamento.valor).filter(
        Lancamento.tipo.in_(["debito", "despesa", "imposto", "salario"]),
        Lancamento.fornecedor_id.isnot(None)).order_by(
        Lancamento.data.desc(), Lancamento.id.desc()).limit(2000).all()
    ult = {}
    for f, d, v in ultimas:
        ult.setdefault(f, {"data": str(d), "valor": round(float(v), 2)})

    comprovantes_aguardando, comprovantes_registro, comprovantes_revisao = db.query(
        func.coalesce(func.sum(case((
            (Comprovante.etapa == "recebido") |
            (Comprovante.sugestao_status == "pendente"), 1), else_=0)), 0),
        func.coalesce(func.sum(case(
            (Comprovante.etapa == "recebido", 1), else_=0)), 0),
        func.coalesce(func.sum(case(
            (Comprovante.sugestao_status == "pendente", 1), else_=0)), 0),
    ).one()
    conciliacoes_recentes, valor_conciliado_recente = db.query(
        func.count(Conciliacao.id),
        func.coalesce(func.sum(Conciliacao.valor), 0),
    ).filter(
        Conciliacao.estornada.is_(False),
        Conciliacao.data.between(inicio_recente, hoje),
    ).one()

    if pix_antigos:
        mensagem_pix = (
            "1 PIX está pendente há 7 dias ou mais. Revise as movimentações mais antigas."
            if pix_antigos == 1 else
            f"{pix_antigos} PIX estão pendentes há 7 dias ou mais. "
            "Revise as movimentações mais antigas.")
    elif pix_pend:
        mensagem_pix = (
            "1 PIX aguarda conciliação. Revise o saldo disponível."
            if pix_pend == 1 else
            f"{pix_pend} PIX aguardam conciliação. Revise os saldos disponíveis.")
    else:
        mensagem_pix = "Não há PIX pendentes para conciliar."

    insights = [
        {"codigo": "pix_pendentes", "nivel": "atencao" if pix_pend else "ok",
         "mensagem": mensagem_pix,
         "acao": "Revisar movimentações" if pix_pend else None,
         "destino": "/movimentacoes" if pix_pend else None},
        {"codigo": "comprovantes_aguardando",
         "nivel": "atencao" if comprovantes_aguardando else "ok",
         "mensagem": (
             ("1 comprovante aguarda tratamento. Revise os comprovantes nas movimentações."
              if comprovantes_aguardando == 1 else
              f"{comprovantes_aguardando} comprovantes aguardam tratamento. "
              "Revise os comprovantes nas movimentações.")
             if comprovantes_aguardando else
             "Não há comprovantes aguardando tratamento."),
         "acao": "Revisar movimentações" if comprovantes_aguardando else None,
         "destino": "/movimentacoes" if comprovantes_aguardando else None},
        {"codigo": "obrigacoes_abertas",
         "nivel": "atencao" if obrigacoes_abertas else "ok",
         "mensagem": (
             ("1 obrigação financeira está aberta. Revise os lançamentos."
              if obrigacoes_abertas == 1 else
              f"{obrigacoes_abertas} obrigações financeiras estão abertas. "
              "Revise os lançamentos.")
             if obrigacoes_abertas else "Não há obrigações financeiras abertas."),
         "acao": "Revisar lançamentos" if obrigacoes_abertas else None,
         "destino": "/lancamentos" if obrigacoes_abertas else None},
        {"codigo": "obrigacoes_proximas",
         "nivel": "atencao" if obrigacoes_proximas else "ok",
         "mensagem": (
             ("1 projeção de pagamento está prevista para os próximos 7 dias."
              if obrigacoes_proximas == 1 else
              f"{obrigacoes_proximas} projeções de pagamento estão previstas "
              "para os próximos 7 dias.")
             if obrigacoes_proximas else
             "Não há obrigações previstas para os próximos 7 dias."),
         "acao": "Revisar projeções" if obrigacoes_proximas else None,
         "destino": "/projecoes" if obrigacoes_proximas else None},
        {"codigo": "conciliacoes_recentes",
         "nivel": "info" if conciliacoes_recentes else "ok",
         "mensagem": (
             ("1 conciliação foi registrada nos últimos 7 dias."
              if conciliacoes_recentes == 1 else
              f"{conciliacoes_recentes} conciliações foram registradas nos últimos 7 dias.")
             if conciliacoes_recentes else
             "Nenhuma conciliação foi registrada nos últimos 7 dias."),
         "acao": "Ver conciliações" if conciliacoes_recentes else None,
         "destino": "/conciliacoes" if conciliacoes_recentes else None},
    ]

    return {"total_a_pagar": round(a_pagar, 2),
            "pix_disponivel": round(disponivel, 2),
            "pix_pendentes": pix_pend,
            "pix_conciliados": pix_conc,
            "projecoes_abertas": proj_abertas,
            "por_fornecedor": [{"fornecedor_id": f, "saldo": round(s, 2),
                                 "ultima_compra": ult.get(f)} for f, s in por_forn],
            "resumo_operacional": {
                "pix_pendentes": {"quantidade": pix_pend,
                                    "saldo": round(float(disponivel), 2)},
                "pix_antigos": {"quantidade": pix_antigos,
                                 "saldo": round(float(saldo_pix_antigos), 2),
                                 "limite_dias": 7},
                "comprovantes_aguardando": {
                    "total": comprovantes_aguardando,
                    "registro": comprovantes_registro,
                    "revisao": comprovantes_revisao},
                "obrigacoes_abertas": {
                    "quantidade": obrigacoes_abertas,
                    "saldo": round(float(a_pagar), 2)},
                "obrigacoes_proximas": {
                    "quantidade": obrigacoes_proximas,
                    "saldo": round(float(saldo_obrigacoes_proximas), 2),
                    "janela_dias": 7},
                "conciliacoes_recentes": {
                    "quantidade": conciliacoes_recentes,
                    "valor": round(float(valor_conciliado_recente), 2),
                    "janela_dias": 7}},
            "insights": insights}


@r.get("/fila-pagamentos")
def fila(db: Session = Depends(get_db),
         u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    """Rodízio: por fornecedor, nota mais antiga em aberto + faltante + ordem."""
    return fila_pagamentos(db)


@r.get("/pix-de-links")
def pix_de_links(limit: int = 50, db: Session = Depends(get_db),
                 u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    """Últimos PIX rastreáveis gerados pelos links (QR/cobrança/gateway)."""
    limit = min(max(limit, 1), 200)
    rows = db.query(Movimentacao).filter(
        Movimentacao.link_token != "").order_by(Movimentacao.id.desc()).limit(limit).all()
    return [{"id": m.id, "codigo": m.codigo, "data_pix": str(m.data_pix),
             "valor": m.valor, "status": m.status,
             "representante_id": m.representante_id, "fornecedor_id": m.fornecedor_id,
             "link_token": m.link_token} for m in rows]


@r.get("/metricas")
def metricas(db: Session = Depends(get_db),
             u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    """Sprint D2: números da operação (atas) — dia, automático vs manual, erros."""
    por_dia = db.query(Comprovante.data_comprovante, func.count(Comprovante.id)).filter(
        Comprovante.data_comprovante.isnot(None)).group_by(
        Comprovante.data_comprovante).order_by(Comprovante.data_comprovante).all()
    conc_dia = db.query(Conciliacao.data, func.count(Conciliacao.id)).filter(
        Conciliacao.estornada.is_(False)).group_by(Conciliacao.data).order_by(
        Conciliacao.data).all()
    auto = db.query(func.count(Comprovante.id)).filter(
        Comprovante.origem == "gateway").scalar() or 0
    manual = db.query(func.count(Comprovante.id)).filter(
        Comprovante.origem != "gateway").scalar() or 0
    creditos = db.query(func.coalesce(func.sum(Lancamento.saldo_aberto), 0)).filter(
        Lancamento.tipo == "credito",
        Lancamento.status.in_(["aberto", "parcial"])).scalar() or 0
    return {"comprovantes_por_dia": [{"data": str(d), "qtd": q} for d, q in por_dia],
            "conciliacoes_por_dia": [{"data": str(d), "qtd": q} for d, q in conc_dia],
            "auto_gateway": auto, "manual_upload": manual,
            "creditos_em_aberto": round(float(creditos), 2)}


_AUDIT_FIELDS = {
    "users": {"nome", "email", "perfil", "ativo", "motivo"},
    "loja": {"nome", "documento", "telefone", "email", "endereco", "tem_logo", "motivo"},
    "pessoas": {"nome", "tipo", "ativo", "apelido", "prazo_dias", "prioridade", "motivo"},
    "catalogos_config": {"id", "tipo", "nome", "ativo", "forma_base", "aplicavel_em", "prazo_dias", "version"},
    "pagamentos": {"id", "tipo", "forma", "valor", "data", "ativo", "cliente_id", "fornecedor_id", "motivo"},
    "notas_obrigacoes": {"id", "relacao", "pessoa_id", "valor", "data_emissao", "vencimento", "ativo", "motivo"},
    "acertos": {"id", "relacao", "pessoa_id", "valor", "ativo", "status", "motivo"},
    "creditos_conta": {"id", "relacao", "pessoa_id", "valor", "ativo", "tipo", "motivo"},
}


def _audit_detalhes(raw, entidade, perfil):
    if entidade in ("users", "loja") and perfil != "admin":
        return None
    try:
        data = json.loads(raw) if raw else None
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    allowed = _AUDIT_FIELDS.get(entidade, set())
    # Somente escalares explicitamente permitidos; nunca devolver objetos livres.
    return {k: v for k, v in data.items() if k in allowed and (v is None or type(v) in (str, int, float, bool))}


@r.get("/auditoria")
def auditoria(entidade: str | None = None, entidade_id: int | None = None,
              acao: str = "", usuario_id: int | None = None,
              db: Session = Depends(get_db),
              u: User = Depends(need("admin", "financeiro"))):
    q = db.query(AuditLog).order_by(AuditLog.id.desc())
    if entidade:
        q = q.filter(AuditLog.entidade == entidade)
    if entidade_id:
        q = q.filter(AuditLog.entidade_id == entidade_id)
    if acao:
        q = q.filter(AuditLog.acao.ilike(f"%{acao}%"))
    if usuario_id:
        q = q.filter(AuditLog.usuario_id == usuario_id)
    rows = q.limit(200).all()
    users = {user.id: user.nome for user in db.query(User).filter(User.id.in_({a.usuario_id for a in rows if a.usuario_id is not None})).all()}
    return [{"id": a.id, "acao": a.acao, "entidade": a.entidade, "entidade_id": a.entidade_id,
             "usuario_id": a.usuario_id, "usuario_nome": users.get(a.usuario_id),
             "ip": a.ip, "created_at": a.created_at.replace(tzinfo=timezone.utc).isoformat(),
             "antes": _audit_detalhes(a.antes, a.entidade, u.perfil),
             "depois": _audit_detalhes(a.depois, a.entidade, u.perfil)} for a in rows]
