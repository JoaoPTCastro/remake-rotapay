from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Projecao, Lancamento, Conciliacao, Movimentacao, Pessoa, User
from ..auth import need, current_user, confere_senha
from ..schemas import ProjecaoIn, LancIn, ConcilIn
from ..services import conciliar, estornar, check_projecao_unica, tolerancia_usada
from ..intelligence import propostas_projecao
from ..audit import audit

rp = APIRouter(prefix="/projecoes", tags=["projecoes"])
rl = APIRouter(prefix="/lancamentos", tags=["lancamentos"])
rc = APIRouter(prefix="/conciliacoes", tags=["conciliacoes"])
rs = APIRouter(tags=["simulacao"])


@rs.get("/simulacao")
def simular(representante_id: int, fornecedor_id: int,
            db: Session = Depends(get_db),
            u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    """Quanto o rifeiro pode pagar sem exceder dívidas (atas §solução 4).

    Não persiste nada: retorna PIX disponível, dívida aberta, tolerância e
    quanto pode ser pago (e quanto viraria crédito explícito).
    """
    pix = db.query(func.coalesce(func.sum(Movimentacao.saldo_disponivel), 0)).filter(
        Movimentacao.representante_id == representante_id,
        Movimentacao.fornecedor_id == fornecedor_id,
        Movimentacao.status.in_(["disponivel", "parcial"])).scalar() or 0
    divida = db.query(func.coalesce(func.sum(Lancamento.saldo_aberto), 0)).filter(
        Lancamento.fornecedor_id == fornecedor_id,
        Lancamento.tipo.in_(["debito", "despesa", "imposto", "salario"]),
        Lancamento.status.in_(["aberto", "parcial"])).scalar() or 0
    forn = db.get(Pessoa, fornecedor_id)
    teto = float(forn.tolerancia_credito) if forn else 0.0
    usada = tolerancia_usada(db, fornecedor_id)
    margem = round(max(teto - usada, 0.0), 2)
    pode_pagar = round(min(float(pix), float(divida) + margem), 2)
    return {"pix_disponivel": round(float(pix), 2),
            "divida_aberta": round(float(divida), 2),
            "tolerancia": teto, "tolerancia_em_uso": usada,
            "pode_pagar_sem_exceder": round(min(float(pix), float(divida)), 2),
            "pode_pagar_total": pode_pagar,
            "credito_gerado_se_pagar_tudo": round(max(pode_pagar - float(divida), 0.0), 2)}


# ---- Projeções ----
@rp.get("")
def list_proj(status: str | None = None, fornecedor_id: int | None = None,
              limit: int = 100, offset: int = 0,
              db: Session = Depends(get_db),
              u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    limit = min(max(limit, 1), 500)
    q = db.query(Projecao).order_by(Projecao.id.desc())
    if status:
        q = q.filter(Projecao.status == status)
    if fornecedor_id:
        q = q.filter(Projecao.fornecedor_id == fornecedor_id)
    return [{"id": p.id, "representante_id": p.representante_id, "fornecedor_id": p.fornecedor_id,
             "valor_projetado": p.valor_projetado, "valor_conciliado": p.valor_conciliado,
             "saldo": p.saldo, "status": p.status, "data_prevista": str(p.data_prevista) if p.data_prevista else None}
            for p in q.offset(offset).limit(limit).all()]


@rp.post("", status_code=201)
def create_proj(body: ProjecaoIn, db: Session = Depends(get_db),
                u: User = Depends(need("admin", "financeiro", "operador"))):
    check_projecao_unica(db, body.representante_id, body.fornecedor_id)
    p = Projecao(**body.model_dump(), valor_conciliado=0.0, status="aberta")
    db.add(p)
    db.flush()
    audit(db, u.id, "projecao_criada", "projecoes", p.id, depois=body.model_dump())
    db.commit()
    return {"id": p.id, "saldo": p.saldo}


@rp.post("/automaticas")
def projecoes_automaticas(aplicar: bool = False, db: Session = Depends(get_db),
                          u: User = Depends(need("admin", "financeiro", "operador"))):
    """Compõe projeções PIX × dívida na ordem do rodízio.

    Sem aplicar: só propõe. Com aplicar=true: cria as que ainda não existem
    (RN-006), cada uma auditada. Nada é conciliado sozinho.
    """
    propostas = propostas_projecao(db)
    if not aplicar:
        return {"aplicado": False, "propostas": propostas}
    criadas, ignoradas = [], []
    for p in propostas:
        if p["ja_existe"]:
            ignoradas.append({"motivo": "já existe projeção aberta para o par",
                              "representante_id": p["representante_id"],
                              "fornecedor_id": p["fornecedor_id"]})
            continue
        try:
            check_projecao_unica(db, p["representante_id"], p["fornecedor_id"])
        except HTTPException:
            ignoradas.append({"motivo": "RN-006: projeção aberta para o par",
                              "representante_id": p["representante_id"],
                              "fornecedor_id": p["fornecedor_id"]})
            continue
        nova = Projecao(representante_id=p["representante_id"],
                        fornecedor_id=p["fornecedor_id"],
                        valor_projetado=p["valor_proposto"], valor_conciliado=0.0,
                        status="aberta",
                        observacao="Automática (rodízio) — revisar antes de conciliar",
                        )
        db.add(nova)
        db.flush()
        audit(db, u.id, "projecao_criada", "projecoes", nova.id,
              depois={"automatica": True, "valor": p["valor_proposto"],
                      "motivo": p["motivo"]})
        criadas.append({"id": nova.id, "representante_id": p["representante_id"],
                        "fornecedor_id": p["fornecedor_id"],
                        "valor_projetado": p["valor_proposto"]})
    db.commit()
    return {"aplicado": True, "criadas": criadas, "ignoradas": ignoradas}


@rp.post("/{pid}/cancelar")
def cancel_proj(pid: int, body: dict, db: Session = Depends(get_db),
                u: User = Depends(need("admin", "financeiro"))):
    confere_senha(u, body.get("senha"))
    p = db.get(Projecao, pid)
    if not p:
        raise HTTPException(404, "Não encontrada")
    if p.valor_conciliado > 0:
        raise HTTPException(422, "Projeção com conciliação: estorne antes de cancelar")
    p.status = "cancelada"
    audit(db, u.id, "projecao_atualizada", "projecoes", p.id, depois={"status": "cancelada"})
    db.commit()
    return {"id": p.id, "status": p.status}


# ---- Lançamentos ----
@rl.get("")
def list_lanc(tipo: str | None = None, fornecedor_id: int | None = None,
              status: str | None = None, limit: int = 100, offset: int = 0,
              db: Session = Depends(get_db),
              u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    limit = min(max(limit, 1), 500)
    q = db.query(Lancamento).order_by(Lancamento.id.desc())
    if tipo:
        q = q.filter(Lancamento.tipo == tipo)
    if fornecedor_id:
        q = q.filter(Lancamento.fornecedor_id == fornecedor_id)
    if status:
        q = q.filter(Lancamento.status == status)
    return [{"id": l.id, "tipo": l.tipo, "valor": l.valor, "saldo_aberto": l.saldo_aberto,
             "status": l.status, "fornecedor_id": l.fornecedor_id,
             "representante_id": l.representante_id, "descricao": l.descricao,
             "prioridade": l.prioridade,
             "data": str(l.data)} for l in q.offset(offset).limit(limit).all()]


@rl.post("", status_code=201)
def create_lanc(body: LancIn, db: Session = Depends(get_db),
                u: User = Depends(need("admin", "financeiro", "operador"))):
    l = Lancamento(**body.model_dump(), saldo_aberto=body.valor, status="aberto", created_by=u.id)
    db.add(l)
    db.flush()
    audit(db, u.id, "lancamento_criado", "lancamentos", l.id, depois=body.model_dump())
    db.commit()
    return {"id": l.id}


@rl.post("/{lid}/cancelar")
def cancel_lanc(lid: int, body: dict, db: Session = Depends(get_db),
                u: User = Depends(need("admin", "financeiro"))):
    confere_senha(u, body.get("senha"))
    l = db.get(Lancamento, lid)
    if not l:
        raise HTTPException(404, "Não encontrado")
    if l.saldo_aberto != l.valor:
        raise HTTPException(422, "Lançamento com conciliação: estorne antes de cancelar")
    l.status = "cancelado"
    audit(db, u.id, "lancamento_cancelado", "lancamentos", l.id)
    db.commit()
    return {"id": l.id, "status": l.status}


# ---- Conciliações ----
@rc.get("")
def list_conc(db: Session = Depends(get_db),
              u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    q = db.query(Conciliacao).order_by(Conciliacao.id.desc()).limit(500).all()
    return [{"id": c.id, "movimentacao_id": c.movimentacao_id, "alvo_tipo": c.alvo_tipo,
             "alvo_id": c.alvo_id, "valor": c.valor, "estornada": c.estornada} for c in q]


@rc.post("", status_code=201)
def create_conc(body: ConcilIn, db: Session = Depends(get_db),
                u: User = Depends(need("admin", "financeiro", "operador"))):
    c = conciliar(db, body.movimentacao_id, body.alvo_tipo, body.alvo_id, body.valor, u.id)
    audit(db, u.id, "conciliacao_criada", "conciliacoes", c.id, depois=body.model_dump())
    db.commit()
    return {"id": c.id, "valor": c.valor}


@rc.post("/{cid}/estornar")
def estornar_conc(cid: int, body: dict, db: Session = Depends(get_db),
                  u: User = Depends(need("admin", "financeiro"))):
    confere_senha(u, body.get("senha"))
    c = estornar(db, cid, body.get("motivo", ""), u.id)
    audit(db, u.id, "conciliacao_estornada", "conciliacoes", c.id)
    db.commit()
    return {"id": c.id, "estornada": True}
