"""Catálogos descritivos e preferências privadas, sem novos efeitos financeiros."""
import pytest
from tests.test_pagamentos import pagamentos_api, person, note, payment_payload
from app.models import NotaObrigacao, Pagamento, Movimentacao, CreditoConta


COLUMNS = {
    'cadastros': ['nome', 'tipo', 'documento', 'telefone', 'email', 'prazo_dias', 'ativo'],
    'notas': ['numero_documento', 'pessoa_nome', 'relacao', 'valor_original', 'valor_abatido', 'saldo_aberto', 'data_emissao', 'vencimento', 'status'],
    'pagamentos': ['codigo', 'tipo', 'forma', 'cliente_nome', 'fornecedor_nome', 'valor', 'data', 'cancelado'],
}


def catalog(c, h, kind, **data):
    r = c.post(f'/configuracoes/catalogos/{kind}', headers=h['admin'], json=data)
    assert r.status_code == 201, r.text
    return r.json()


def prefs(screen='notas', **extra):
    return {'colunas': [{'campo': f, 'visivel': True} for f in COLUMNS[screen]],
        'ordenacao': None, 'filtros': {}, **extra}


def test_catalogos_snapshot_congelado_e_desativacao_logica(pagamentos_api):
    c, h, sessions = pagamentos_api
    pid, forn = person(c, h, prazo_dias=5), person(c, h)
    op = catalog(c, h, 'operacoes', nome='Compra descritiva', aplicavel_em='ambos')
    prazo = catalog(c, h, 'condicoes', nome='Trinta dias', prazo_dias=30)
    forma = catalog(c, h, 'formas', nome='PIX balcão', forma_base='PIX')
    body = {'pessoa_id': pid, 'relacao': 'cliente', 'numero_documento': 'CAT-01', 'valor_original': 500,
        'data_emissao': '2020-01-01', 'descricao': 'Nota original', 'condicao_id': prazo['id'], 'operacao_id': op['id']}
    r = c.post('/notas', headers=h['admin'], json=body)
    assert r.status_code == 201, r.text
    n = r.json()
    assert n['prazo_dias_snapshot'] == 30 and n['vencimento'] == '2020-01-31'
    assert n['modo_vencimento'] == 'prazo_informado'
    assert n['condicao_nome_snapshot'] == 'Trinta dias' and n['operacao_nome_snapshot'] == 'Compra descritiva'
    pbody = payment_payload(cliente_id=pid, fornecedor_id=forn, forma_id=forma['id'], operacao_id=op['id'])
    p = c.post('/pagamentos', headers=h['admin'], json=pbody)
    assert p.status_code == 201, p.text
    for kind, row in (('operacoes', op), ('condicoes', prazo), ('formas', forma)):
        url = f"/configuracoes/catalogos/{kind}/{row['id']}"
        assert c.patch(url, headers=h['admin'], json={'nome': 'Nome alterado'}).status_code == 200
        assert c.post(url + '/desativar', headers=h['admin']).status_code == 200
        assert c.delete(url, headers=h['admin']).status_code in (404, 405)
    current = c.get(f"/notas/{n['id']}", headers=h['admin']).json()
    assert current['valor_original'] == current['saldo_aberto'] == 500
    assert current['condicao_nome_snapshot'] == 'Trinta dias'
    assert current['operacao_nome_snapshot'] == 'Compra descritiva'
    currentp = c.get(f"/pagamentos/{p.json()['id']}", headers=h['admin']).json()
    assert currentp['forma_nome_snapshot'] == 'PIX balcão'
    assert currentp['operacao_nome_snapshot'] == 'Compra descritiva'
    assert currentp['orcamentos']['cliente']['saldo_disponivel'] == 300
    replay = c.post('/pagamentos', headers=h['admin'], json=pbody)
    assert replay.status_code == 201 and replay.json()['id'] == p.json()['id']
    assert replay.json()['forma_nome_snapshot'] == 'PIX balcão'
    assert c.post('/notas', headers=h['admin'], json={**body, 'numero_documento': 'CAT-02'}).status_code == 422
    with sessions() as db:
        assert db.query(NotaObrigacao).count() == db.query(Pagamento).count() == 1
        assert db.query(Movimentacao).count() == db.query(CreditoConta).count() == 0


