"""Cliente mínimo da Checkto (llms.txt): criar cobrança PIX.

Docs: POST /gateway/pix/receive com x-public-key/x-secret-key.
Valores em reais (decimal). Callback URL fixa. Sem polling.
"""
import httpx
from fastapi import HTTPException
from .config import (CHECKTO_PUBLIC_KEY, CHECKTO_SECRET_KEY,
                     CHECKTO_CALLBACK_URL)

BASE = "https://app.checkto.com.br/api/v1"


def _headers() -> dict:
    if not CHECKTO_PUBLIC_KEY or not CHECKTO_SECRET_KEY:
        raise HTTPException(422, "Checkto não configurada: defina CHECKTO_PUBLIC_KEY "
                                 "e CHECKTO_SECRET_KEY no ambiente")
    return {"x-public-key": CHECKTO_PUBLIC_KEY,
            "x-secret-key": CHECKTO_SECRET_KEY,
            "Content-Type": "application/json"}


def criar_cobranca_pix(identifier: str, amount: float, client: dict) -> dict:
    """Cria cobrança PIX. Retorna {transactionId, pix{code,image}, webhookToken}.

    Sem CHECKTO_CALLBACK_URL, a cobrança sai sem webhook (útil p/ teste);
    o registro automático só funciona com callback configurada.
    """
    payload = {"identifier": identifier, "amount": round(amount, 2),
               "client": client, "products": [],
               "metadata": {"provider": "pix-atravessado"}}
    if CHECKTO_CALLBACK_URL:
        payload["callbackUrl"] = CHECKTO_CALLBACK_URL
    try:
        r = httpx.post(f"{BASE}/gateway/pix/receive", headers=_headers(),
                       json=payload, timeout=30)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Falha ao falar com a Checkto: {e}")
    if r.status_code >= 400:
        try:
            detail = r.json().get("message", r.text[:300])
        except Exception:
            detail = r.text[:300]  # ex.: página HTML 403 do firewall geográfico
        raise HTTPException(502, f"Checkto recusou ({r.status_code}): {detail}")
    return r.json()
