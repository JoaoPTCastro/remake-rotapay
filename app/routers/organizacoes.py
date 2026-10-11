"""Base privada de organizações; não oferece operações financeiras entre lojas."""
import secrets
from functools import wraps
from inspect import signature
from datetime import timedelta
from fastapi import APIRouter, Depends, Response, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from ..auth import current_user, hash_pw, token_for
from ..database import get_control_db as get_db
from ..models import User, _now
from ..audit import audit
from ..organizacoes_models import Organizacao, VinculoOrganizacao, ConviteFornecedor
from ..ambientes import financeiro_habilitado, provisionar, PAPEIS_INTERNOS
from ..organizacoes_schemas import OrganizacaoIn, ConviteIn, AceitarConviteIn, RegistrarFornecedorIn
from ..organizacoes import exigir_vinculo, hash_token, convite_publico, aceitar_convite, bloquear_convite


def transacao_segura(func):
    @wraps(func)
    def executar(*args, **kwargs):
        db = kwargs['db']
        try:
            return func(*args, **kwargs)
        except (IntegrityError, OperationalError):
            db.rollback()
            raise HTTPException(409, 'Operação concorrente; tente novamente')
    executar.__signature__ = signature(func)
    return executar


def privado(response: Response):
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Content-Type-Options'] = 'nosniff'


router = APIRouter(prefix='/organizacoes', tags=['organizações'], dependencies=[Depends(privado)])
r = router


@router.get('')
def listar(db: Session = Depends(get_db), usuario: User = Depends(current_user)):
    rows = db.execute(select(Organizacao, VinculoOrganizacao).join(VinculoOrganizacao,
        VinculoOrganizacao.organizacao_id == Organizacao.id).where(VinculoOrganizacao.user_id == usuario.id,
        VinculoOrganizacao.ativo.is_(True), Organizacao.ativo.is_(True)).order_by(Organizacao.id)).all()
    return [{'id': org.id, 'nome': org.nome, 'ativo': org.ativo, 'perfil': membro.perfil, 'financeiro_habilitado': financeiro_habilitado(db, org.id)} for org, membro in rows]


@router.post('', status_code=201)
@transacao_segura
def criar(body: OrganizacaoIn, db: Session = Depends(get_db), usuario: User = Depends(current_user)):
    if usuario.perfil != 'admin':
        raise HTTPException(403, 'Sem permissão')
    exigir_vinculo(db, usuario, 1, admin=True)
    org = Organizacao(nome=body.nome)
    db.add(org)
    db.flush()
    db.add(VinculoOrganizacao(user_id=usuario.id, organizacao_id=org.id, perfil='admin'))
    audit(db, usuario.id, 'organizacao_criada', 'organizacao', org.id, depois={'nome': org.nome})
    db.commit()
    return {'id': org.id, 'nome': org.nome, 'ativo': org.ativo, 'perfil': 'admin', 'financeiro_habilitado': False}


@router.post('/convites/registrar', status_code=201)
@transacao_segura
def registrar(body: RegistrarFornecedorIn, db: Session = Depends(get_db)):
    bloquear_convite(db, hash_token(body.token))
    convite = db.scalar(select(ConviteFornecedor).where(ConviteFornecedor.token_hash == hash_token(body.token)).with_for_update())
    if not convite or convite.revoked_at or convite.accepted_at or convite.expires_at <= _now():
        raise HTTPException(409, 'Convite indisponível')
    org = db.get(Organizacao, convite.organizacao_id)
    if not org or not org.ativo:
        raise HTTPException(409, 'Convite indisponível')
    if db.scalar(select(User.id).where(func.lower(func.trim(User.email)) == convite.email)):
        raise HTTPException(409, 'Entre com sua conta para aceitar o convite')
    usuario = User(nome=body.nome, email=convite.email, senha_hash=hash_pw(body.senha), perfil='fornecedor', ativo=True)
    db.add(usuario)
    db.flush()
    return aceitar_convite(db, usuario, body.token)


@router.post('/convites/aceitar')
@transacao_segura
def aceitar(body: AceitarConviteIn, db: Session = Depends(get_db), usuario: User = Depends(current_user)):
    return aceitar_convite(db, usuario, body.token)


@router.get('/{organizacao_id}')
def detalhe(organizacao_id: int, db: Session = Depends(get_db), usuario: User = Depends(current_user)):
    org, membro = exigir_vinculo(db, usuario, organizacao_id)
    return {'id': org.id, 'nome': org.nome, 'ativo': org.ativo, 'perfil': membro.perfil, 'financeiro_habilitado': financeiro_habilitado(db, org.id)}


