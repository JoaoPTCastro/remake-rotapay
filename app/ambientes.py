"""Persistência financeira por loja, separada das identidades centrais."""
import os
from functools import lru_cache
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import create_engine, select, event
from sqlalchemy.orm import sessionmaker
from .models import Base, Loja, User
from .organizacoes_models import Organizacao, VinculoOrganizacao
from .ambientes_models import AmbienteOrganizacao

# Configuração privada do servidor. Nenhum endpoint aceita caminho/URL de banco.
database_root = Path(os.getenv('TENANT_DATABASE_DIR', './ambientes-locais'))
PAPEIS_INTERNOS = ('admin', 'financeiro', 'operador', 'consulta')


def upload_root(db, base):
    root = Path(base).resolve()
    org_id = db.info.get('organizacao_id', 1)
    if org_id == 1:
        return root
    target = root / 'organizacoes' / str(int(org_id))
    resolved = target.resolve()
    if resolved != target or not resolved.is_relative_to(root):
        raise HTTPException(503, 'Ambiente de arquivos indisponível')
    return resolved


def _database_path(org_id):
    if not isinstance(org_id, int) or org_id < 2:
        raise HTTPException(503, 'Ambiente financeiro inválido')
    root = database_root.resolve()
    target = root / f'organizacao-{org_id}.sqlite3'
    if target.is_symlink() or target.resolve() != target:
        raise HTTPException(503, 'Ambiente financeiro indisponível')
    return target


@lru_cache(maxsize=128)
def _sessions(path):
    engine = create_engine(f'sqlite:///{path}', connect_args={'check_same_thread': False, 'timeout': 15})
    @event.listens_for(engine, 'connect')
    def foreign_keys(conn, _record):
        conn.execute('PRAGMA foreign_keys=ON')
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def financeiro_habilitado(db, org_id):
    if org_id == 1:
        return True
    registro = db.get(AmbienteOrganizacao, org_id)
    return bool(registro and registro.pronto)


def provisionar(db, org, usuario_id=None):
    registro = db.get(AmbienteOrganizacao, org.id)
    if org.id == 1 or (registro and registro.pronto):
        return {'organizacao_id': org.id, 'financeiro_habilitado': True}
    path = _database_path(org.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    factory = _sessions(str(path))
    with factory() as local:
        Base.metadata.create_all(local.get_bind())
        if not local.query(Loja).first():
            local.add(Loja(nome=org.nome))
            local.commit()
    if not registro:
        registro = AmbienteOrganizacao(organizacao_id=org.id, pronto=True)
        db.add(registro)
    else:
        registro.pronto = True
    from .audit import audit
    audit(db, usuario_id, 'ambiente_provisionado', 'organizacao', org.id)
    db.commit()
    return {'organizacao_id': org.id, 'financeiro_habilitado': True}


def abrir_financeiro(central, org_id):
    org = central.get(Organizacao, org_id)
    if not org or not org.ativo or not financeiro_habilitado(central, org_id):
        raise HTTPException(503, 'Ambiente financeiro indisponível')
    path = _database_path(org_id)
    if not path.is_file():
        raise HTTPException(503, 'Ambiente financeiro indisponível')
    local = _sessions(str(path))()
    local.info.update(organizacao_id=org_id, controle_session=central, runtime_ambiente=True)
    try:
        # Referências locais sustentam FKs/auditoria, sem credenciais ou emails pessoais.
        membros = central.execute(select(User, VinculoOrganizacao).join(
            VinculoOrganizacao, VinculoOrganizacao.user_id == User.id).where(
            VinculoOrganizacao.organizacao_id == org_id)).all()
        ativos = set()
        for user, membro in membros:
            if membro.perfil not in PAPEIS_INTERNOS:
                continue
            ativos.add(user.id)
            shadow = local.get(User, user.id)
            if shadow is None:
                shadow = User(id=user.id, email=f'usuario-{user.id}@referencia.local', senha_hash='')
                local.add(shadow)
            shadow.nome, shadow.perfil = user.nome, membro.perfil
            shadow.ativo = user.ativo and membro.ativo
        for shadow in local.query(User).all():
            if shadow.id not in ativos:
                shadow.ativo = False
        local.commit()
        return local
    except Exception:
        local.close()
        raise


def autor_financeiro_ativo(db, user_id):
    """Públicos revogam acesso quando autor perde vínculo central, sem copiar senhas."""
    central = db.info.get('controle_session')
    if central is None:
        return True  # Compatibilidade de dependências isoladas anteriores.
    if central.query(Organizacao.id).first() is None:
        return True
    org_id = db.info.get('organizacao_id', 1)
    return central.scalar(select(VinculoOrganizacao.id).join(User).join(Organizacao).where(
        VinculoOrganizacao.organizacao_id == org_id, VinculoOrganizacao.user_id == user_id,
        VinculoOrganizacao.ativo.is_(True), User.ativo.is_(True), Organizacao.ativo.is_(True),
        VinculoOrganizacao.perfil.in_(('admin', 'financeiro')))) is not None
