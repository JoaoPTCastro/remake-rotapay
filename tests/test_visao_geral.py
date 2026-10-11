"""Visão global com oráculos financeiros independentes e leituras sem mutação."""
import csv
import io
from decimal import Decimal
from datetime import date
import pytest
from tests.test_pagamentos import pagamentos_api, person, note, payment, apply
from tests.test_creditos import origin, credit, use, undo
from tests.test_legado import snapshot
from app.models import Pessoa, Movimentacao, Lancamento, Projecao


def get(c, h, path='/visao-geral/resumo', **params):
    r = c.get(path, headers=h['admin'], params=params)
    assert r.status_code == 200, r.text
    assert r.headers.get('cache-control') == 'private, no-store'
    return r.json()


def extrato(c, h, pid, relation):
    r = c.get(f'/extratos/{pid}', headers=h['admin'], params={'relacao': relation})
    assert r.status_code == 200, r.text
    return r.json()['totais_globais']


def summed(values):
    first = values[0]
    if isinstance(first, dict):
        return {key: summed([x[key] for x in values]) for key in first}
    return float(sum(Decimal(str(x)) for x in values))


@pytest.fixture
def visao_api(pagamentos_api):
    c, h, sessions = pagamentos_api
    a = person(c, h, nome='Titular Alpha')
    b = person(c, h, nome='Titular Beta')
    other = person(c, h, nome='Sem histórico')
    na = note(c, h, a, value=500)
    nb = note(c, h, b, value=300)
    nf = note(c, h, a, 'fornecedor', value=800)
    direct = payment(c, h, cliente_id=a, fornecedor_id=a, valor=250)
    incoming = payment(c, h, tipo='cliente_loja', cliente_id=b, valor=200)
    outgoing = payment(c, h, tipo='repasse_fornecedor', fornecedor_id=a,
        pagamento_origem_id=incoming['id'], valor=80)
    assert apply(c, h, direct['id'], na['id'], valor=100).status_code == 201
    assert apply(c, h, direct['id'], nf['id'], 'fornecedor', valor=90).status_code == 201
    return c, h, sessions, {'a': a, 'b': b, 'other': other, 'na': na, 'nb': nb, 'nf': nf,
        'direct': direct, 'incoming': incoming, 'outgoing': outgoing}


def test_global_igual_soma_extratos_por_titular_relacao(visao_api):
    c, h, sessions, ids = visao_api
    before = snapshot(sessions)
    global_ = get(c, h)
    for relation in ('cliente', 'fornecedor'):
        expected = summed([extrato(c, h, ids[key], relation) for key in ('a', 'b', 'other')])
        assert global_['contas'][relation] == expected
    assert snapshot(sessions) == before


def test_caixa_conta_fatos_uma_vez_e_separa_pix_direto(visao_api):
    c, h, _, _ = visao_api
    flow = get(c, h)['fluxo_caixa']
    assert flow['entradas_cliente_loja'] == 200
    assert flow['saidas_repasse_fornecedor'] == 80
    assert flow['saldo_liquido'] == 120
    assert flow['pagamentos_diretos_cliente_fornecedor'] == 250
    assert flow['quantidade_entradas'] == flow['quantidade_saidas'] == flow['quantidade_diretos'] == 1


def test_titular_inativo_e_tipo_historico_nao_apagam_saldos(visao_api):
    c, h, sessions, ids = visao_api
    before = get(c, h)['contas']
    with sessions() as db:
        p = db.get(Pessoa, ids['a'])
        p.ativo = False
        p.tipo = 'fornecedor'
        db.commit()
    assert get(c, h)['contas'] == before
    expected = extrato(c, h, ids['a'], 'cliente')
    rows = get(c, h, '/visao-geral/posicoes', relacao='cliente', pessoa_id=ids['a'])['itens']
    assert len(rows) == 1 and rows[0]['totais_globais'] == expected
    assert rows[0]['pessoa']['ativo'] is False


def test_legado_nao_entra_na_visao_nova(visao_api):
    c, h, sessions, ids = visao_api
    before = get(c, h)
    with sessions() as db:
        db.add(Movimentacao(codigo='PIX-LEGADO-GLOBAL', data_pix=date(2026, 1, 1), valor=99999,
            saldo_disponivel=99999, representante_id=ids['a'], fornecedor_id=ids['a'],
            link_token='SEGREDO-PUBLICO-LEGADO', comprovante_path='/privado/comprovante.pdf'))
        db.add(Lancamento(tipo='credito', valor=99999, saldo_aberto=99999, data=date(2026, 1, 1), representante_id=ids['a']))
        db.add(Projecao(representante_id=ids['a'], fornecedor_id=ids['a'], valor_projetado=99999, valor_conciliado=0))
        db.commit()
    assert get(c, h) == before


