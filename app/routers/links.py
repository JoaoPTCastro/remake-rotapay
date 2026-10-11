"""Links de pagamento do vendedor — gerados pelo admin, usados pelo vendedor.

Fluxo (diagrama): Loja (admin) gera link individual → vendedor abre,
informa o valor → recebe a chave PIX do fornecedor p/ repassar ao cliente.
"""
import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..database import get_db
from ..ambientes import autor_financeiro_ativo
from ..models import LinkPagamento, Movimentacao, Pessoa, User
from ..cadastros import chave_principal, backfill_pessoas, fixar_destino, chave_do_link
from ..auth import need
from ..audit import audit
from ..utils_brcode import payload_copia_cola

r = APIRouter(prefix="/links", tags=["links"])


class LinkIn(BaseModel):
    representante_id: int
    fornecedor_id: int
    valor_fixo: float | None = Field(default=None, gt=0)


def _out(l: LinkPagamento, db: Session):
    rep = db.get(Pessoa, l.representante_id)
    forn = db.get(Pessoa, l.fornecedor_id)
    return {"id": l.id, "token": l.token,
            "representante_id": l.representante_id,
            "representante_nome": rep.nome if rep else "?",
            "fornecedor_id": l.fornecedor_id,
            "fornecedor_nome": forn.nome if forn else "?",
            "valor_fixo": l.valor_fixo, "ativo": l.ativo,
            "tem_cobranca": bool(l.pix_code),
            "url": (f"/v/{l.token}" if db.info.get("organizacao_id", 1) == 1
                    else f"/v/{db.info["organizacao_id"]}/{l.token}")}


@r.get("")
def listar(db: Session = Depends(get_db),
           u: User = Depends(need("admin", "financeiro", "operador", "consulta"))):
    return [_out(l, db) for l in db.query(LinkPagamento).order_by(LinkPagamento.id.desc()).all()]


@r.post("", status_code=201)
def criar(body: LinkIn, db: Session = Depends(get_db),
          u: User = Depends(need("admin", "financeiro"))):
    rep = db.get(Pessoa, body.representante_id)
    forn = db.get(Pessoa, body.fornecedor_id)
    if not rep or rep.tipo not in ("representante", "ambos"):
        raise HTTPException(422, "Vendedor (representante) inválido")
    if not forn or forn.tipo not in ("fornecedor", "ambos") or not forn.ativo:
        raise HTTPException(422, "Fornecedor inválido ou inativo")
    backfill_pessoas(db, forn.id)
    key = chave_principal(db, forn)
    if not key:
        raise HTTPException(422, "Fornecedor sem chave PIX cadastrada — cadastre em Pessoas")
    l = LinkPagamento(token=secrets.token_urlsafe(16)[:24],
                      representante_id=rep.id, fornecedor_id=forn.id,
                      valor_fixo=body.valor_fixo, ativo=True, created_by=u.id)
    fixar_destino(l, key)
    db.add(l)
    db.flush()
    auto = None
    if body.valor_fixo:
        try:
            _gerar_cobranca(db, l, rep)
            auto = True
        except HTTPException as e:
            # Sem valor: sem dados do vendedor ou sem gateway — o link
            # continua valendo no modo manual (chave + copia-e-cola).
            auto = str(e.detail)
    audit(db, u.id, "link_criado", "links_pagamento", l.id,
          depois={"vendedor": rep.id, "fornecedor": forn.id,
                  "cobranca_automatica": auto})
    if auto is True:
        audit(db, u.id, "cobranca_criada", "links_pagamento", l.id,
              depois={"automatica": True, "valor": float(body.valor_fixo or 0)})
    db.commit()
    return _out(l, db)


def _gerar_cobranca(db: Session, l: LinkPagamento, rep: Pessoa | None) -> dict:
    """Cria a cobrança PIX na Checkto e guarda QR no link. Exige valor fixo."""
    if db.info.get("organizacao_id", 1) != 1:
        raise HTTPException(503, "Integração de pagamento indisponível neste ambiente")
    from ..checkto import criar_cobranca_pix
    if not l.valor_fixo or l.valor_fixo <= 0:
        raise HTTPException(422, "Defina valor fixo no link para gerar a cobrança")
    if not rep or not rep.email or not rep.telefone or not rep.documento:
        raise HTTPException(422, "Vendedor precisa de nome, email, telefone e documento "
                                 "em Pessoas (exigência da Checkto)")
    resp = criar_cobranca_pix(
        identifier=f"link-{l.token}",
        amount=float(l.valor_fixo),
        client={"name": rep.nome, "email": rep.email,
                "phone": rep.telefone, "document": rep.documento})
    l.checkto_transaction_id = resp.get("transactionId", "")
    l.checkto_webhook_token = resp.get("webhookToken", "")
    pix = resp.get("pix", {}) or {}
    l.pix_code = pix.get("code", "")
    l.pix_image = pix.get("image", "")
    return {"id": l.id, "transactionId": l.checkto_transaction_id,
            "pix_code": l.pix_code, "pix_image": l.pix_image}


@r.post("/{lid}/cobrar", status_code=201)
def cobrar(lid: int, db: Session = Depends(get_db),
           u: User = Depends(need("admin", "financeiro"))):
    """Gera a cobrança PIX na Checkto para o link (exige valor fixo).

    Guarda transactionId + webhookToken + QR no link. O vendedor abre /v/ e
    mostra o QR; ao pagar, o webhook registra tudo sozinho.
    """
    l = db.get(LinkPagamento, lid)
    if not l or not l.ativo:
        raise HTTPException(404, "Link não encontrado ou revogado")
    rep = db.get(Pessoa, l.representante_id)
    saida = _gerar_cobranca(db, l, rep)
    audit(db, u.id, "cobranca_criada", "links_pagamento", l.id,
          depois={"transactionId": l.checkto_transaction_id, "valor": float(l.valor_fixo or 0)})
    db.commit()
    return saida


@r.post("/{lid}/revogar")
def revogar(lid: int, db: Session = Depends(get_db),
            u: User = Depends(need("admin", "financeiro"))):
    l = db.get(LinkPagamento, lid)
    if not l:
        raise HTTPException(404, "Não encontrado")
    l.ativo = False
    audit(db, u.id, "link_revogado", "links_pagamento", l.id)
    db.commit()
    return {"id": l.id, "ativo": False}


@r.get("/v/{token}")
def resolver(token: str, db: Session = Depends(get_db)):
    """Público: resolve o link do vendedor → dados p/ gerar o PIX."""
    l = db.query(LinkPagamento).filter_by(token=token, ativo=True).first()
    if not l or not autor_financeiro_ativo(db, l.created_by):
        raise HTTPException(404, "Link inválido ou revogado")
    rep = db.get(Pessoa, l.representante_id)
    forn = db.get(Pessoa, l.fornecedor_id)
    key = chave_do_link(db, l) if forn else None
    if not forn or not forn.ativo or not key:
        raise HTTPException(404, "Chave PIX indisponível")
    pago = db.query(Movimentacao.id).filter(
        Movimentacao.link_token == l.token).first() is not None
    return {"vendedor_nome": rep.nome if rep else "",
            "fornecedor_id": forn.id, "fornecedor_nome": forn.nome,
            "chave_pix": key.chave, "banco": key.banco,
            "conta": key.conta, "titular": key.titular or forn.nome,
            "valor_fixo": l.valor_fixo,
            "payload_pix": payload_copia_cola(
                key.chave, forn.nome, valor=l.valor_fixo, txid=l.token),
            "pago": pago,
            "pix_code": l.pix_code, "pix_image": l.pix_image}
