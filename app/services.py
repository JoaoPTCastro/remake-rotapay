"""Regras de conciliação: RN-003, RN-006, RN-007 + política de excedente.

Concorrência: conciliar/estornar rodam sob _LOCK (processo único + SQLite)
para impedir double-spend entre threads. Não vale para multi-processo —
migrar para SELECT FOR UPDATE no Postgres (ver ADR).

Política de excedente (§10 RF-052, premissa do produto):
- Conciliação NUNCA gera crédito automático.
- Se PIX > obrigação: quita a obrigação; o restante permanece em
  movimentacao.saldo_disponivel para uso futuro (status parcial).
- Criação de crédito com fornecedor só via POST /lancamentos tipo=credito,
  explícito e auditado.
"""
from datetime import date
from threading import Lock
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .models import Movimentacao, Projecao, Lancamento, Conciliacao, Estorno, Pessoa

# Processo único + SQLite: lock em memória impede double-spend entre
# threads (dois POST concorrentes). Não vale para multi-processo —
# migrar para SELECT FOR UPDATE no Postgres (ver ADR).
_LOCK = Lock()


def _mov_status(m: Movimentacao):
    if m.saldo_disponivel <= 0:
        m.status = "conciliada"
    elif abs(m.saldo_disponivel - m.valor) < 0.005:
        if m.status != "cancelada":
            m.status = "disponivel"
    else:
        m.status = "parcial"


def tolerancia_usada(db: Session, forn_id: int) -> float:
    """Soma dos créditos explícitos por tolerância ainda em aberto."""
    rows = db.query(Lancamento).filter(
        Lancamento.fornecedor_id == forn_id,
        Lancamento.tipo == "credito",
        Lancamento.origem == "tolerancia",
        Lancamento.status.in_(["aberto", "parcial"]),
    ).all()
    return round(sum(l.saldo_aberto for l in rows), 2)


def conciliar(db: Session, mov_id: int, alvo_tipo: str, alvo_id: int,
              valor: float, usuario_id: int | None) -> Conciliacao:
    with _LOCK:
        return _conciliar(db, mov_id, alvo_tipo, alvo_id, valor, usuario_id)


def _credito_de(c: Conciliacao, db: Session) -> Lancamento | None:
    """Crédito de tolerância gerado por esta conciliação (qualquer status)."""
    return db.query(Lancamento).filter(
        Lancamento.origem == "tolerancia",
        Lancamento.descricao == f"Crédito por tolerância (conciliação #{c.id})",
    ).first()