@router.get('/{organizacao_id}/membros')
def membros(organizacao_id: int, db: Session = Depends(get_db), usuario: User = Depends(current_user)):
    exigir_vinculo(db, usuario, organizacao_id, admin=True)
    rows = db.execute(select(User, VinculoOrganizacao).join(VinculoOrganizacao,
        VinculoOrganizacao.user_id == User.id).where(VinculoOrganizacao.organizacao_id == organizacao_id)
        .order_by(User.id)).all()
    return [{'user_id': u.id, 'nome': u.nome, 'email': u.email, 'perfil': m.perfil,
        'ativo': m.ativo and u.ativo} for u, m in rows]


@router.post('/{organizacao_id}/convites', status_code=201)
@transacao_segura
def convidar(organizacao_id: int, body: ConviteIn, db: Session = Depends(get_db), usuario: User = Depends(current_user)):
    exigir_vinculo(db, usuario, organizacao_id, admin=True)
    token = secrets.token_urlsafe(32)
    convite = ConviteFornecedor(token_hash=hash_token(token), email=body.email, nome=body.nome,
        organizacao_id=organizacao_id, created_by=usuario.id, expires_at=_now() + timedelta(days=7))
    db.add(convite)
    db.flush()
    audit(db, usuario.id, 'convite_fornecedor_criado', 'organizacao', organizacao_id, depois={'convite_id': convite.id})
    db.commit()
    return {**convite_publico(convite), 'token': token}


@router.get('/{organizacao_id}/convites')
def convites(organizacao_id: int, db: Session = Depends(get_db), usuario: User = Depends(current_user)):
    exigir_vinculo(db, usuario, organizacao_id, admin=True)
    return [convite_publico(c) for c in db.scalars(select(ConviteFornecedor).where(
        ConviteFornecedor.organizacao_id == organizacao_id).order_by(ConviteFornecedor.id))]


@router.post('/{organizacao_id}/convites/{convite_id}/revogar')
@transacao_segura
def revogar(organizacao_id: int, convite_id: int, db: Session = Depends(get_db), usuario: User = Depends(current_user)):
    exigir_vinculo(db, usuario, organizacao_id, admin=True)
    if db.get_bind().dialect.name == 'sqlite':
        from sqlalchemy import update
        db.execute(update(ConviteFornecedor).where(ConviteFornecedor.id == convite_id)
            .values(token_hash=ConviteFornecedor.token_hash))
    convite = db.scalar(select(ConviteFornecedor).where(ConviteFornecedor.id == convite_id).with_for_update())
    if not convite or convite.organizacao_id != organizacao_id:
        raise HTTPException(404, 'Convite não encontrado')
    if convite.accepted_at:
        raise HTTPException(409, 'Convite já aceito; revogar convite não remove vínculo')
    if not convite.revoked_at:
        convite.revoked_at = _now()
        audit(db, usuario.id, 'convite_fornecedor_revogado', 'organizacao', organizacao_id, depois={'convite_id': convite.id})
        db.commit()
    return convite_publico(convite)


@router.post('/{organizacao_id}/provisionar')
@transacao_segura
def provisionar_ambiente(organizacao_id: int, db: Session = Depends(get_db), usuario: User = Depends(current_user)):
    from sqlalchemy import update
    # Serializa provisionamento/registro central; nova loja nasce vazia, sem seed financeiro.
    db.execute(update(Organizacao).where(Organizacao.id == organizacao_id).values(nome=Organizacao.nome))
    org, _ = exigir_vinculo(db, usuario, organizacao_id, admin=True)
    return provisionar(db, org, usuario.id)


@router.post('/{organizacao_id}/selecionar')
def selecionar(organizacao_id: int, db: Session = Depends(get_db), usuario: User = Depends(current_user)):
    org, membro = exigir_vinculo(db, usuario, organizacao_id)
    if membro.perfil not in PAPEIS_INTERNOS:
        raise HTTPException(403, 'Use o acesso de fornecedor para suas relações autorizadas')
    if not financeiro_habilitado(db, org.id):
        raise HTTPException(409, 'Prepare o ambiente antes de selecionar')
    return {'access_token': token_for(usuario, org.id), 'token_type': 'bearer',
        'user': {'id': usuario.id, 'nome': usuario.nome, 'email': usuario.email,
                 'perfil': membro.perfil, 'organizacao_id': org.id, 'organizacao_nome': org.nome}}
