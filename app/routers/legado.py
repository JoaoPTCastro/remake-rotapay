"""Gestão privada de classificações; nenhuma migração/baixa é exposta."""
import json
import secrets
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from ..auth import need
from ..audit import audit
from ..database import get_db
from ..models import LegadoLote, LegadoClassificacao, User
from ..legado_schemas import FonteLegado, PreviaLegado, ConfirmacaoLegado
from ..legado_classificacao import (query_fonte, MODELOS, origem, previa,
    payload_itens, digest, canonico, horario, SEM_IMPACTO)

r = APIRouter(prefix="/legado", tags=["legado"])


def _pagina(itens, total, limit, offset):
    return {"itens": itens, "total": total, "limit": limit, "offset": offset,
        "tem_mais": offset + len(itens) < total, **SEM_IMPACTO}


def _recibo(lote, repetido=None):
    result = {"id": lote.id, "chave_idempotencia": lote.chave_idempotencia,
        "payload_hash": lote.payload_hash, "hash_previa": lote.hash_previa,
        "created_by": lote.created_by, "created_at": horario(lote.created_at),
        **json.loads(lote.recibo_json), **SEM_IMPACTO}
    if repetido is not None:
        result["repetido"] = repetido
    return result


@r.get("/inventario")
def inventario(fonte: FonteLegado = "movimentacao",
        limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
        db: Session = Depends(get_db),
        u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    q = query_fonte(db, fonte)
    total = q.count()
    rows = q.order_by(MODELOS[fonte].id.desc()).offset(offset).limit(limit).all()
    return {"fonte": fonte, **_pagina([origem(db, fonte, row.id) for row in rows], total, limit, offset)}


@r.post("/previa")
def gerar_previa(body: PreviaLegado, db: Session = Depends(get_db),
        u: User = Depends(need("admin", "financeiro"))):
    return previa(db, body.itens)


@r.get("/classificacoes")
def classificacoes(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
        db: Session = Depends(get_db), u: User = Depends(need("admin", "financeiro"))):
    q = db.query(LegadoLote)
    return _pagina([_recibo(lote) for lote in q.order_by(LegadoLote.id.desc()).offset(offset).limit(limit)], q.count(), limit, offset)


@r.post("/classificacoes", status_code=201)
def confirmar(body: ConfirmacaoLegado, response: Response,
        db: Session = Depends(get_db), u: User = Depends(need("admin", "financeiro"))):
    payload_hash = digest({"regra": 1, "itens": payload_itens(body.itens), "hash_previa": body.hash_previa})
    existente = db.query(LegadoLote).filter_by(chave_idempotencia=body.chave_idempotencia).first()
    if existente:
        if not secrets.compare_digest(existente.payload_hash, payload_hash):
            raise HTTPException(409, "Chave de idempotência já utilizada com outro conteúdo")
        response.status_code = 200
        return _recibo(existente, True)
    try:
        preview = previa(db, body.itens)
    except HTTPException as exc:
        if exc.status_code != 409:
            raise
        # Another request may commit this exact key after the initial read
        # but before source validation. Return its frozen receipt as replay.
        db.rollback()
        existente = db.query(LegadoLote).filter_by(chave_idempotencia=body.chave_idempotencia).first()
        if existente and secrets.compare_digest(existente.payload_hash, payload_hash):
            response.status_code = 200
            return _recibo(existente, True)
        raise
    if not secrets.compare_digest(preview["hash_previa"], body.hash_previa):
        raise HTTPException(409, "Prévia divergente; revise os itens antes de confirmar")
    try:
        lote = LegadoLote(chave_idempotencia=body.chave_idempotencia,
            payload_hash=payload_hash, hash_previa=body.hash_previa,
            recibo_json="{}", created_by=u.id)
        db.add(lote)
        db.flush()
        itens = []
        for item in preview["itens"]:
            campos = {k: item[k] for k in ("fonte", "fonte_id", "snapshot_hash", "decisao", "evidencia", "pessoa_id", "relacao")}
            ledger = LegadoClassificacao(**campos, lote_id=lote.id, created_by=u.id)
            db.add(ledger)
            db.flush()
            itens.append({**item, "id": ledger.id})
        lote.recibo_json = canonico({"itens": itens, "total": len(itens)})
        audit(db, u.id, "legado_lote_classificado", "legado_lotes", lote.id,
            depois={"total": len(itens), "fontes": [{"fonte": i["fonte"], "fonte_id": i["fonte_id"], "decisao": i["decisao"]} for i in itens], **SEM_IMPACTO})
        db.commit()
        db.refresh(lote)
    except (IntegrityError, OperationalError):
        db.rollback()
        # Uniqueness arbitrates concurrent first submissions. A completed
        # identical receipt may be returned; every other race conflicts.
        existente = db.query(LegadoLote).filter_by(chave_idempotencia=body.chave_idempotencia).first()
        if existente and secrets.compare_digest(existente.payload_hash, payload_hash):
            response.status_code = 200
            return _recibo(existente, True)
        raise HTTPException(409, "Origem já classificada ou lote em atualização; recarregue")
    return _recibo(lote, False)
