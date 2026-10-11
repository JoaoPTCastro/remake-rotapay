"""Cadastros: cada teste usa banco próprio e restaura overrides anteriores.

O TestClient não executa lifespan: a inicialização nunca alcança pix.db.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import token_for
from app.database import get_db
from app.main import app
from app.models import Base, User


@pytest.fixture
def cadastro_api(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'cadastros.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        users = [User(nome=perfil, email=f"{perfil}@test.local", perfil=perfil,
                      senha_hash="fixture", ativo=True)
                 for perfil in ("admin", "consulta")]
        db.add_all(users)
        db.commit()
        headers = {u.perfil: {"Authorization": f"Bearer {token_for(u)}"}
                   for u in users}

    def isolated_db():
        with sessions() as db:
            yield db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = isolated_db
    client = TestClient(app)
    try:
        yield client, headers, sessions, engine
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def create_person(client, headers, **extra):
    response = client.post('/pessoas', json={'nome': 'Cadastro teste', 'tipo': 'ambos', **extra},
                           headers=headers['admin'])
    assert response.status_code == 201, response.text
    return response.json()['id']


def test_ambos_tem_um_id_nas_listas_legadas(cadastro_api):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h)
    for route in ('/pessoas', '/representantes', '/fornecedores'):
        result = c.get(route, headers=h['admin'])
        assert result.status_code == 200, result.text
        assert [p['id'] for p in result.json()] == [pid]


@pytest.mark.parametrize('patch', [
    {'nome': None}, {'nome': ''}, {'prazo_dias': -1},
    {'tolerancia_credito': -1}, {'prioridade': 4},
    {'tipo': 'inventado'}, {'campo_inexistente': 'x'},
])
def test_patch_invalido_nao_muda_cadastro(cadastro_api, patch):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h)
    response = c.patch(f'/pessoas/{pid}', json=patch, headers=h['admin'])
    assert response.status_code == 422, response.text
    assert c.get(f'/pessoas/{pid}', headers=h['admin']).json()['nome'] == 'Cadastro teste'


def test_consulta_pode_ler_mas_nao_escrever(cadastro_api):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h)
    assert c.get(f'/pessoas/{pid}', headers=h['consulta']).status_code == 200
    requests = [
        c.post('/pessoas', json={'nome': 'Intruso', 'tipo': 'cliente'}, headers=h['consulta']),
        c.patch(f'/pessoas/{pid}', json={'ativo': False}, headers=h['consulta']),
        c.post(f'/pessoas/{pid}/contatos', json={'nome': 'Contato'}, headers=h['consulta']),
        c.post(f'/pessoas/{pid}/chaves-pix', json={'chave': 'segredo'}, headers=h['consulta']),
    ]
    assert all(response.status_code == 403 for response in requests)


def test_remove_papel_com_historico_bloqueado(cadastro_api):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h)
    launch = c.post('/lancamentos', json={'tipo': 'debito', 'valor': 100,
                    'data': '2026-10-01', 'fornecedor_id': pid}, headers=h['admin'])
    assert launch.status_code == 201, launch.text
    response = c.patch(f'/pessoas/{pid}', json={'tipo': 'cliente'}, headers=h['admin'])
    assert response.status_code == 409, response.text
    assert c.get(f'/pessoas/{pid}', headers=h['admin']).json()['tipo'] == 'ambos'


def test_contatos_principais_sincronizam_legado(cadastro_api):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h)
    for name, phone in [('Responsável A', '111'), ('Responsável B', '222')]:
        response = c.post(f'/pessoas/{pid}/contatos', json={'nome': name,
                          'telefone': phone, 'principal': True}, headers=h['admin'])
        assert response.status_code == 201, response.text
    detail = c.get(f'/pessoas/{pid}', headers=h['admin']).json()
    assert detail['telefone'] == '222'
    assert sum(contact['principal'] for contact in detail['contatos']) == 1


def test_chave_inativa_nao_reaparece_por_fallback_legado(cadastro_api):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h)
    key = c.post(f'/pessoas/{pid}/chaves-pix', json={'chave': 'chave-a',
                 'principal': True}, headers=h['admin'])
    assert key.status_code == 201, key.text
    assert c.get(f'/chave-pix/{pid}').json()['chave_pix'] == 'chave-a'
    other = c.post(f'/pessoas/{pid}/chaves-pix', json={'chave': 'chave-b'}, headers=h['admin'])
    assert other.status_code == 201, other.text
    response = c.delete(f"/pessoas/{pid}/chaves-pix/{key.json()['id']}", headers=h['admin'])
    assert response.status_code == 200, response.text
    assert c.get(f'/chave-pix/{pid}').status_code == 404


def test_chave_expirada_bloqueia_publico_e_link(cadastro_api):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h)
    key = c.post(f'/pessoas/{pid}/chaves-pix', json={'chave': 'expirada',
                 'categoria': 'temporaria', 'validade': '2000-01-01', 'principal': True},
                 headers=h['admin'])
    assert key.status_code == 201, key.text
    assert c.get(f'/chave-pix/{pid}').status_code == 404
    response = c.post('/links', json={'representante_id': pid, 'fornecedor_id': pid},
                      headers=h['admin'])
    assert response.status_code == 422, response.text


def test_chave_temporaria_exige_validade(cadastro_api):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h)
    response = c.post(f'/pessoas/{pid}/chaves-pix',
                      json={'chave': 'sem-validade', 'categoria': 'temporaria'}, headers=h['admin'])
    assert response.status_code == 422, response.text


def test_backfill_preserva_id_e_nao_duplica(cadastro_api):
    from app.cadastros import backfill_pessoas
    from app.models import Pessoa, PessoaContato, PessoaChavePix
    _, _, sessions, _ = cadastro_api
    with sessions() as db:
        person = Pessoa(nome='Legado', tipo='fornecedor', telefone='123',
                        email='legado@test.local', chave_pix='antiga', banco='Banco', conta='Conta')
        db.add(person)
        db.commit()
        pid = person.id
        for _ in range(2):
            backfill_pessoas(db)
            db.commit()
        assert db.get(Pessoa, pid).chave_pix == 'antiga'
        assert db.query(PessoaContato).filter_by(pessoa_id=pid).count() == 1
        assert db.query(PessoaChavePix).filter_by(pessoa_id=pid).count() == 1


def test_troca_principal_preserva_destino_link_existente(cadastro_api):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h, chave_pix='chave-original')
    link = c.post('/links', json={'representante_id': pid, 'fornecedor_id': pid}, headers=h['admin'])
    assert link.status_code == 201, link.text
    token = link.json()['token']
    key = c.post(f'/pessoas/{pid}/chaves-pix', json={'chave': 'chave-nova',
                 'principal': True}, headers=h['admin'])
    assert key.status_code == 201, key.text
    public = c.get(f'/links/v/{token}')
    assert public.status_code == 200, public.text
    assert public.json()['chave_pix'] == 'chave-original'
    assert c.get(f'/chave-pix/{pid}').json()['chave_pix'] == 'chave-nova'


def test_patch_legado_nao_duplica_chaves(cadastro_api):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h, chave_pix='antiga')
    for _ in range(2):
        response = c.patch(f'/pessoas/{pid}', json={'chave_pix': 'nova'}, headers=h['admin'])
        assert response.status_code == 200, response.text
    assert c.get(f'/chave-pix/{pid}').json()['chave_pix'] == 'nova'
    detail = c.get(f'/pessoas/{pid}', headers=h['admin']).json()
    assert len(detail['chaves_pix']) == 1


def test_desativar_preserva_historico_e_bloqueia_chave(cadastro_api):
    c, h, sessions, _ = cadastro_api
    pid = create_person(c, h, chave_pix='chave-preservada')
    launch = c.post('/lancamentos', json={'tipo': 'debito', 'valor': 100,
                    'data': '2026-10-01', 'fornecedor_id': pid}, headers=h['admin'])
    assert launch.status_code == 201, launch.text
    response = c.post(f'/pessoas/{pid}/desativar', headers=h['admin'])
    assert response.status_code == 200, response.text
    assert c.get(f'/chave-pix/{pid}').status_code == 404
    from app.models import Lancamento
    with sessions() as db:
        assert db.get(Lancamento, launch.json()['id']).fornecedor_id == pid
    assert c.delete(f'/pessoas/{pid}', headers=h['admin']).status_code == 409


def test_patch_desativacao_principal_nao_escolhe_alternativa(cadastro_api):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h)
    key = c.post(f'/pessoas/{pid}/chaves-pix', json={'chave': 'principal',
                 'principal': True}, headers=h['admin'])
    assert key.status_code == 201, key.text
    c.post(f'/pessoas/{pid}/chaves-pix', json={'chave': 'alternativa'}, headers=h['admin'])
    response = c.patch(f"/pessoas/{pid}/chaves-pix/{key.json()['id']}",
                       json={'ativo': False}, headers=h['admin'])
    assert response.status_code == 200, response.text
    assert c.get(f'/chave-pix/{pid}').status_code == 404


def test_cliente_alias_preserva_lista_representantes(cadastro_api):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h, tipo='cliente')
    assert any(p['id'] == pid for p in c.get('/representantes', headers=h['admin']).json())
    assert not c.get('/fornecedores', headers=h['admin']).json()


def test_expiracao_futura_bloqueia_link_sem_editar_banco(cadastro_api, monkeypatch):
    from datetime import date
    import app.cadastros as cadastros
    c, h, _, _ = cadastro_api
    monkeypatch.setattr(cadastros, 'hoje', lambda: date(2026, 10, 1))
    pid = create_person(c, h)
    key = c.post(f'/pessoas/{pid}/chaves-pix', json={'chave': 'valida-hoje',
                 'categoria': 'temporaria', 'validade': '2026-10-01', 'principal': True}, headers=h['admin'])
    assert key.status_code == 201, key.text
    link = c.post('/links', json={'representante_id': pid, 'fornecedor_id': pid}, headers=h['admin'])
    assert link.status_code == 201, link.text
    token = link.json()['token']
    assert c.get(f'/links/v/{token}').status_code == 200
    monkeypatch.setattr(cadastros, 'hoje', lambda: date(2026, 10, 2))
    assert c.get(f'/chave-pix/{pid}').status_code == 404
    assert c.get(f'/links/v/{token}').status_code == 404


def test_child_de_outro_cadastro_nao_pode_ser_editado(cadastro_api):
    c, h, _, _ = cadastro_api
    first = create_person(c, h)
    second = create_person(c, h, nome='Outro cadastro')
    key = c.post(f'/pessoas/{first}/chaves-pix', json={'chave': 'protegida',
                 'principal': True}, headers=h['admin'])
    assert key.status_code == 201, key.text
    response = c.patch(f"/pessoas/{second}/chaves-pix/{key.json()['id']}",
                       json={'chave': 'alterada'}, headers=h['admin'])
    assert response.status_code == 404, response.text
    assert c.get(f'/chave-pix/{first}').json()['chave_pix'] == 'protegida'


@pytest.mark.parametrize('patch', [{'chave': 'destino-alterado'}, {'ativo': False}])
def test_link_fixo_recusa_chave_modificada_ou_inativa(cadastro_api, patch):
    c, h, _, _ = cadastro_api
    pid = create_person(c, h)
    key = c.post(f'/pessoas/{pid}/chaves-pix', json={'chave': 'destino-original',
                 'principal': True}, headers=h['admin'])
    assert key.status_code == 201, key.text
    link = c.post('/links', json={'representante_id': pid, 'fornecedor_id': pid}, headers=h['admin'])
    assert link.status_code == 201, link.text
    token = link.json()['token']
    response = c.patch(f"/pessoas/{pid}/chaves-pix/{key.json()['id']}",
                       json=patch, headers=h['admin'])
    assert response.status_code == 200, response.text
    assert c.get(f'/links/v/{token}').status_code == 404


def test_backfill_links_legados_preserva_destino_e_idempotente(cadastro_api):
    from app.cadastros import backfill_pessoas, backfill_links
    from app.models import Pessoa, LinkPagamento, PessoaChavePix
    c, h, sessions, _ = cadastro_api
    with sessions() as db:
        person = Pessoa(nome='Fornecedor legado', tipo='ambos', chave_pix='chave-migrada')
        db.add(person)
        db.flush()
        pid = person.id
        link = LinkPagamento(token='link-legado', representante_id=pid, fornecedor_id=pid)
        db.add(link)
        db.commit()
        lid = link.id
        for _ in range(2):
            backfill_pessoas(db)
            backfill_links(db)
            db.commit()
        assert db.get(LinkPagamento, lid).token == 'link-legado'
        assert db.query(PessoaChavePix).filter_by(pessoa_id=pid).count() == 1
    response = c.post(f'/pessoas/{pid}/chaves-pix', json={'chave': 'outra-principal',
                      'principal': True}, headers=h['admin'])
    assert response.status_code == 201, response.text
    with sessions() as db:
        backfill_pessoas(db)
        backfill_links(db)
        db.commit()
    response = c.get('/links/v/link-legado')
    assert response.status_code == 200, response.text
    assert response.json()['chave_pix'] == 'chave-migrada'


def test_backfill_link_sem_chave_nao_adota_destino_futuro(cadastro_api):
    from app.cadastros import backfill_pessoas, backfill_links
    from app.models import Pessoa, LinkPagamento
    c, h, sessions, _ = cadastro_api
    with sessions() as db:
        person = Pessoa(nome='Sem chave', tipo='ambos')
        db.add(person)
        db.flush()
        pid = person.id
        db.add(LinkPagamento(token='link-sem-chave', representante_id=pid, fornecedor_id=pid))
        db.commit()
        backfill_pessoas(db)
        backfill_links(db)
        db.commit()
    response = c.post(f'/pessoas/{pid}/chaves-pix', json={'chave': 'destino-futuro',
                      'principal': True}, headers=h['admin'])
    assert response.status_code == 201, response.text
    with sessions() as db:
        backfill_links(db)
        db.commit()
    assert c.get('/links/v/link-sem-chave').status_code == 404