def _conciliar(db: Session, mov_id: int, alvo_tipo: str, alvo_id: int,
               valor: float, usuario_id: int | None) -> Conciliacao:
    if valor <= 0:
        raise HTTPException(422, "Valor deve ser maior que zero (RN-002)")
    m: Movimentacao | None = db.get(Movimentacao, mov_id)
    if not m:
        raise HTTPException(404, "Movimentação não encontrada")
    if m.status == "cancelada":
        raise HTTPException(422, "Movimentação cancelada não pode ser conciliada")
    if valor - m.saldo_disponivel > 0.005:  # RN-003
        raise HTTPException(422, f"Valor excede saldo disponível ({m.saldo_disponivel:.2f})")

    if alvo_tipo == "projecao":
        alvo: Projecao | None = db.get(Projecao, alvo_id)
        if not alvo:
            raise HTTPException(404, "Projeção não encontrada")
        if alvo.status in ("conciliada", "cancelada"):
            raise HTTPException(422, "Projeção encerrada")
        saldo_alvo = alvo.saldo
        forn_id = alvo.fornecedor_id
    else:
        alvo = db.get(Lancamento, alvo_id)
        if not alvo:
            raise HTTPException(404, "Lançamento não encontrado")
        if alvo.status in ("quitado", "cancelado"):
            raise HTTPException(422, "Lançamento encerrado")
        saldo_alvo = alvo.saldo_aberto
        forn_id = alvo.fornecedor_id

    # Excedente (RF-052 + tolerância Sprint 4): só dentro da tolerância do
    # fornecedor — e sempre como crédito EXPLÍCITO e auditável, nunca silencioso.
    excesso = round(valor - saldo_alvo, 2)
    credito_id = None
    if excesso > 0.005:
        forn = db.get(Pessoa, forn_id) if forn_id else None
        teto = float(forn.tolerancia_credito) if forn else 0.0
        usada = tolerancia_usada(db, forn_id) if forn_id else 0.0
        if excesso + usada - teto > 0.005:
            raise HTTPException(422, f"Valor excede o saldo em R$ {excesso:.2f}. "
                                     f"Tolerância do fornecedor: R$ {teto:.2f} "
                                     f"(em uso: R$ {usada:.2f}). Excedente permanece "
                                     "no PIX — sem crédito automático.")
        if alvo_tipo == "projecao":
            alvo.valor_conciliado = round(alvo.valor_conciliado + saldo_alvo, 2)
            alvo.status = "conciliada"
        else:
            alvo.saldo_aberto = 0.0
            alvo.status = "quitado"
        cred = Lancamento(tipo="credito", natureza="tolerancia", valor=excesso,
                          saldo_aberto=excesso, data=date.today(),
                          representante_id=m.representante_id,
                          fornecedor_id=forn_id,
                          descricao="Crédito por tolerância (pendente)",
                          origem="tolerancia", status="aberto", created_by=usuario_id)
        db.add(cred)
        db.flush()
        credito_id = cred.id
    elif alvo_tipo == "projecao":
        alvo.valor_conciliado = round(alvo.valor_conciliado + valor, 2)
        alvo.status = "conciliada" if alvo.saldo <= 0.005 else "parcial"
    else:
        alvo.saldo_aberto = round(alvo.saldo_aberto - valor, 2)
        alvo.status = "quitado" if alvo.saldo_aberto <= 0.005 else "parcial"

    m.saldo_disponivel = round(m.saldo_disponivel - valor, 2)
    _mov_status(m)
    c = Conciliacao(movimentacao_id=m.id, alvo_tipo=alvo_tipo, alvo_id=alvo_id,
                    valor=round(valor, 2), data=date.today(), usuario_id=usuario_id)
    db.add(c)
    db.flush()
    if credito_id:
        cred.descricao = f"Crédito por tolerância (conciliação #{c.id})"
    return c


def estornar(db: Session, conc_id: int, motivo: str, usuario_id: int | None):
    with _LOCK:
        return _estornar(db, conc_id, motivo, usuario_id)


def _estornar(db: Session, conc_id: int, motivo: str, usuario_id: int | None):
    c: Conciliacao | None = db.get(Conciliacao, conc_id)
    if not c:
        raise HTTPException(404, "Conciliação não encontrada")
    if c.estornada:
        raise HTTPException(422, "Conciliação já estornada")
    # Reverte só o que foi consumido do alvo: se gerou crédito de tolerância,
    # a parte do excesso não saiu do alvo (virou crédito à parte).
    cred = _credito_de(c, db)
    excesso = round(cred.valor, 2) if cred else 0.0
    consumido = round(c.valor - excesso, 2)
    m = db.get(Movimentacao, c.movimentacao_id)
    m.saldo_disponivel = round(m.saldo_disponivel + c.valor, 2)
    _mov_status(m)
    if c.alvo_tipo == "projecao":
        a = db.get(Projecao, c.alvo_id)
        a.valor_conciliado = round(a.valor_conciliado - consumido, 2)
        a.status = "aberta" if a.valor_conciliado <= 0.005 else "parcial"
    else:
        a = db.get(Lancamento, c.alvo_id)
        a.saldo_aberto = round(a.saldo_aberto + consumido, 2)
        a.status = "aberto" if abs(a.saldo_aberto - a.valor) < 0.005 else "parcial"
    c.estornada = True
    db.add(Estorno(conciliacao_id=c.id, motivo=motivo, usuario_id=usuario_id))
    # cancela o crédito de tolerância gerado por esta conciliação, se ainda aberto
    if cred and cred.status in ("aberto", "parcial"):
        cred.saldo_aberto = 0.0
        cred.status = "cancelado"
    return c


def check_projecao_unica(db: Session, rep_id: int, forn_id: int):
    """RN-006: só uma projeção aberta/parcial por Representante+Fornecedor."""
    q = db.query(Projecao).filter(
        Projecao.representante_id == rep_id,
        Projecao.fornecedor_id == forn_id,
        Projecao.status.in_(["aberta", "parcial"]),
    ).first()
    if q:
        raise HTTPException(422, f"Já existe projeção {q.status} (id={q.id}) "
                                 "para este Representante+Fornecedor (RN-006)")
