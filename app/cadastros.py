"""Compatibilidade dos cadastros: migração explícita e seleção segura da chave principal."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from .models import Pessoa, PessoaContato, PessoaChavePix, LinkPagamento


def hoje():
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()


def backfill_pessoas(db, pessoa_id=None):
    """Idempotente; usa somente a sessão fornecida, sem abrir banco de produção."""
    query = db.query(Pessoa)
    if pessoa_id is not None:
        query = query.filter(Pessoa.id == pessoa_id)
    for p in query.all():
        if not db.query(PessoaContato).filter_by(pessoa_id=p.id).first() and (p.telefone or p.email):
            db.add(PessoaContato(pessoa_id=p.id, nome=p.nome, telefone=p.telefone,
                                email=p.email, principal=True))
        if not db.query(PessoaChavePix).filter_by(pessoa_id=p.id).first() and p.chave_pix:
            db.add(PessoaChavePix(pessoa_id=p.id, chave=p.chave_pix, titular=p.titular_chave,
                                banco=p.banco, conta=p.conta, principal=True))
    db.flush()


def chave_principal(db, p):
    keys = db.query(PessoaChavePix).filter_by(pessoa_id=p.id).all()
    if keys:
        return next((k for k in keys if k.principal and k.ativo and
                     (k.validade is None or k.validade >= hoje())), None)
    # Compatibilidade até executar backfill.
    if p.chave_pix:
        return PessoaChavePix(chave=p.chave_pix, titular=p.titular_chave,
                              banco=p.banco, conta=p.conta, ativo=True, principal=True)
    return None


def sincronizar_chave(db, p):
    k = chave_principal(db, p)
    p.chave_pix = k.chave if k else ""
    p.banco = k.banco if k else ""
    p.conta = k.conta if k else ""
    p.titular_chave = k.titular if k else ""


SNAPSHOT_FIELDS = (("chave", "chave_snapshot"), ("titular", "titular_snapshot"),
                   ("banco", "banco_snapshot"), ("agencia", "agencia_snapshot"),
                   ("conta", "conta_snapshot"), ("tipo_conta", "tipo_conta_snapshot"))


def fixar_destino(link, key):
    link.destino_fixado = True
    if key is not None:
        link.chave_pix_id = key.id
        for field, snapshot in SNAPSHOT_FIELDS:
            setattr(link, snapshot, getattr(key, field) or "")


def backfill_links(db):
    """Fixa uma vez o destino conhecido; não recupera chaves históricas anteriores."""
    for link in db.query(LinkPagamento).filter_by(destino_fixado=False).all():
        person = db.get(Pessoa, link.fornecedor_id)
        fixar_destino(link, chave_principal(db, person) if person else None)
    db.flush()


def chave_do_link(db, link):
    if not link.destino_fixado or not link.chave_pix_id:
        return None
    key = db.get(PessoaChavePix, link.chave_pix_id)
    if not key or key.pessoa_id != link.fornecedor_id or not key.ativo:
        return None
    if key.validade is not None and key.validade < hoje():
        return None
    if any((getattr(key, field) or "") != getattr(link, snapshot)
           for field, snapshot in SNAPSHOT_FIELDS):
        return None
    return key