@pytest.mark.parametrize('kind,data', [('formas', {'nome': 'Cartão', 'forma_base': 'cartao'}),
    ('condicoes', {'nome': 'Negativo', 'prazo_dias': -1}), ('condicoes', {'nome': 'Grande', 'prazo_dias': 36501}),
    ('operacoes', {'nome': ''}), ('operacoes', {'nome': 'Op', 'aplicavel_em': 'inexistente'})])
def test_catalogos_invalidos(pagamentos_api, kind, data):
    c, h, _ = pagamentos_api
    assert c.post(f'/configuracoes/catalogos/{kind}', headers=h['admin'], json=data).status_code == 422


def test_selecao_incompativel_falha_sem_documento_parcial(pagamentos_api):
    c, h, sessions = pagamentos_api
    pid, forn = person(c, h), person(c, h)
    cash = catalog(c, h, 'formas', nome='Dinheiro', forma_base='dinheiro')
    op = catalog(c, h, 'operacoes', nome='Só pagamento', aplicavel_em='pagamentos')
    prazo = catalog(c, h, 'condicoes', nome='Prazo catálogo', prazo_dias=10)
    nbody = {'pessoa_id': pid, 'relacao': 'cliente', 'numero_documento': 'INV', 'valor_original': 100,
        'data_emissao': '2020-01-01', 'descricao': 'Inválida', 'modo_vencimento': 'sem_vencimento'}
    for extra in ({'operacao_id': op['id']}, {'operacao_id': 999999}, {'condicao_id': prazo['id']}, {'condicao_id': 999999}):
        assert c.post('/notas', headers=h['admin'], json={**nbody, **extra}).status_code == 422
    assert c.post('/pagamentos', headers=h['admin'], json=payment_payload(cliente_id=pid,
        fornecedor_id=forn, forma_id=cash['id'])).status_code == 422
    assert c.patch(f"/configuracoes/catalogos/condicoes/{prazo['id']}", headers=h['admin'], json={'prazo_dias': 20}).status_code == 422
    with sessions() as db:
        assert db.query(NotaObrigacao).count() == db.query(Pagamento).count() == 0


@pytest.mark.parametrize('perfil', ['admin', 'financeiro', 'operador', 'consulta'])
def test_permissoes_catalogo_e_preferencia_privada(pagamentos_api, perfil):
    c, h, _ = pagamentos_api
    url = '/configuracoes/catalogos/operacoes'
    assert c.get(url, headers=h[perfil]).status_code == 200
    r = c.post(url, headers=h[perfil], json={'nome': 'Operação perfil'})
    assert r.status_code == (201 if perfil in ('admin', 'financeiro') else 403)
    purl = '/configuracoes/tabelas/notas'
    assert c.get(purl, headers=h[perfil]).status_code == 200
    assert c.put(purl, headers=h[perfil], json=prefs()).status_code == 200
    assert c.delete(purl, headers=h[perfil]).status_code == 200
    assert c.get(url).status_code == c.get(purl).status_code == 401


