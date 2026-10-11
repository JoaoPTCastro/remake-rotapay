"""Cadastro público com banco/ambientes descartáveis e isolamento explícito."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app import ambientes
from app.auth import check_pw
from app.config import SECRET_KEY, ALGORITHM
from app.database import get_control_db
from app.models import Base, User, Pessoa, Pagamento
from app.organizacoes_models import Organizacao, VinculoOrganizacao
from app.routers import cadastro_publico as signup


@pytest.fixture
def cadastro(tmp_path, monkeypatch):
    monkeypatch.setenv('REGISTER_PUBLIC_ENABLED', 'true')
    monkeypatch.setattr(ambientes, 'database_root', tmp_path / 'tenants')
    signup._hits.clear()
    signup._global_hits.clear()
    engine = create_engine(f'sqlite:///{tmp_path / "central.db"}', connect_args={'check_same_thread': False, 'timeout': 15})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        db.add(Organizacao(id=1, nome='Original'))
        db.commit()
    app = FastAPI()
    app.include_router(signup.router)
    def isolated():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_control_db] = isolated
    with TestClient(app) as client:
        yield client, sessions, tmp_path
    engine.dispose()


def body(**changes):
    return {'nome': 'Responsável Loja', 'loja_nome': 'Loja Nova', 'email': 'Nova@teste.local', 'senha': 'Senha-Segura-2026', **changes}


def test_cria_apenas_loja_nova_vazia_e_token_local(cadastro):
    client, sessions, root = cadastro
    response = client.post('/auth/registrar', json=body())
    assert response.status_code == 201, response.text
    data = response.json()
    assert response.headers['cache-control'] == 'no-store'
    assert data['organizacao_id'] > 1
    claims = jwt.decode(data['access_token'], SECRET_KEY, algorithms=[ALGORITHM])
    assert claims['org'] == data['organizacao_id']
    with sessions() as db:
        user = db.scalar(select(User))
        assert user.email == 'nova@teste.local' and user.perfil == 'consulta'
        assert check_pw(body()['senha'], user.senha_hash)
        memberships = list(db.scalars(select(VinculoOrganizacao)))
        assert len(memberships) == 1
        assert memberships[0].organizacao_id == data['organizacao_id']
        assert memberships[0].perfil == 'admin' and memberships[0].ativo
        local = ambientes.abrir_financeiro(db, data['organizacao_id'])
        try:
            assert local.query(Pessoa).count() == local.query(Pagamento).count() == 0
        finally:
            local.close()


@pytest.mark.parametrize('flag', ['', 'false', 'yes', '1'])
def test_flag_failclosed(cadastro, monkeypatch, flag):
    client, sessions, _ = cadastro
    monkeypatch.setenv('REGISTER_PUBLIC_ENABLED', flag)
    assert client.post('/auth/registrar', json=body()).status_code == 403
    with sessions() as db:
        assert db.query(User).count() == 0


@pytest.mark.parametrize('changes', [{'senha': 'senha-fraca'}, {'nome': '  '}, {'email': 'email-ruim'}, {'senha': 'A' * 129}, {'perfil': 'admin'}, {'organizacao_id': 1}])
def test_rejeita_entradas_invalidas_e_privilegios(cadastro, changes):
    client, sessions, _ = cadastro
    assert client.post('/auth/registrar', json=body(**changes)).status_code == 422
    with sessions() as db:
        assert db.query(User).count() == 0


def test_duplicate_normalizado_sem_alterar_conta(cadastro):
    client, sessions, _ = cadastro
    assert client.post('/auth/registrar', json=body()).status_code == 201
    assert client.post('/auth/registrar', json=body(email='  NOVA@teste.local  ', senha='Outra-Senha-2026')).status_code == 409
    with sessions() as db:
        assert db.query(User).count() == 1
        assert check_pw(body()['senha'], db.scalar(select(User)).senha_hash)


def test_falha_provisionamento_deixa_entidades_inativas(cadastro, monkeypatch):
    client, sessions, _ = cadastro
    def fail(db, org, user):
        db.commit()  # Reproduz falha depois do commit interno do provisionador.
        raise OSError('disco indisponível')
    monkeypatch.setattr(signup, 'provisionar', fail)
    assert client.post('/auth/registrar', json=body()).status_code == 503
    with sessions() as db:
        assert not db.scalar(select(User)).ativo
        assert not db.get(Organizacao, 2).ativo
        assert not db.scalar(select(VinculoOrganizacao)).ativo
    assert client.post('/auth/registrar', json=body()).status_code == 409


def test_limite_por_ip_ignora_forwarded_for(cadastro):
    client, _, _ = cadastro
    for number in range(5):
        assert client.post('/auth/registrar', json=body(senha='fraca'), headers={'X-Forwarded-For': str(number)}).status_code == 422
    assert client.post('/auth/registrar', json=body()).status_code == 429


def test_duas_lojas_nao_compartilham_vinculos(cadastro):
    client, sessions, _ = cadastro
    first = client.post('/auth/registrar', json=body()).json()
    second = client.post('/auth/registrar', json=body(email='outra@teste.local')).json()
    assert first['organizacao_id'] != second['organizacao_id']
    with sessions() as db:
        assert db.query(VinculoOrganizacao).filter_by(organizacao_id=1).count() == 0
        for account in (first, second):
            membership = db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id == account['user']['id']))
            assert membership.organizacao_id == account['organizacao_id']


def test_login_mantem_contexto_e_nao_acessa_original(cadastro):
    from app.routers.auth import r as auth_router
    from app.routers.organizacoes import router as org_router
    client, _, _ = cadastro
    client.app.include_router(auth_router)
    client.app.include_router(org_router)
    created = client.post('/auth/registrar', json=body()).json()
    login = client.post('/auth/login', json={'email': 'nova@teste.local', 'senha': body()['senha']})
    assert login.status_code == 200, login.text
    claims = jwt.decode(login.json()['access_token'], SECRET_KEY, algorithms=[ALGORITHM])
    assert claims['org'] == created['organizacao_id']
    assert login.json()['user']['perfil'] == 'admin'
    headers = {'Authorization': f"Bearer {login.json()['access_token']}"}
    assert client.get('/organizacoes/1', headers=headers).status_code == 403
    own = client.get(f"/organizacoes/{created['organizacao_id']}", headers=headers)
    assert own.status_code == 200


def test_email_concorrente_cria_uma_conta(cadastro):
    from concurrent.futures import ThreadPoolExecutor
    client, sessions, _ = cadastro
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda email: client.post('/auth/registrar', json=body(email=email)).status_code,
                                ['corrida@teste.local', 'CORRIDA@teste.local']))
    assert sorted(replies) == [201, 409]
    with sessions() as db:
        assert db.query(User).count() == 1
        assert db.query(Organizacao).count() == 2


def test_falha_antes_commit_provisionador_reserva_id_inativo(cadastro, monkeypatch):
    client, sessions, _ = cadastro
    original = signup.provisionar
    def fail(db, org, user):
        raise OSError('falha ao criar banco')
    monkeypatch.setattr(signup, 'provisionar', fail)
    assert client.post('/auth/registrar', json=body()).status_code == 503
    with sessions() as db:
        assert not db.get(Organizacao, 2).ativo
    monkeypatch.setattr(signup, 'provisionar', original)
    response = client.post('/auth/registrar', json=body(email='segunda@teste.local'))
    assert response.status_code == 201
    assert response.json()['organizacao_id'] == 3


def test_header_ip_sem_chave_nao_burla_limite(cadastro, monkeypatch):
    client, _, _ = cadastro
    monkeypatch.setenv('PRIVATE_PROXY_KEY', 'chave-privada-do-teste')
    for number in range(5):
        assert client.post('/auth/registrar', json=body(senha='fraca'), headers={
            'X-RotaPay-Client-IP': f'192.0.2.{number}', 'X-RotaPay-Proxy-Key': 'chave-falsa'}).status_code == 422
    assert client.post('/auth/registrar', json=body()).status_code == 429


def test_proxy_autenticado_separa_limites_por_ip(cadastro, monkeypatch):
    client, _, _ = cadastro
    monkeypatch.setenv('PRIVATE_PROXY_KEY', 'chave-privada-do-teste')
    for _ in range(5):
        assert client.post('/auth/registrar', json=body(senha='fraca'), headers={
            'X-RotaPay-Client-IP': '192.0.2.1', 'X-RotaPay-Proxy-Key': 'chave-privada-do-teste'}).status_code == 422
    assert client.post('/auth/registrar', json=body(), headers={
        'X-RotaPay-Client-IP': '192.0.2.1', 'X-RotaPay-Proxy-Key': 'chave-privada-do-teste'}).status_code == 429
    assert client.post('/auth/registrar', json=body(), headers={
        'X-RotaPay-Client-IP': '192.0.2.2', 'X-RotaPay-Proxy-Key': 'chave-privada-do-teste'}).status_code == 201


def test_proxy_autenticado_rejeita_ip_invalido(cadastro, monkeypatch):
    client, _, _ = cadastro
    monkeypatch.setenv('PRIVATE_PROXY_KEY', 'chave-privada-do-teste')
    assert client.post('/auth/registrar', json=body(), headers={
        'X-RotaPay-Client-IP': 'qualquer', 'X-RotaPay-Proxy-Key': 'chave-privada-do-teste'}).status_code == 400
