"""Autorizações de organização e aceitação explícita de vínculo de fornecedor."""
import hashlib
from sqlalchemy import select, update
from fastapi import HTTPException
from .audit import audit
from .models import _now, User
from .organizacoes_models import Organizacao, VinculoOrganizacao, FornecedorIdentidade, FornecedorVinculo, ConviteFornecedor


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def exigir_vinculo(db, usuario, organizacao_id, admin=False):
    org = db.get(Organizacao, organizacao_id)
    vinculo = db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id == usuario.id,
        VinculoOrganizacao.organizacao_id == organizacao_id, VinculoOrganizacao.ativo.is_(True)))
    if not org or not org.ativo or not vinculo or (admin and vinculo.perfil != 'admin'):
        raise HTTPException(403, 'Sem acesso a esta organização')
    return org, vinculo


def convite_publico(convite):
    return {campo: getattr(convite, campo) for campo in ('id', 'email', 'nome', 'organizacao_id',
        'created_at', 'expires_at', 'accepted_at', 'revoked_at')}


def bloquear_convite(db, token_hash):
    if db.get_bind().dialect.name == 'sqlite':
        # Reserva a escrita antes das leituras: SQLite não implementa FOR UPDATE.
        db.execute(update(ConviteFornecedor).where(ConviteFornecedor.token_hash == token_hash)
            .values(token_hash=ConviteFornecedor.token_hash))


def aceitar_convite(db, usuario, token):
    bloquear_convite(db, hash_token(token))
    # Convites distintos do mesmo usuário compartilham uma única identidade.
    db.scalar(select(User).where(User.id == usuario.id).with_for_update())
    convite = db.scalar(select(ConviteFornecedor).where(ConviteFornecedor.token_hash == hash_token(token)).with_for_update())
    if not convite or convite.email != usuario.email.strip().lower():
        raise HTTPException(403, 'Convite indisponível para este usuário')
    org = db.get(Organizacao, convite.organizacao_id)
    if not org or not org.ativo or convite.revoked_at:
        raise HTTPException(409, 'Convite indisponível')
    if convite.accepted_at:
        if convite.accepted_by != usuario.id:
            raise HTTPException(409, 'Convite já utilizado')
        identidade = db.scalar(select(FornecedorIdentidade).where(FornecedorIdentidade.user_id == usuario.id))
        _, membro = exigir_vinculo(db, usuario, org.id)
        fornecedor = db.scalar(select(FornecedorVinculo).where(FornecedorVinculo.identidade_id == identidade.id,
            FornecedorVinculo.organizacao_id == org.id, FornecedorVinculo.ativo.is_(True))) if identidade else None
        if not fornecedor:
            raise HTTPException(409, 'Vínculo de fornecedor indisponível')
        return {'organizacao_id': org.id, 'fornecedor_identidade_id': identidade.id, 'perfil': membro.perfil, 'aceito': True}
    if convite.expires_at <= _now():
        raise HTTPException(409, 'Convite expirado')
    identidade = db.scalar(select(FornecedorIdentidade).where(FornecedorIdentidade.user_id == usuario.id))
    if not identidade:
        identidade = FornecedorIdentidade(user_id=usuario.id)
        db.add(identidade)
        db.flush()
    fornecedor = db.scalar(select(FornecedorVinculo).where(FornecedorVinculo.identidade_id == identidade.id,
        FornecedorVinculo.organizacao_id == org.id))
    if fornecedor and not fornecedor.ativo:
        raise HTTPException(409, 'Vínculo desativado; contate a loja')
    if not fornecedor:
        db.add(FornecedorVinculo(identidade_id=identidade.id, organizacao_id=org.id))
    membro = db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id == usuario.id,
        VinculoOrganizacao.organizacao_id == org.id))
    if membro and not membro.ativo:
        raise HTTPException(409, 'Acesso desativado; contate a loja')
    if not membro:
        membro = VinculoOrganizacao(user_id=usuario.id, organizacao_id=org.id, perfil='fornecedor')
        db.add(membro)
    convite.accepted_at = _now()
    convite.accepted_by = usuario.id
    audit(db, usuario.id, 'convite_fornecedor_aceito', 'organizacao', org.id,
        depois={'convite_id': convite.id, 'fornecedor_identidade_id': identidade.id})
    db.commit()
    return {'organizacao_id': org.id, 'fornecedor_identidade_id': identidade.id, 'perfil': membro.perfil, 'aceito': True}
