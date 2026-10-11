"""Administração autenticada: banco e credenciais exclusivos por cenário."""
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.auth import hash_pw, token_for
from app.database import get_db
from app.main import app
from app.models import Base, User, Loja, AuditLog


@pytest.fixture
def administracao_api(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'administracao.db'}", connect_args={"check_same_thread": False, "timeout": 15})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        users = [User(nome=f"Pessoa {p}", email=f"{p}@administracao.local", perfil=p,
                      senha_hash=hash_pw("Senha teste 123!"), ativo=True)
                 for p in ("admin", "financeiro", "operador", "consulta")]
        db.add_all(users)
        db.commit()
        headers = {u.perfil: {"Authorization": f"Bearer {token_for(u)}"} for u in users}
        ids = {u.perfil: u.id for u in users}
    def isolated_db():
        with sessions() as db:
            yield db
    old = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = isolated_db
    client = TestClient(app)  # Sem lifespan: nunca inicializa banco operacional.
    try:
        yield client, headers, sessions, ids
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old)
        engine.dispose()


@pytest.mark.parametrize("perfil", ["admin", "financeiro", "operador", "consulta"])
def test_proprio_nome_sem_escalada_e_email_com_senha(administracao_api, perfil):
    c, h, sessions, ids = administracao_api
    r = c.patch('/auth/me', headers=h[perfil], json={'nome': ' Nome atualizado '})
    assert r.status_code == 200, r.text
    assert r.json()['nome'] == 'Nome atualizado' and r.json()['perfil'] == perfil
    for forbidden in ({'perfil': 'admin'}, {'ativo': False}, {'id': ids['admin']}):
        assert c.patch('/auth/me', headers=h[perfil], json=forbidden).status_code == 422
    for payload in ({'email': 'novo@example.com'}, {'email': 'novo@example.com', 'senha_atual': 'errada'}):
        assert c.patch('/auth/me', headers=h[perfil], json=payload).status_code == 403
    r = c.patch('/auth/me', headers=h[perfil], json={'email': f' NOVO-{perfil}@Example.com ', 'senha_atual': 'Senha teste 123!'})
    assert r.status_code == 200, r.text
    assert r.json()['email'] == f'novo-{perfil}@example.com'
    assert 'senha' not in r.text and 'hash' not in r.text
    assert c.post('/auth/login', json={'email': f'novo-{perfil}@example.com', 'senha': 'Senha teste 123!'}).status_code == 200
    with sessions() as db:
        assert db.get(User, ids[perfil]).ativo
        logs = db.query(AuditLog).filter(AuditLog.entidade_id == ids[perfil]).all()
        assert logs and all('Senha teste' not in (a.antes + a.depois) and 'senha_hash' not in (a.antes + a.depois) for a in logs)


@pytest.mark.parametrize('payload', [{}, {'nome': ' '}, {'email': 'inválido'}, {'email': None}, {'nome': 'X' * 121}, {'senha_hash': 'forjado'}])
def test_me_rejeita_dados_invalidos_sem_escrita(administracao_api, payload):
    c, h, sessions, ids = administracao_api
    assert c.patch('/auth/me', headers=h['consulta'], json=payload).status_code == 422
    with sessions() as db:
        assert db.get(User, ids['consulta']).nome == 'Pessoa consulta'
        assert db.query(AuditLog).count() == 0


def test_email_conflitante_reverte_nome_e_auditoria(administracao_api):
    c, h, sessions, ids = administracao_api
    r = c.patch('/auth/me', headers=h['consulta'], json={'nome': 'Não persistir', 'email': ' ADMIN@administracao.local ', 'senha_atual': 'Senha teste 123!'})
    assert r.status_code == 409, r.text
    with sessions() as db:
        assert db.get(User, ids['consulta']).nome == 'Pessoa consulta'
        assert db.query(AuditLog).count() == 0


