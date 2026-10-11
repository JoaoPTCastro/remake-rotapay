"""Extrato de conta: disponibilidades independentes e leitura privada."""
import pytest
from tests.test_pagamentos import pagamentos_api, person, note, payment, apply
from tests.test_acertos_fontes_mistas import setup, mixed_body
from tests.test_acertos import draft, execute
from tests.test_creditos import undo
from tests.test_creditos import origin, credit


def totals(c, h, pid, relation='cliente'):
    r = c.get(f'/extratos/{pid}', headers=h['admin'], params={'relacao': relation})
    assert r.status_code == 200, r.text
    return r.json()


def listing(c, h, pid, section, **params):
    r = c.get(f'/extratos/{pid}/{section}', headers=h['admin'], params={'relacao': 'cliente', **params})
    assert r.status_code == 200, r.text
    return r.json()


def test_misto_totais_sem_duplicar_fonte_e_estorno_integral(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, source, _, cr, n, p = setup(c, h)
    a = draft(c, h, mixed_body(pid, cr, n, p))
    assert execute(c, h, a['id']).status_code == 200
    out = totals(c, h, pid)
    t = out['totais_globais']
    assert out['escopo'] == 'dominio_novo'
    assert t['notas']['saldo_aberto'] == 300
    assert t['notas']['saldo_vencido'] == 0
    assert t['pagamentos']['saldo_disponivel'] == 60
    assert t['pagamentos']['destinado_credito'] == 100
    assert t['creditos']['saldo_disponivel'] == 40
    assert t['disponibilidade_total_para_abater'] == 100
    rows = listing(c, h, pid, 'pagamentos')['itens']
    assert {r['id'] for r in rows} == {source['id'], p['id']}
    assert c.post(f"/acertos/{a['id']}/estornar", headers=h['admin'], json=undo()).status_code == 200
    t = totals(c, h, pid)['totais_globais']
    assert t['notas']['saldo_aberto'] == 500
    assert t['pagamentos']['saldo_disponivel'] == 200
    assert t['creditos']['saldo_disponivel'] == 100
    assert t['disponibilidade_total_para_abater'] == 300
    events = listing(c, h, pid, 'timeline')['itens']
    assert any(e['tipo'] == 'acerto_estornado' and e['acerto_id'] == a['id'] for e in events)
    assert sum(e['tipo'] == 'nota_abatimento_estornado' and e['nota_id'] == n['id'] for e in events) == 2
    assert all(e['valor'] is None for e in events if e['tipo'].startswith('acerto_'))


def test_pagamento_direto_relacoes_independentes(pagamentos_api):
    c, h, _ = pagamentos_api
    pid = person(c, h)
    cli, forn = note(c, h, pid), note(c, h, pid, 'fornecedor', 900)
    p = payment(c, h, cliente_id=pid, fornecedor_id=pid)
    assert apply(c, h, p['id'], cli['id'], valor=100).status_code == 201
    assert apply(c, h, p['id'], forn['id'], 'fornecedor', valor=200).status_code == 201
    tc, tf = totals(c, h, pid)['totais_globais'], totals(c, h, pid, 'fornecedor')['totais_globais']
    assert tc['pagamentos']['valor_elegivel'] == tf['pagamentos']['valor_elegivel'] == 300
    assert tc['pagamentos']['saldo_disponivel'] == 200
    assert tf['pagamentos']['saldo_disponivel'] == 100
    assert tc['notas']['saldo_aberto'] == 900 and tf['notas']['saldo_aberto'] == 700


@pytest.mark.parametrize('perfil', ['admin', 'financeiro', 'operador', 'consulta'])
def test_leitura_todos_perfis_sem_acesso_anonimo(pagamentos_api, perfil):
    c, h, _ = pagamentos_api
    pid = person(c, h)
    for suffix in ('', '/notas', '/pagamentos', '/creditos', '/acertos', '/timeline'):
        url = f'/extratos/{pid}{suffix}?relacao=cliente'
        assert c.get(url, headers=h[perfil]).status_code == 200
        assert c.get(url).status_code == 401


def test_filtros_paginados_nao_alteram_totais_globais(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, other = person(c, h), person(c, h)
    note(c, h, other, value=999)
    ids = {note(c, h, pid, value=100)['id'] for _ in range(3)}
    before = totals(c, h, pid)
    rows = []
    for offset in range(3):
        out = listing(c, h, pid, 'notas', status='aberto', limit=1, offset=offset)
        assert out['escopo'] == 'lista_filtrada' and out['total_filtrado'] == 3
        assert out['tem_mais'] == (offset < 2)
        rows += out['itens']
    assert {r['id'] for r in rows} == ids
    assert listing(c, h, pid, 'notas', data_de='2021-01-01')['itens'] == []
    assert totals(c, h, pid) == before
    assert before['totais_globais']['notas']['saldo_aberto'] == 300


@pytest.mark.parametrize('params', [ {'relacao': 'ambos'}, {'relacao': 'cliente', 'limit': 501},
    {'relacao': 'cliente', 'offset': -1}, {'relacao': 'cliente', 'data_de': 'nao-data'},
    {'relacao': 'cliente', 'data_de': '2021-01-01', 'data_ate': '2020-01-01'} ])
def test_validacao_filtros(pagamentos_api, params):
    c, h, _ = pagamentos_api
    pid = person(c, h)
    assert c.get(f'/extratos/{pid}/notas', headers=h['admin'], params=params).status_code == 422
    assert c.get('/extratos/999999?relacao=cliente', headers=h['admin']).status_code == 404


def test_cancelados_revertidos_historico_sem_consumo_ativo(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, p, a = origin(c, h)
    cr = credit(c, h, p, a)
    assert c.post(f"/creditos/{cr['id']}/reverter", headers=h['admin'], json=undo()).status_code == 200
    assert c.post(f"/acertos/{a['id']}/estornar", headers=h['admin'], json=undo()).status_code == 200
    assert c.post(f"/pagamentos/{p['id']}/cancelar", headers=h['admin'], json=undo()).status_code == 200
    notes = listing(c, h, pid, 'notas')['itens']
    assert c.post(f"/notas/{notes[0]['id']}/cancelar", headers=h['admin'], json=undo()).status_code == 200
    t = totals(c, h, pid)['totais_globais']
    assert t['notas']['saldo_aberto'] == t['notas']['valor_original'] == 0
    assert t['pagamentos']['saldo_disponivel'] == t['pagamentos']['valor_elegivel'] == 0
    assert t['creditos']['saldo_disponivel'] == t['creditos']['valor_reconhecido_ativo'] == 0
    assert t['notas']['quantidade_canceladas'] == t['pagamentos']['quantidade_cancelados'] == 1
    assert t['creditos']['quantidade_revertidos'] == t['acertos']['estornado'] == 1
    assert listing(c, h, pid, 'creditos', status='revertido')['itens'][0]['id'] == cr['id']
    types = {e['tipo'] for e in listing(c, h, pid, 'timeline')['itens']}
    assert {'credito_revertido', 'pagamento_cancelado', 'nota_cancelada', 'acerto_estornado'} <= types


def test_vencidos_centavos_e_timeline_paginacao_estavel(pagamentos_api):
    c, h, _ = pagamentos_api
    pid = person(c, h)
    note(c, h, pid, value=0.03)
    r = c.post('/notas', headers=h['admin'], json={'pessoa_id': pid, 'relacao': 'cliente',
        'numero_documento': 'VENCIDO', 'valor_original': 0.07, 'data_emissao': '2020-01-01',
        'descricao': 'Nota vencida', 'modo_vencimento': 'data', 'vencimento': '2020-01-02'})
    assert r.status_code == 201, r.text
    t = totals(c, h, pid)['totais_globais']
    assert t['notas']['saldo_aberto'] == 0.10
    assert t['notas']['saldo_vencido'] == 0.07
    full = listing(c, h, pid, 'timeline')
    pages = [listing(c, h, pid, 'timeline', limit=1, offset=i)['itens'][0] for i in range(full['total_filtrado'])]
    assert [e['id'] for e in pages] == [e['id'] for e in full['itens']]
    assert len({e['id'] for e in pages}) == len(pages)


def test_conta_inativa_historico_privado_sem_mutacao(pagamentos_api):
    from app.models import Pessoa, NotaObrigacao, Pagamento, CreditoConta, Acerto
    c, h, sessions = pagamentos_api
    pid = person(c, h)
    note(c, h, pid, value=100)
    with sessions() as db:
        db.get(Pessoa, pid).ativo = False
        db.commit()
        before = {m.__tablename__: db.query(m).count() for m in (NotaObrigacao, Pagamento, CreditoConta, Acerto)}
    for section in ('notas', 'pagamentos', 'creditos', 'acertos'):
        assert listing(c, h, pid, section)['escopo'] == 'lista_filtrada'
        assert c.get(f'/extratos/{pid}/{section}?relacao=cliente&status=inventado', headers=h['admin']).status_code == 422
    assert totals(c, h, pid)['pessoa']['ativo'] is False
    assert listing(c, h, pid, 'timeline')['total_filtrado'] == 1
    with sessions() as db:
        assert {m.__tablename__: db.query(m).count() for m in (NotaObrigacao, Pagamento, CreditoConta, Acerto)} == before


def test_status_elegivel_filtrado_antes_paginacao(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, forn = person(c, h), person(c, h)
    opened = note(c, h, pid, value=100)
    p = payment(c, h, cliente_id=pid, fornecedor_id=forn, valor=500)
    for _ in range(5):
        n = note(c, h, pid, value=100)
        assert apply(c, h, p['id'], n['id'], valor=100).status_code == 201
    out = listing(c, h, pid, 'notas', status='aberto', limit=1)
    assert out['total_filtrado'] == 1 and out['itens'][0]['id'] == opened['id']
    available = payment(c, h, cliente_id=pid, fornecedor_id=forn, valor=100)
    out = listing(c, h, pid, 'pagamentos', status='disponivel', limit=1)
    assert out['total_filtrado'] == 1 and out['itens'][0]['id'] == available['id']


def test_timeline_periodo_calendario_sao_paulo_e_cache_privado(pagamentos_api):
    from datetime import datetime
    from app.models import NotaObrigacao
    c, h, sessions = pagamentos_api
    pid = person(c, h)
    ids = [note(c, h, pid, value=1)['id'] for _ in range(3)]
    with sessions() as db:
        for nid, dt in zip(ids, (datetime(2020, 1, 2, 2, 59, 59), datetime(2020, 1, 2, 3), datetime(2020, 1, 3, 3))):
            db.get(NotaObrigacao, nid).created_at = dt
        db.commit()
    out = listing(c, h, pid, 'timeline', data_de='2020-01-02', data_ate='2020-01-02')
    assert out['total_filtrado'] == 1 and out['itens'][0]['nota_id'] == ids[1]
    assert out['itens'][0]['data_hora'].endswith('+00:00')
    for section in ('', '/notas', '/pagamentos', '/creditos', '/acertos', '/timeline'):
        r = c.get(f'/extratos/{pid}{section}?relacao=cliente', headers=h['admin'])
        assert 'no-store' in r.headers['cache-control'] and 'private' in r.headers['cache-control']