def test_credito_reconhecido_substitui_sobra_e_estorno_reverte_sem_caixa(pagamentos_api):
    c, h, sessions = pagamentos_api
    pid, p, a = origin(c, h)
    initial_flow = get(c, h)['fluxo_caixa']
    cr = credit(c, h, p, a)
    totals = get(c, h)['contas']['cliente']
    assert totals['pagamentos']['saldo_disponivel'] == 0
    assert totals['creditos']['saldo_disponivel'] == 100
    assert totals['disponibilidade_total_para_abater'] == 100
    n = note(c, h, pid, value=500)
    used = use(c, h, cr, n['id'])
    assert used.status_code == 201, used.text
    totals = get(c, h)['contas']['cliente']
    assert totals['creditos']['saldo_disponivel'] == 40
    assert totals['notas']['saldo_aberto'] == 440
    assert get(c, h)['fluxo_caixa'] == initial_flow
    assert c.post(f"/creditos/{cr['id']}/aplicacoes/{used.json()['id']}/estornar", headers=h['admin'], json=undo()).status_code == 200
    totals = get(c, h)['contas']['cliente']
    assert totals['creditos']['saldo_disponivel'] == 100 and totals['notas']['saldo_aberto'] == 500
    assert c.post(f"/creditos/{cr['id']}/reverter", headers=h['admin'], json=undo()).status_code == 200
    totals = get(c, h)['contas']['cliente']
    assert totals['pagamentos']['saldo_disponivel'] == 100 and totals['creditos']['saldo_disponivel'] == 0
    assert get(c, h)['fluxo_caixa'] == initial_flow


@pytest.mark.parametrize('role', ['admin', 'financeiro', 'operador', 'consulta'])
def test_todas_leituras_privadas_por_perfil_sem_mutacao(visao_api, role):
    c, h, sessions, _ = visao_api
    before = snapshot(sessions)
    for path in ('/visao-geral/resumo', '/visao-geral/posicoes', '/visao-geral/fila', '/visao-geral/export.csv'):
        r = c.get(path, headers=h[role], params={'relacao': 'cliente'})
        assert r.status_code == 200, r.text
        assert r.headers['cache-control'] == 'private, no-store'
        assert c.get(path, params={'relacao': 'cliente'}).status_code == 401
        assert c.get(path, headers={'Authorization': 'Bearer ' + 'x' * 43}, params={'relacao': 'cliente'}).status_code == 401
    assert snapshot(sessions) == before


@pytest.mark.parametrize('params', [{'relacao': 'ambos'}, {'pessoa_id': 0}, {'limit': 0}, {'limit': 101},
    {'offset': -1}, {'offset': 100001}, {'pessoa_id': '1 OR 1=1'}])
def test_filtros_invalidos_nao_escrevem(visao_api, params):
    c, h, sessions, _ = visao_api
    before = snapshot(sessions)
    for path in ('/visao-geral/posicoes', '/visao-geral/fila'):
        assert c.get(path, headers=h['admin'], params=params).status_code == 422
    assert snapshot(sessions) == before


def test_estorno_aplicacao_cancelamento_pagamento_e_nota_nao_duplicam_contas(visao_api):
    c, h, _, ids = visao_api
    p = payment(c, h, tipo='cliente_loja', cliente_id=ids['b'], valor=50)
    applied = apply(c, h, p['id'], ids['nb']['id'], valor=50).json()
    out = get(c, h)
    assert out['contas']['cliente']['notas']['valor_abatido'] == 150
    assert out['fluxo_caixa']['entradas_cliente_loja'] == 250
    assert c.post(f"/pagamentos/{p['id']}/aplicacoes/{applied['id']}/estornar", headers=h['admin'], json=undo()).status_code == 200
    assert c.post(f"/pagamentos/{p['id']}/cancelar", headers=h['admin'], json=undo()).status_code == 200
    out = get(c, h)
    assert out['contas']['cliente']['notas']['valor_abatido'] == 100
    assert out['fluxo_caixa']['entradas_cliente_loja'] == 200
    assert out['contas']['cliente']['pagamentos']['quantidade_cancelados'] == 1
    assert c.post(f"/notas/{ids['nb']['id']}/cancelar", headers=h['admin'], json=undo()).status_code == 200
    assert get(c, h)['contas']['cliente']['notas']['valor_original'] == 500