def test_admin_edita_identidade_e_token_usa_perfil_corrente(administracao_api):
    c, h, sessions, ids = administracao_api
    r = c.patch(f"/auth/users/{ids['operador']}", headers=h['admin'], json={'nome': 'Operador novo', 'email': 'novo@example.com', 'perfil': 'financeiro', 'motivo': 'Ajuste autorizado'})
    assert r.status_code == 200, r.text
    assert set(r.json()) == {'id', 'nome', 'email', 'perfil', 'ativo'}
    assert c.patch('/loja', headers=h['operador'], json={'nome': 'Loja nova'}).status_code == 200
    assert c.patch(f"/auth/users/{ids['operador']}", headers=h['admin'], json={'perfil': 'consulta'}).status_code == 200
    assert c.patch('/loja', headers=h['operador'], json={'nome': 'Loja proibida'}).status_code == 403
    assert c.patch(f"/auth/users/{ids['operador']}", headers=h['admin'], json={'ativo': False}).status_code == 200
    assert c.get('/auth/me', headers=h['operador']).status_code == 401


def test_ultimo_admin_e_auto_desativacao_protegidos(administracao_api):
    c, h, sessions, ids = administracao_api
    for payload in ({'perfil': 'consulta'}, {'ativo': False}):
        assert c.patch(f"/auth/users/{ids['admin']}", headers=h['admin'], json=payload).status_code == 422
    with sessions() as db:
        assert db.get(User, ids['admin']).perfil == 'admin'
        assert db.get(User, ids['admin']).ativo
        assert db.query(AuditLog).count() == 0


def test_get_loja_leitura_sem_criar_linha_ou_auditar(administracao_api):
    c, h, sessions, _ = administracao_api
    for role in h:
        assert c.get('/loja', headers=h[role]).status_code == 200
    with sessions() as db:
        assert db.query(Loja).count() == db.query(AuditLog).count() == 0
    assert c.get('/loja').status_code in (401, 403)


def test_loja_strict_e_consulta_nao_altera_financeiro(administracao_api):
    c, h, sessions, _ = administracao_api
    assert c.patch('/loja', headers=h['consulta'], json={'nome': 'Proibido'}).status_code == 403
    assert c.post('/notas', headers=h['consulta'], json={}).status_code == 403
    for payload in ({'nome': 'X'}, {'perfil': 'admin'}, {'email': 'sem-arroba'}):
        assert c.patch('/loja', headers=h['admin'], json=payload).status_code == 422
    with sessions() as db:
        assert db.query(Loja).count() == 0


def imagem(fmt='PNG', size=(20, 20)):
    from io import BytesIO
    from PIL import Image
    output = BytesIO()
    Image.new('RGB', size, 'red').save(output, format=fmt)
    return output.getvalue()


@pytest.mark.parametrize('fmt', ['PNG', 'JPEG', 'WEBP'])
def test_logo_privado_reencodificado_e_remocao_logica(administracao_api, tmp_path, monkeypatch, fmt):
    from app.routers import loja
    from PIL import Image
    from io import BytesIO
    c, h, sessions, _ = administracao_api
    monkeypatch.setattr(loja, 'UPLOAD_DIR', tmp_path)
    assert c.get('/loja/logo', headers=h['admin']).status_code == 404
    data = imagem(fmt)
    r = c.post('/loja/logo', headers=h['financeiro'], files={'arquivo': ('../../logo.html', data, 'text/html')})
    assert r.status_code == 200, r.text
    assert r.json()['tem_logo'] and r.json()['logo_url'] == '/loja/logo'
    assert c.get('/loja/logo').status_code in (401, 403)
    for role in h:
        r = c.get('/loja/logo', headers=h[role])
        assert r.status_code == 200 and r.headers['content-type'] == 'image/png'
        assert 'no-store' in r.headers['cache-control'] and r.headers['x-content-type-options'] == 'nosniff'
        with Image.open(BytesIO(r.content)) as img:
            assert img.format == 'PNG' and img.size == (20, 20)
    assert c.delete('/loja/logo', headers=h['consulta']).status_code == 403
    assert c.delete('/loja/logo', headers=h['admin']).json()['tem_logo'] is False
    assert c.get('/loja/logo', headers=h['admin']).status_code == 404
    with sessions() as db:
        assert db.query(Loja).one().logo_arquivo is None
        assert db.query(AuditLog).filter(AuditLog.acao == 'loja_logo_removido').count() == 1
    assert len(list((tmp_path / 'loja-logos').glob('*.png'))) == 1


