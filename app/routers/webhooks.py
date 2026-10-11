"""Webhook real da Checkto (llms.txt §7).

Validação: comparação direta do `token` do payload com o `webhookToken`
guardado na criação da cobrança (ou `CHECKTO_WEBHOOK_TOKEN` do painel).
NÃO há HMAC — a docs não prevê assinatura.

Mapeamento: `transaction.identifier` = `link-{token}` do nosso link;
`transaction.id` garante idempotência. Só `TRANSACTION_PAID` com
`status=COMPLETED` registra movimentação + comprovante (origem=gateway).
Responde sempre 2XX (rejeição vai para auditoria, sem retry em loop).
"""
import json
from datetime import date
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Movimentacao, Comprovante, Job, Pessoa, LinkPagamento
from ..audit import audit
from ..config import CHECKTO_WEBHOOK_TOKEN

r = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _token_ok(db: Session, token: str, identifier: str) -> bool:
    if token and token == CHECKTO_WEBHOOK_TOKEN:
        return True
    if identifier.startswith("link-"):
        link = db.query(LinkPagamento).filter_by(token=identifier[5:]).first()
        if link and link.checkto_webhook_token and link.checkto_webhook_token == token:
            return True
    return False


@r.post("/checkto")
async def checkto(req: Request, db: Session = Depends(get_db)):
    try:
        body = json.loads(await req.body() or b"{}")
    except Exception:
        return JSONResponse({"ok": False, "reason": "json inválido"}, status_code=200)
    event = body.get("event", "")
    token = body.get("token", "")
    tx = body.get("transaction", {}) or {}
    identifier = tx.get("identifier", "") or ""
    if not _token_ok(db, token, identifier):
        audit(db, None, "webhook_rejeitado", "webhooks", None,
              depois={"event": event, "identifier": identifier})
        db.commit()
        return {"ok": False, "reason": "token inválido"}
    if event != "TRANSACTION_PAID" or tx.get("status") != "COMPLETED":
        audit(db, None, "webhook_ignorado", "webhooks", None,
              depois={"event": event, "status": tx.get("status")})
        db.commit()
        return {"ok": True, "ignored": event}
    tx_id = tx.get("id", "")
    if not tx_id:
        return {"ok": False, "reason": "transaction.id ausente (idempotência obrigatória)"}
    if db.query(Comprovante).filter_by(arquivo_hash=f"ckto:{tx_id}").first():
        audit(db, None, "webhook_duplicado", "webhooks", None,
              depois={"tx": tx_id, "identifier": identifier})
        db.commit()
        return {"ok": True, "duplicate": True}
    link = db.query(LinkPagamento).filter_by(
        token=identifier[5:]).first() if identifier.startswith("link-") else None
    if not link or not link.ativo:
        audit(db, None, "webhook_sem_link", "webhooks", None, depois={"identifier": identifier})
        db.commit()
        return {"ok": False, "reason": "link desconhecido"}
    forn = db.get(Pessoa, link.fornecedor_id)
    valor = round(float(tx.get("amount", 0)), 2)
    if valor <= 0:
        return {"ok": False, "reason": "valor inválido"}
    client = body.get("client", {}) or {}
    m = Movimentacao(codigo="PIX-TMP",
                     data_pix=date.fromisoformat(tx["payedAt"][:10]) if tx.get("payedAt") else date.today(),
                     valor=valor, saldo_disponivel=valor,
                     remetente=client.get("name", ""), representante_id=link.representante_id,
                     destinatario=forn.nome if forn else "",
                     fornecedor_id=link.fornecedor_id, autor="CHECKTO",
                     forma_pagamento="PIX", natureza="DESPESA",
                     link_token=link.token,
                     observacao=f"Pago via Checkto (tx {tx_id})",
                     status="disponivel")
    db.add(m)
    db.flush()
    m.codigo = f"PIX-{m.id:06d}"
    comp = Comprovante(movimentacao_id=m.id, arquivo_path=f"checkto:{tx_id}",
                       arquivo_hash=f"ckto:{tx_id}", origem="gateway",
                       enviado_por="checkto", data_comprovante=m.data_pix,
                       etapa="registrado")
    db.add(comp)
    db.flush()
    db.add(Job(tipo="comprovante", ref_id=comp.id, status="processado",
               detalhe="checkto: pago, comprovante automático"))
    audit(db, None, "pagamento_checkto", "movimentacoes", m.id,
          depois={"tx": tx_id, "valor": valor, "identifier": identifier})
    db.commit()
    return {"ok": True, "movimentacao_id": m.id, "codigo": m.codigo}
