"""Notas documentais: bancos descartáveis, sem lifespan nem acesso ao PIX real."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.auth import hash_pw, token_for
from app.database import get_db
from app.main import app
from app.models import Base, User


@pytest.fixture
def notas_api(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'notas.db'}", connect_args={'check_same_thread': False, 'timeout': 15})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        users = [User(nome=p, email=f'{p}@notas.local', perfil=p, senha_hash=hash_pw('senha-teste'), ativo=True)
                 for p in ('admin', 'financeiro', 'operador', 'consulta')]
        db.add_all(users)
        db.commit()
        headers = {u.perfil: {'Authorization': f'Bearer {token_for(u)}'} for u in users}
    def isolated_db():
        with sessions() as db:
            yield db
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = isolated_db
    client = TestClient(app)
    try:
        yield client, headers, sessions
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def person(c, h, **extra):
    r = c.post('/pessoas', headers=h['admin'], json={'nome': 'Titular teste', 'tipo': 'ambos', 'prazo_dias': 10, **extra})
    assert r.status_code == 201, r.text
    return r.json()['id']


def note(c, h, pid, **extra):
    r = c.post('/notas', headers=h['admin'], json={'pessoa_id': pid, 'relacao': 'cliente',
        'numero_documento': 'NF-123', 'valor_original': 100, 'data_emissao': '2020-01-01',
        'descricao': 'Obrigação documental', **extra})
    assert r.status_code == 201, r.text
    return r.json()


def abat(c, h, nid, **extra):
    return c.post(f'/notas/{nid}/abatimentos', headers=h['admin'], json={'valor': 30,
        'data': '2020-01-03', 'referencia': 'Acerto externo', 'observacao': 'Conferido na loja',
        'chave_idempotencia': 'pagamento-1', **extra})


def test_parciais_preservam_original_id_e_historico(notas_api):
    c, h, _ = notas_api
    n = note(c, h, person(c, h))
    for index, value in enumerate((30, 20, 50)):
        r = abat(c, h, n['id'], valor=value, chave_idempotencia=f'parcial-{index}')
        assert r.status_code == 201, r.text
        d = c.get(f"/notas/{n['id']}", headers=h['admin']).json()
        assert d['id'] == n['id'] and d['valor_original'] == 100
    assert d['valor_abatido'] == 100 and d['saldo_aberto'] == 0
    assert len(c.get('/notas', headers=h['admin']).json()) == 1


def test_prazo_snapshot_nao_muda_com_cadastro(notas_api):
    c, h, _ = notas_api
    pid = person(c, h)
    n = note(c, h, pid)
    assert n['prazo_dias_snapshot'] == 10 and n['vencimento'] == '2020-01-11'
    assert c.patch(f'/pessoas/{pid}', headers=h['admin'], json={'prazo_dias': 90}).status_code == 200
    d = c.get(f"/notas/{n['id']}", headers=h['admin']).json()
    assert d['prazo_dias_snapshot'] == 10 and d['vencimento'] == n['vencimento']


def test_sem_vencimento_nunca_atrasada(notas_api):
    c, h, _ = notas_api
    n = note(c, h, person(c, h), modo_vencimento='sem_vencimento')
    assert n['vencimento'] is None and n['em_atraso'] is False


@pytest.mark.parametrize('role,relacao', [('fornecedor', 'cliente'), ('cliente', 'fornecedor')])
def test_papel_incompativel_recusado(notas_api, role, relacao):
    c, h, _ = notas_api
    pid = person(c, h, tipo=role)
    r = c.post('/notas', headers=h['admin'], json={'pessoa_id': pid, 'relacao': relacao,
        'numero_documento': 'NF', 'valor_original': 100, 'data_emissao': '2020-01-01', 'descricao': 'Nota'})
    assert r.status_code == 422, r.text


def test_cadastro_inativo_nao_recebe_nova_nota(notas_api):
    c, h, _ = notas_api
    pid = person(c, h)
    c.patch(f'/pessoas/{pid}', headers=h['admin'], json={'ativo': False})
    r = c.post('/notas', headers=h['admin'], json={'pessoa_id': pid, 'relacao': 'cliente',
        'numero_documento': 'NF', 'valor_original': 100, 'data_emissao': '2020-01-01', 'descricao': 'Nota'})
    assert r.status_code == 422, r.text


def test_nota_impede_remocao_papel_mas_permite_inativacao(notas_api):
    c, h, _ = notas_api
    pid = person(c, h)
    n = note(c, h, pid)
    assert c.patch(f'/pessoas/{pid}', headers=h['admin'], json={'tipo': 'fornecedor'}).status_code == 409
    assert c.patch(f'/pessoas/{pid}', headers=h['admin'], json={'ativo': False}).status_code == 200
    assert c.get(f"/notas/{n['id']}", headers=h['admin']).status_code == 200


def test_idempotencia_e_conflito(notas_api):
    c, h, _ = notas_api
    n = note(c, h, person(c, h))
    a = abat(c, h, n['id'])
    assert a.status_code == 201, a.text
    b = abat(c, h, n['id'])
    assert b.status_code in (200, 201), b.text
    assert a.json()['id'] == b.json()['id']
    assert abat(c, h, n['id'], valor=20).status_code == 409
    d = c.get(f"/notas/{n['id']}", headers=h['admin']).json()
    assert d['saldo_aberto'] == 70 and d['valor_abatido'] == 30


@pytest.mark.parametrize('valor', [0, -1, 100.001, 10000000000])
def test_valor_original_invalido(notas_api, valor):
    c, h, _ = notas_api
    pid = person(c, h)
    r = c.post('/notas', headers=h['admin'], json={'pessoa_id': pid, 'relacao': 'cliente',
        'numero_documento': 'NF', 'valor_original': valor, 'data_emissao': '2020-01-01', 'descricao': 'Nota'})
    assert r.status_code == 422, r.text


def test_excesso_e_observacao_vazia_recusados(notas_api):
    c, h, _ = notas_api
    n = note(c, h, person(c, h))
    assert abat(c, h, n['id'], valor=101).status_code == 422
    assert abat(c, h, n['id'], observacao='   ').status_code == 422
    assert c.get(f"/notas/{n['id']}", headers=h['admin']).json()['saldo_aberto'] == 100


def test_estorno_senha_motivo_e_repeticao(notas_api):
    c, h, _ = notas_api
    n = note(c, h, person(c, h))
    a = abat(c, h, n['id'])
    assert a.status_code == 201, a.text
    url = f"/notas/{n['id']}/abatimentos/{a.json()['id']}/estornar"
    assert c.post(url, headers=h['admin'], json={'motivo': 'Erro'}).status_code == 422
    assert c.post(url, headers=h['admin'], json={'motivo': 'Erro', 'senha': 'errada'}).status_code == 403
    assert c.post(url, headers=h['admin'], json={'motivo': '   ', 'senha': 'senha-teste'}).status_code == 422
    r = c.post(url, headers=h['admin'], json={'motivo': 'Duplicidade externa', 'senha': 'senha-teste'})
    assert r.status_code == 200, r.text
    assert c.get(f"/notas/{n['id']}", headers=h['admin']).json()['saldo_aberto'] == 100
    assert c.post(url, headers=h['admin'], json={'motivo': 'Repetição', 'senha': 'senha-teste'}).status_code == 422


def test_cancelamento_preserva_documento(notas_api):
    c, h, _ = notas_api
    n = note(c, h, person(c, h))
    url = f"/notas/{n['id']}/cancelar"
    assert c.post(url, headers=h['admin'], json={'motivo': 'Erro'}).status_code == 422
    r = c.post(url, headers=h['admin'], json={'motivo': 'Documento inválido', 'senha': 'senha-teste'})
    assert r.status_code == 200, r.text
    d = c.get(f"/notas/{n['id']}", headers=h['admin']).json()
    assert d['valor_original'] == 100 and d['status'] == 'cancelado'
    assert abat(c, h, n['id']).status_code in (409, 422)


def test_leitura_e_escrita_por_perfil(notas_api):
    c, h, _ = notas_api
    pid = person(c, h)
    n = note(c, h, pid)
    for perfil in ('consulta', 'operador'):
        assert c.get('/notas', headers=h[perfil]).status_code == 200
        assert c.get(f'/pessoas/{pid}/extrato-notas?relacao=cliente', headers=h[perfil]).status_code == 200
        assert c.post(f"/notas/{n['id']}/abatimentos", headers=h[perfil], json={'valor': 1, 'data': '2020-01-03',
            'referencia': 'Teste', 'observacao': 'Teste', 'chave_idempotencia': perfil}).status_code == 403
    assert c.get('/notas').status_code in (401, 403)


def test_concorrencia_nao_excede_saldo(notas_api):
    c, h, _ = notas_api
    n = note(c, h, person(c, h))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(abat, c, h, n['id'], valor=100, chave_idempotencia=f'concorrente-{i}') for i in range(2)]
        responses = [f.result() for f in futures]
    assert sorted(r.status_code for r in responses) in ([201, 409], [201, 422]), [r.text for r in responses]
    d = c.get(f"/notas/{n['id']}", headers=h['admin']).json()
    assert d['saldo_aberto'] == 0 and d['valor_abatido'] == 100


def test_extratos_independentes_e_motor_pix_intacto(notas_api):
    from app.models import Movimentacao, Lancamento, Conciliacao
    c, h, sessions = notas_api
    pid = person(c, h)
    cliente = note(c, h, pid, valor_original=200)
    fornecedor = note(c, h, pid, relacao='fornecedor', valor_original=500)
    assert abat(c, h, cliente['id'], valor=50).status_code == 201
    assert abat(c, h, fornecedor['id'], valor=100, chave_idempotencia='fornecedor-1').status_code == 201
    for role, original, paid, saldo, nid in [('cliente', 200, 50, 150, cliente['id']), ('fornecedor', 500, 100, 400, fornecedor['id'])]:
        r = c.get(f'/pessoas/{pid}/extrato-notas?relacao={role}', headers=h['admin'])
        assert r.status_code == 200, r.text
        d = r.json()
        assert d['origem'] == 'notas_rotapay'
        assert d['resumo']['valor_original'] == original and d['resumo']['valor_abatido'] == paid
        assert d['resumo']['saldo_aberto'] == saldo and [n['id'] for n in d['notas']] == [nid]
    with sessions() as db:
        assert all(db.query(model).count() == 0 for model in (Movimentacao, Lancamento, Conciliacao))


def test_anexos_autenticados_ownership_e_exclusao_logica(notas_api, tmp_path, monkeypatch):
    import app.routers.notas as router
    monkeypatch.setattr(router, 'UPLOAD_DIR', str(tmp_path / 'uploads'))
    c, h, _ = notas_api
    pid = person(c, h)
    n = note(c, h, pid)
    other = note(c, h, pid, numero_documento='Outra')
    pdf = b'%PDF-1.4\nconteudo demonstrativo\n%%EOF'
    r = c.post(f"/notas/{n['id']}/anexos", headers=h['admin'], files={'f': ('../../comprovante.pdf', pdf, 'application/octet-stream')})
    assert r.status_code == 201, r.text
    aid = r.json()['id']
    url = f"/notas/{n['id']}/anexos/{aid}/arquivo"
    assert c.get(url).status_code in (401, 403)
    download = c.get(url, headers=h['consulta'])
    assert download.status_code == 200 and download.content == pdf
    assert c.get(f"/notas/{other['id']}/anexos/{aid}/arquivo", headers=h['admin']).status_code == 404
    assert c.delete(f"/notas/{n['id']}/anexos/{aid}", headers=h['consulta']).status_code == 403
    assert c.delete(f"/notas/{n['id']}/anexos/{aid}", headers=h['admin']).status_code == 200
    assert c.get(url, headers=h['admin']).status_code == 404


def test_anexo_recusa_extensao_conteudo_e_tamanho(notas_api, tmp_path, monkeypatch):
    import app.routers.notas as router
    monkeypatch.setattr(router, 'UPLOAD_DIR', str(tmp_path / 'uploads'))
    c, h, _ = notas_api
    n = note(c, h, person(c, h))
    url = f"/notas/{n['id']}/anexos"
    for filename, data in [('fraude.pdf', b'<script>executar</script>'), ('arquivo.html', b'%PDF-1.4')]:
        r = c.post(url, headers=h['admin'], files={'f': (filename, data, 'application/pdf')})
        assert r.status_code in (400, 415, 422), r.text


def test_anexo_limite_real_e_arquivo_fora_raiz(notas_api, tmp_path, monkeypatch):
    import app.routers.notas as router
    from app.models import NotaAnexo
    monkeypatch.setattr(router, 'UPLOAD_DIR', str(tmp_path / 'uploads'))
    monkeypatch.setattr(router, 'MAX_UPLOAD_MB', 1)
    c, h, sessions = notas_api
    n = note(c, h, person(c, h))
    url = f"/notas/{n['id']}/anexos"
    oversized = b'%PDF-' + b'x' * (1024 * 1024)
    r = c.post(url, headers=h['admin'], files={'f': ('grande.pdf', oversized, 'application/pdf')})
    assert r.status_code == 422
    assert c.get(f"/notas/{n['id']}", headers=h['admin']).json()['anexos'] == []
    outside = tmp_path / 'segredo.pdf'
    outside.write_bytes(b'%PDF-segredo')
    with sessions() as db:
        a = NotaAnexo(nota_id=n['id'], nome_original='fora.pdf', arquivo_path=str(outside), tamanho=12, created_by=1)
        db.add(a)
        db.commit()
        aid = a.id
    assert c.get(f"/notas/{n['id']}/anexos/{aid}/arquivo", headers=h['admin']).status_code == 404


def test_duplicidade_documento_e_cancelamento_com_abatimento(notas_api):
    c, h, _ = notas_api
    pid = person(c, h)
    n = note(c, h, pid)
    payload = {'pessoa_id': pid, 'relacao': 'cliente', 'numero_documento': 'NF-123',
        'valor_original': 100, 'data_emissao': '2020-01-01', 'descricao': 'Duplicada'}
    assert c.post('/notas', headers=h['admin'], json=payload).status_code == 409
    a = abat(c, h, n['id'])
    assert a.status_code == 201
    url = f"/notas/{n['id']}/cancelar"
    assert c.post(url, headers=h['admin'], json={'senha': 'senha-teste', 'motivo': 'Correção'}).status_code == 422
    detail = c.get(f"/notas/{n['id']}", headers=h['admin']).json()
    assert detail['saldo_aberto'] == 70 and detail['status'] == 'parcial'
    assert detail['abatimentos'][0]['observacao'] == 'Conferido na loja'
    assert detail['abatimentos'][0]['origem'] == 'registro_documental'


def test_vencimento_explicito_prazo_e_validacao(notas_api):
    c, h, _ = notas_api
    pid = person(c, h)
    n = note(c, h, pid, numero_documento='Prazo', modo_vencimento='prazo_informado', prazo_dias=5)
    assert n['vencimento'] == '2020-01-06' and n['prazo_dias_snapshot'] == 5
    n = note(c, h, pid, numero_documento='Data', modo_vencimento='data', vencimento='2020-02-01')
    assert n['vencimento'] == '2020-02-01'
    base = {'pessoa_id': pid, 'relacao': 'cliente', 'numero_documento': 'Inválido',
        'valor_original': 100, 'data_emissao': '2020-01-01', 'descricao': 'Teste'}
    for extra in ({'modo_vencimento': 'data'}, {'modo_vencimento': 'prazo_informado'},
                  {'modo_vencimento': 'prazo_informado', 'prazo_dias': -1}):
        assert c.post('/notas', headers=h['admin'], json={**base, **extra}).status_code == 422


def test_financeiro_escreve_e_original_nao_editavel(notas_api):
    c, h, _ = notas_api
    pid = person(c, h)
    r = c.post('/notas', headers=h['financeiro'], json={'pessoa_id': pid, 'relacao': 'cliente',
        'numero_documento': 'Financeiro', 'valor_original': 100, 'data_emissao': '2020-01-01', 'descricao': 'Teste'})
    assert r.status_code == 201
    nid = r.json()['id']
    assert c.patch(f'/notas/{nid}', headers=h['admin'], json={'valor_original': 5}).status_code == 405
    assert c.delete(f'/notas/{nid}', headers=h['admin']).status_code == 405
    assert c.get(f'/notas/{nid}', headers=h['consulta']).json()['valor_original'] == 100


def test_abatimento_exige_data_ja_ocorrida(notas_api):
    from datetime import timedelta
    from app.cadastros import hoje
    c, h, _ = notas_api
    n = note(c, h, person(c, h))
    for data in ('2019-12-31', (hoje() + timedelta(days=1)).isoformat()):
        r = abat(c, h, n['id'], data=data)
        assert r.status_code == 422, r.text
    assert c.get(f"/notas/{n['id']}", headers=h['admin']).json()['saldo_aberto'] == 100


def test_numero_documento_escopo_titular_e_relacao(notas_api):
    c, h, _ = notas_api
    pid = person(c, h)
    one = note(c, h, pid)
    two = note(c, h, pid, relacao='fornecedor')
    three = note(c, h, person(c, h, nome='Outro titular'))
    assert len({one['id'], two['id'], three['id']}) == 3


@pytest.mark.parametrize('valor', ['NaN', 'Infinity', '-Infinity'])
def test_dinheiro_nao_finito_recusado(notas_api, valor):
    c, h, _ = notas_api
    pid = person(c, h)
    r = c.post('/notas', headers=h['admin'], json={'pessoa_id': pid, 'relacao': 'cliente',
        'numero_documento': 'NF-finito', 'valor_original': valor, 'data_emissao': '2020-01-01', 'descricao': 'Teste'})
    assert r.status_code == 422, r.text
    n = note(c, h, pid)
    assert abat(c, h, n['id'], valor=valor).status_code == 422


def test_reenvio_abatimento_estornado_nao_reaplica(notas_api):
    c, h, _ = notas_api
    pid = person(c, h)
    n = note(c, h, pid)
    a = abat(c, h, n['id'])
    aid = a.json()['id']
    r = c.post(f"/notas/{n['id']}/abatimentos/{aid}/estornar", headers=h['admin'],
        json={'senha': 'senha-teste', 'motivo': 'Duplicidade'})
    assert r.status_code == 200
    replay = abat(c, h, n['id'])
    assert replay.status_code == 201 and replay.json()['id'] == aid and replay.json()['estornado'] is True
    assert c.get(f"/notas/{n['id']}", headers=h['admin']).json()['saldo_aberto'] == 100
    assert c.post(f"/notas/{n['id']}/cancelar", headers=h['admin'],
        json={'senha': 'senha-teste', 'motivo': 'Documento inválido'}).status_code == 200
    extrato = c.get(f'/pessoas/{pid}/extrato-notas?relacao=cliente', headers=h['admin']).json()
    assert extrato['resumo']['saldo_aberto'] == 0 and extrato['resumo']['valor_original'] == 0
    assert extrato['notas'][0]['id'] == n['id']


def test_filtro_quitado_e_atraso_usam_centavos(notas_api):
    c, h, _ = notas_api
    n = note(c, h, person(c, h), valor_original=0.30)
    assert abat(c, h, n['id'], valor=0.10, chave_idempotencia='centavos-1').status_code == 201
    assert abat(c, h, n['id'], valor=0.20, chave_idempotencia='centavos-2').status_code == 201
    quitadas = c.get('/notas?status=quitado', headers=h['admin']).json()
    assert [r['id'] for r in quitadas] == [n['id']]
    assert quitadas[0]['saldo_aberto'] == 0
    assert c.get('/notas?status=parcial', headers=h['admin']).json() == []
    assert c.get('/notas?em_atraso=true', headers=h['admin']).json() == []


def test_senha_com_espacos_e_motivo_limpo(notas_api):
    c, h, sessions = notas_api
    n = note(c, h, person(c, h))
    a = abat(c, h, n['id']).json()
    with sessions() as db:
        u = db.query(User).filter_by(perfil='admin').one()
        u.senha_hash = hash_pw(' senha com espaços ')
        db.commit()
        auth = {'Authorization': f'Bearer {token_for(u)}'}
    endpoint = f"/notas/{n['id']}/abatimentos/{a['id']}/estornar"
    assert c.post(endpoint, headers=auth, json={'senha': 'senha com espaços', 'motivo': 'Correção'}).status_code == 403
    assert c.post(endpoint, headers=auth, json={'senha': ' senha com espaços ', 'motivo': '   '}).status_code == 422
    r = c.post(endpoint, headers=auth, json={'senha': ' senha com espaços ', 'motivo': ' Correção documental '})
    assert r.status_code == 200, r.text
    assert r.json()['estorno']['motivo'] == 'Correção documental'