@pytest.mark.parametrize('kind', ['svg', 'pdf', 'empty', 'too_big', 'dimension', 'pixels', 'animated'])
def test_logo_rejeitado_sem_linha_arquivo_ou_auditoria(administracao_api, tmp_path, monkeypatch, kind):
    from app.routers import loja
    from PIL import Image
    from io import BytesIO
    c, h, sessions, _ = administracao_api
    monkeypatch.setattr(loja, 'UPLOAD_DIR', tmp_path)
    payload = {'svg': b'<svg onload="alert(1)"/>', 'pdf': b'%PDF-1.4', 'empty': b'',
               'too_big': b'x' * (2 * 1024 * 1024 + 1)}
    if kind in payload:
        data = payload[kind]
    elif kind == 'dimension':
        data = imagem(size=(2049, 1))
    elif kind == 'pixels':
        data = imagem(size=(2048, 2048))
    else:
        output = BytesIO()
        Image.new('RGB', (10, 10), 'red').save(output, format='PNG', save_all=True,
            append_images=[Image.new('RGB', (10, 10), 'blue')], duration=100)
        data = output.getvalue()
    r = c.post('/loja/logo', headers=h['admin'], files={'arquivo': ('logo.png', data, 'image/png')})
    assert r.status_code == 422, r.text
    with sessions() as db:
        assert db.query(Loja).count() == db.query(AuditLog).count() == 0
    assert not list(tmp_path.rglob('*.png'))


def test_logo_path_escapa_nao_servido(administracao_api, tmp_path, monkeypatch):
    from app.routers import loja
    c, h, sessions, _ = administracao_api
    monkeypatch.setattr(loja, 'UPLOAD_DIR', tmp_path)
    (tmp_path / 'fora.png').write_bytes(imagem())
    with sessions() as db:
        db.add(Loja(nome='Teste', logo_arquivo='../fora.png'))
        db.commit()
    assert c.get('/loja/logo', headers=h['admin']).status_code == 404


def test_inventario_permissoes_corresponde_rotas_e_matriz_restrita(administracao_api):
    c, h, _, _ = administracao_api
    assert c.get('/auth/permissoes').status_code in (401, 403)
    admin = c.get('/auth/permissoes', headers=h['admin']).json()
    entries = {(a['metodo'], a['rota']): a for a in admin['acoes']}
    assert len(entries) == len(admin['acoes'])
    assert ('POST', '/auth/login') not in entries and ('POST', '/auth/seed-admin') not in entries
    assert entries[('PATCH', '/loja')]['perfis'] == ['admin', 'financeiro']
    assert entries[('GET', '/auth/users')]['perfis'] == ['admin']
    for role in h:
        data = c.get('/auth/permissoes', headers=h[role]).json()
        if role != 'admin':
            assert data['matriz'] is None
            assert all(a['permitido'] and a['perfis'] == [role] for a in data['acoes'])
        allowed = {(a['metodo'], a['rota']) for a in data['acoes'] if a['permitido']}
        for method, path, body in [('GET', '/auth/users', None), ('PATCH', '/loja', {'nome': 'Loja válida'}), ('GET', '/loja', None)]:
            r = c.request(method, path, headers=h[role], json=body)
            assert (r.status_code != 403) == ((method, path) in allowed)
    assert len(admin['matriz']) == 4