def test_preferencia_isolada_usuario_tela_reset_e_no_get_write(pagamentos_api):
    c, h, sessions = pagamentos_api
    from app.models import Base
    with sessions() as db:
        before = {m.local_table.name: db.query(m.class_).count() for m in Base.registry.mappers}
    defaults = c.get('/configuracoes/tabelas/notas', headers=h['admin']).json()
    assert c.get('/configuracoes/tabelas/notas', headers=h['admin']).json() == defaults
    with sessions() as db:
        assert {m.local_table.name: db.query(m.class_).count() for m in Base.registry.mappers} == before
    body = prefs(ordenacao={'campo': 'saldo_aberto', 'direcao': 'desc'}, filtros={'status': 'aberto'})
    body['colunas'] = [body['colunas'][0], *reversed(body['colunas'][1:])]
    body['colunas'][1]['visivel'] = False
    r = c.put('/configuracoes/tabelas/notas', headers=h['admin'], json=body)
    assert r.status_code == 200, r.text
    own = c.get('/configuracoes/tabelas/notas', headers=h['admin']).json()
    assert own['colunas'] == body['colunas'] and own['ordenacao'] == body['ordenacao']
    other = c.get('/configuracoes/tabelas/notas', headers=h['financeiro']).json()
    assert other['ordenacao'] is None and all(x['visivel'] for x in other['colunas'])
    assert c.get('/configuracoes/tabelas/cadastros', headers=h['admin']).json()['ordenacao'] is None
    assert c.delete('/configuracoes/tabelas/notas', headers=h['admin']).status_code == 200
    assert c.get('/configuracoes/tabelas/notas', headers=h['admin']).json()['ordenacao'] is None


@pytest.mark.parametrize('variant', ['faltando', 'duplicada', 'desconhecida', 'principal', 'sort', 'direction', 'filters', 'uid'])
def test_preferencia_invalida_nao_substitui(pagamentos_api, variant):
    c, h, _ = pagamentos_api
    body = prefs()
    if variant == 'faltando': body['colunas'].pop()
    elif variant == 'duplicada': body['colunas'].append(body['colunas'][0])
    elif variant == 'desconhecida': body['colunas'][-1]['campo'] = 'segredo'
    elif variant == 'principal': body['colunas'][0]['visivel'] = False
    elif variant == 'sort': body['ordenacao'] = {'campo': 'senha_hash', 'direcao': 'asc'}
    elif variant == 'direction': body['ordenacao'] = {'campo': 'saldo_aberto', 'direcao': 'DROP TABLE'}
    elif variant == 'filters': body['filtros'] = {'sql': 'segredo'}
    else: body['user_id'] = 999999
    r = c.put('/configuracoes/tabelas/notas', headers=h['admin'], json=body)
    assert r.status_code == 422, r.text
    current = c.get('/configuracoes/tabelas/notas', headers=h['admin']).json()
    assert current['ordenacao'] is None and all(x['visivel'] for x in current['colunas'])


def test_ordenacao_notas_saldo_financeiro_e_invalid_sql_rejeitado(pagamentos_api):
    c, h, _ = pagamentos_api
    pid = person(c, h)
    ids = [note(c, h, pid, value=v)['id'] for v in (2, 100, 0.03)]
    r = c.get('/notas', headers=h['admin'], params={'pessoa_id': pid, 'ordenar_por': 'saldo_aberto', 'direcao': 'asc'})
    assert r.status_code == 200, r.text
    assert [n['id'] for n in r.json()] == [ids[2], ids[0], ids[1]]
    r = c.get('/notas', headers=h['admin'], params={'ordenar_por': 'valor_original;DROP TABLE notas_obrigacoes'})
    assert r.status_code == 422, r.text


def test_preferencia_concorrente_upsert_unico_sem_misturar_corpos(pagamentos_api):
    from concurrent.futures import ThreadPoolExecutor
    from app.models import PreferenciaTabela
    c, h, sessions = pagamentos_api
    first = prefs(ordenacao={'campo': 'saldo_aberto', 'direcao': 'asc'}, filtros={'status': 'aberto'})
    second = prefs(ordenacao={'campo': 'valor_original', 'direcao': 'desc'}, filtros={'status': 'quitado'})
    second['colunas'][-1]['visivel'] = False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda body: c.put('/configuracoes/tabelas/notas', headers=h['admin'], json=body), [first, second]))
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    current = c.get('/configuracoes/tabelas/notas', headers=h['admin']).json()
    assert current in (first, second)
    with sessions() as db:
        assert db.query(PreferenciaTabela).count() == 1