def test_fila_so_notas_abertas_ordem_documental_e_leitura(visao_api):
    from app.models import NotaObrigacao
    c, h, sessions, ids = visao_api
    n1 = note(c, h, ids['a'], value=1)
    n2 = note(c, h, ids['a'], value=2)
    with sessions() as db:
        db.get(NotaObrigacao, n1['id']).vencimento = date(2020, 1, 1)
        db.get(NotaObrigacao, n2['id']).vencimento = date(2020, 1, 2)
        db.commit()
    canceled = note(c, h, ids['a'], value=3)
    assert c.post(f"/notas/{canceled['id']}/cancelar", headers=h['admin'], json=undo()).status_code == 200
    paid = note(c, h, ids['a'], value=4)
    p = payment(c, h, cliente_id=ids['a'], fornecedor_id=ids['a'], valor=4)
    assert apply(c, h, p['id'], paid['id'], valor=4).status_code == 201
    before = snapshot(sessions)
    out = get(c, h, '/visao-geral/fila', relacao='cliente', pessoa_id=ids['a'])
    row_ids = [r['id'] for r in out['itens']]
    assert row_ids[:2] == [n1['id'], n2['id']]
    assert canceled['id'] not in row_ids and paid['id'] not in row_ids
    assert all(r['saldo_aberto'] > 0 for r in out['itens'])
    assert snapshot(sessions) == before


def test_paginacao_preserva_totais_e_csv_filtrado(visao_api):
    c, h, sessions, ids = visao_api
    before = snapshot(sessions)
    global_before = get(c, h)
    first = get(c, h, '/visao-geral/posicoes', relacao='cliente', limit=1)
    second = get(c, h, '/visao-geral/posicoes', relacao='cliente', limit=1, offset=1)
    assert first['total_filtrado'] == second['total_filtrado'] == 3
    assert first['tem_mais'] is True
    assert first['itens'][0]['pessoa']['id'] != second['itens'][0]['pessoa']['id']
    for page in (first, second):
        row = page['itens'][0]
        assert row['totais_globais'] == extrato(c, h, row['pessoa']['id'], 'cliente')
    csv_response = c.get('/visao-geral/export.csv', headers=h['admin'], params={'relacao': 'cliente', 'pessoa_id': ids['a']})
    assert csv_response.status_code == 200
    assert csv_response.content.startswith(b'\xef\xbb\xbf')
    rows = list(csv.DictReader(io.StringIO(csv_response.text.lstrip('\ufeff')), delimiter=';'))
    assert len(rows) == 1 and rows[0]['pessoa_id'] == str(ids['a'])
    assert rows[0]['notas_saldo_aberto'] == '400,00'
    assert rows[0]['pagamentos_saldo_disponivel'] == '150,00'
    assert get(c, h) == global_before
    assert snapshot(sessions) == before


@pytest.mark.parametrize('name', ['=SUM(1;2)', ' +1', '\t@danger', '-1', 'normal;com separador'])
def test_csv_neutraliza_formula_e_preserva_colunas(pagamentos_api, name):
    c, h, sessions = pagamentos_api
    pid = person(c, h, nome=name)
    # Imported legacy names may retain whitespace stripped by current forms.
    with sessions() as db:
        db.get(Pessoa, pid).nome = name
        db.commit()
    response = c.get('/visao-geral/export.csv', headers=h['admin'], params={'relacao': 'cliente', 'pessoa_id': pid})
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text.lstrip('\ufeff')), delimiter=';'))
    assert len(rows) == 1
    assert rows[0]['pessoa_nome'] == (name if name.startswith('normal') else "'" + name)
    assert rows[0]['relacao'] == 'cliente'


def test_busca_percentual_e_sublinhado_sao_literais(pagamentos_api):
    c, h, _ = pagamentos_api
    target = person(c, h, nome='Literal %_ especial')
    person(c, h, nome='Outra pessoa')
    for path in ('/visao-geral/posicoes', '/visao-geral/fila'):
        if path.endswith('/fila'):
            note(c, h, target)
        result = get(c, h, path, relacao='cliente', q='%_')
        assert result['total_filtrado'] == 1
        row = result['itens'][0]
        assert (row.get('pessoa') or {'id': row['pessoa_id']})['id'] == target


def test_export_limite_rejeita_sem_truncar(visao_api, monkeypatch):
    from app.routers import visao_geral
    c, h, _, ids = visao_api
    monkeypatch.setattr(visao_geral, 'MAX_EXPORT', 2)
    response = c.get('/visao-geral/export.csv', headers=h['admin'], params={'relacao': 'cliente'})
    assert response.status_code == 413
    assert 'refine os filtros' in response.json()['detail']
    filtered = c.get('/visao-geral/export.csv', headers=h['admin'], params={'relacao': 'cliente', 'pessoa_id': ids['a']})
    assert filtered.status_code == 200


def test_centavos_oraculo_independente_por_relacao(pagamentos_api):
    c, h, _ = pagamentos_api
    a = person(c, h)
    b = person(c, h)
    for pid, value in ((a, 0.10), (b, 0.20)):
        note(c, h, pid, value=value)
        payment(c, h, tipo='cliente_loja', cliente_id=pid, valor=value)
    result = get(c, h)
    assert result['contas']['cliente']['notas']['saldo_aberto'] == 0.30
    assert result['contas']['cliente']['pagamentos']['saldo_disponivel'] == 0.30
    assert result['contas']['fornecedor']['notas']['saldo_aberto'] == 0
    assert result['fluxo_caixa']['entradas_cliente_loja'] == 0.30