def test_auditoria_identidade_detalhes_apenas_admin_sem_segredos(administracao_api):
    c, h, sessions, ids = administracao_api
    assert c.patch(f"/auth/users/{ids['consulta']}", headers=h['admin'], json={'nome': 'Nome auditado', 'email': 'auditado@example.com', 'motivo': 'Conferência humana'}).status_code == 200
    assert c.patch('/loja', headers=h['admin'], json={'nome': 'Empresa auditada', 'email': 'empresa@example.com'}).status_code == 200
    admin = c.get('/auditoria', headers=h['admin'])
    assert admin.status_code == 200, admin.text
    rows = admin.json()
    user = next(a for a in rows if a['acao'] == 'usuario_atualizado')
    before = user['antes'] if isinstance(user['antes'], dict) else json.loads(user['antes'])
    after = user['depois'] if isinstance(user['depois'], dict) else json.loads(user['depois'])
    assert before['nome'] == 'Pessoa consulta' and after['nome'] == 'Nome auditado'
    assert after['email'] == 'auditado@example.com'
    fin = c.get('/auditoria', headers=h['financeiro'])
    assert fin.status_code == 200
    assert 'auditado@example.com' not in fin.text and 'Pessoa consulta' not in fin.text
    assert all(a['antes'] is None and a['depois'] is None for a in fin.json())
    for role in ('consulta', 'operador'):
        assert c.get('/auditoria', headers=h[role]).status_code == 403
    exported = c.get('/export/auditoria.csv', headers=h['admin'])
    assert exported.status_code == 200, exported.text
    for value in (admin.text, fin.text, exported.text):
        assert 'Senha teste' not in value and 'senha_hash' not in value and 'pbkdf2$' not in value


def test_logo_subdiretorio_symlink_nao_expoe_arquivo(administracao_api, tmp_path, monkeypatch):
    from app.routers import loja
    c, h, sessions, _ = administracao_api
    monkeypatch.setattr(loja, 'UPLOAD_DIR', tmp_path)
    root = tmp_path / 'loja-logos'
    root.mkdir()
    outside = tmp_path / 'fora'
    outside.mkdir()
    (outside / 'privado.png').write_bytes(imagem())
    (root / 'atalho').symlink_to(outside, target_is_directory=True)
    with sessions() as db:
        db.add(Loja(nome='Loja', logo_arquivo='atalho/privado.png'))
        db.commit()
    assert c.get('/loja/logo', headers=h['consulta']).status_code == 404


def test_admin_conflito_email_nao_atualiza_ou_audita(administracao_api):
    c, h, sessions, ids = administracao_api
    r = c.patch(f"/auth/users/{ids['consulta']}", headers=h['admin'], json={'nome': 'Não aplicar', 'email': 'FINANCEIRO@administracao.local', 'perfil': 'admin'})
    assert r.status_code == 409
    with sessions() as db:
        u = db.get(User, ids['consulta'])
        assert u.nome == 'Pessoa consulta' and u.perfil == 'consulta'
        assert db.query(AuditLog).count() == 0


def test_logo_nao_admin_operador_sem_permissao_e_metadata_removida(administracao_api, tmp_path, monkeypatch):
    from app.routers import loja
    from PIL import Image, PngImagePlugin
    from io import BytesIO
    c, h, sessions, _ = administracao_api
    monkeypatch.setattr(loja, 'UPLOAD_DIR', tmp_path)
    output = BytesIO()
    meta = PngImagePlugin.PngInfo()
    meta.add_text('segredo', 'LOCAL-METADATA-SENTINELA')
    Image.new('RGB', (20, 20)).save(output, format='PNG', pnginfo=meta)
    data = output.getvalue()
    for role in ('operador', 'consulta'):
        assert c.post('/loja/logo', headers=h[role], files={'arquivo': ('logo.png', data, 'image/png')}).status_code == 403
    assert c.post('/loja/logo', files={'arquivo': ('logo.png', data, 'image/png')}).status_code in (401, 403)
    assert c.post('/loja/logo', headers=h['admin'], files={'arquivo': ('logo.png', data, 'image/png')}).status_code == 200
    assert b'LOCAL-METADATA-SENTINELA' not in c.get('/loja/logo', headers=h['admin']).content


def test_auditoria_whitelist_nao_exporta_objetos_tokens_ou_hash(administracao_api):
    c, h, sessions, ids = administracao_api
    forbidden = {'senha_hash': 'HASH-SENTINELA', 'token': 'TOKEN-SENTINELA', 'arquivo_path': '/SEGREDO-SENTINELA', 'nome': {'nested': 'OBJETO-SENTINELA'}}
    with sessions() as db:
        db.add(AuditLog(usuario_id=ids['admin'], acao='usuario_atualizado', entidade='users', entidade_id=ids['consulta'], antes=json.dumps(forbidden), depois=json.dumps({'email': 'pessoa@example.com', **forbidden})))
        db.commit()
    for role in ('admin', 'financeiro'):
        r = c.get('/auditoria', headers=h[role])
        assert r.status_code == 200
        assert all(s not in r.text for s in ('HASH-SENTINELA', 'TOKEN-SENTINELA', 'SEGREDO-SENTINELA', 'OBJETO-SENTINELA'))
        exported = c.get('/export/auditoria.csv', headers=h[role])
        assert exported.status_code == 200
        assert all(s not in exported.text for s in ('HASH-SENTINELA', 'TOKEN-SENTINELA', 'SEGREDO-SENTINELA', 'OBJETO-SENTINELA'))


def test_concorrencia_rebaixamentos_preserva_um_admin(administracao_api, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from time import sleep
    from sqlalchemy.orm import Query
    c, h, sessions, ids = administracao_api
    with sessions() as db:
        second = User(nome='Segundo admin', email='segundo@administracao.local', perfil='admin', ativo=True, senha_hash=hash_pw('Senha teste 123!'))
        db.add(second)
        db.commit()
        second_id = second.id
        second_header = {'Authorization': f'Bearer {token_for(second)}'}
    barrier = Barrier(2)
    original = Query.count
    def synchronized_count(query):
        result = original(query)
        entities = [entry.get('entity') for entry in query.column_descriptions]
        if entities == [User] and result == 2:
            sleep(0.15)
        return result
    monkeypatch.setattr(Query, 'count', synchronized_count)
    def downgrade(user_id, headers):
        barrier.wait(timeout=5)
        return c.patch(f'/auth/users/{user_id}', headers=headers, json={'perfil': 'consulta'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(downgrade, ids['admin'], h['admin']), pool.submit(downgrade, second_id, second_header)]
        results = [f.result() for f in futures]
    with sessions() as db:
        assert original(db.query(User).filter(User.perfil == 'admin', User.ativo.is_(True))) >= 1, [r.status_code for r in results]
    assert sorted(r.status_code for r in results) == [200, 422]


def test_admin_nao_contorna_senha_atual_pelos_endpoints_administrativos(administracao_api):
    c, h, sessions, ids = administracao_api
    own = f"/auth/users/{ids['admin']}"
    with sessions() as db:
        original_hash = db.get(User, ids['admin']).senha_hash
    assert c.patch(own, headers=h['admin'], json={'email': 'contorno@example.com'}).status_code == 422
    assert c.post(own + '/password', headers=h['admin'], json={'senha': 'Senha contornada 456!'}).status_code == 422
    with sessions() as db:
        admin = db.get(User, ids['admin'])
        assert admin.email == 'admin@administracao.local'
        assert admin.senha_hash == original_hash
        assert db.query(AuditLog).count() == 0
    # Salvar nome e email inalterado continua compatível com o formulário admin.
    assert c.patch(own, headers=h['admin'], json={'nome': 'Admin atualizado', 'email': 'admin@administracao.local'}).status_code == 200
    assert c.post(f"/auth/users/{ids['operador']}/password", headers=h['admin'], json={'senha': 'Senha redefinida 456!'}).status_code == 200
    assert c.post('/auth/me/password', headers=h['admin'], json={'senha_atual': 'Senha teste 123!', 'nova': 'Senha pessoal 456!'}).status_code == 200
    assert c.get('/auth/me', headers=h['admin']).status_code == 401
