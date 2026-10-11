"""Sobra reconhecida explicitamente, sem duplicar dinheiro nem voltar à fonte no uso."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from datetime import timedelta
import pytest
from tests.test_pagamentos import pagamentos_api, person, note, payment, apply, balance, detail
from tests.test_acertos import payload, draft, execute, supplier_confirm
from app.cadastros import hoje


def origin(c, h, relacao='cliente', original=1100, applied=1000):
    cli, forn = person(c, h), person(c, h)
    pid = cli if relacao == 'cliente' else forn
    n = note(c, h, pid, relacao, applied)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=original)
    a = draft(c, h, payload(pid, [(p['id'], n['id'], applied)], relacao=relacao))
    if relacao == 'fornecedor':
        supplier_confirm(c, h, a['id'])
    assert execute(c, h, a['id']).status_code == 200
    return pid, p, a


def credit_payload(p, a, **extra):
    return {'acerto_id': a['id'], 'pagamento_id': p['id'], 'valor': 100, 'data': '2020-01-04',
        'referencia': 'credito-'+uuid4().hex, 'observacao': 'Sobra reconhecida expressamente',
        'chave_idempotencia': uuid4().hex, 'confirmacao': True,
        **({'fornecedor_confirmou': True, 'referencia_confirmacao': 'Fornecedor autorizou crédito'} if a['relacao'] == 'fornecedor' else {}), **extra}


def credit(c, h, p, a, **extra):
    r = c.post('/creditos', headers=h['admin'], json=credit_payload(p, a, **extra))
    assert r.status_code == 201, r.text
    return r.json()


def fetch(c, h, cid):
    r = c.get(f'/creditos/{cid}', headers=h['admin'])
    assert r.status_code == 200, r.text
    return r.json()


def use(c, h, cr, nid, **extra):
    return c.post(f"/creditos/{cr['id']}/aplicacoes", headers=h['admin'], json={'nota_id': nid,
        'valor': 60, 'data': '2020-01-05', 'referencia': 'uso-'+uuid4().hex,
        'observacao': 'Aplicação explícita do crédito', 'chave_idempotencia': uuid4().hex,
        **({'fornecedor_confirmou': True, 'referencia_confirmacao': 'Fornecedor autorizou uso'} if cr['relacao'] == 'fornecedor' else {}), **extra})


def undo():
    return {'senha': 'senha-teste', 'motivo': 'Correção expressamente documentada'}


def test_ciclo_aceite_sem_devolver_fonte_no_uso(pagamentos_api):
    c, h, sessions = pagamentos_api
    pid, p, a = origin(c, h)
    cr = credit(c, h, p, a)
    assert cr['valor_original'] == cr['saldo_disponivel'] == 100
    pg = detail(c, h, p['id'])
    assert pg['orcamentos']['cliente']['saldo_disponivel'] == 0
    assert pg['orcamentos']['cliente']['destinado_credito'] == 100
    assert pg['orcamentos']['fornecedor']['saldo_disponivel'] == 1100
    n = note(c, h, pid, value=500)
    u = use(c, h, cr, n['id'])
    assert u.status_code == 201, u.text
    assert balance(c, h, n['id']) == 440 and fetch(c, h, cr['id'])['saldo_disponivel'] == 40
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 0
    url = f"/creditos/{cr['id']}/aplicacoes/{u.json()['id']}/estornar"
    assert c.post(url, headers=h['admin'], json=undo()).status_code == 200
    assert balance(c, h, n['id']) == 500 and fetch(c, h, cr['id'])['saldo_disponivel'] == 100
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 0
    assert c.post(f"/creditos/{cr['id']}/reverter", headers=h['admin'], json=undo()).status_code == 200
    assert fetch(c, h, cr['id'])['status'] == 'revertido'
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 100
    from app.models import Movimentacao, Lancamento, Conciliacao
    with sessions() as db:
        assert all(db.query(model).count() == 0 for model in (Movimentacao, Lancamento, Conciliacao))


def test_origem_recursos_nao_consume_credito_reconhecido(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, p, a = origin(c, h)
    url = f"/creditos/recursos-origem?acerto_id={a['id']}"
    before = c.get(url, headers=h['admin'])
    assert before.status_code == 200, before.text
    assert before.json()['fontes'][0]['maximo_reconhecivel'] == 100
    credit(c, h, p, a)
    after = c.get(url, headers=h['admin'])
    assert after.json()['fontes'] == []
    resources = c.get(f'/acertos/recursos?pessoa_id={pid}&relacao=cliente&limit=1', headers=h['admin']).json()
    assert resources['pagamentos'] == []


def test_limites_sobra_snapshot_e_saldo_corrente(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, p, a = origin(c, h)
    cr = credit(c, h, p, a, valor=60)
    assert c.post('/creditos', headers=h['admin'], json=credit_payload(p, a, valor=41)).status_code == 422
    n = note(c, h, pid, value=500)
    assert apply(c, h, p['id'], n['id'], valor=20).status_code == 201
    assert c.post('/creditos', headers=h['admin'], json=credit_payload(p, a, valor=21)).status_code == 422
    assert c.post('/creditos', headers=h['admin'], json=credit_payload(p, a, valor=20)).status_code == 201
    assert fetch(c, h, cr['id'])['saldo_disponivel'] == 60


def test_guard_estorno_origem_pagamento_e_nota_inclusive_usado(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, p, a = origin(c, h)
    cr = credit(c, h, p, a)
    n = note(c, h, pid, value=100)
    u = use(c, h, cr, n['id'], valor=100)
    assert u.status_code == 201
    assert fetch(c, h, cr['id'])['status'] == 'utilizado'
    for url in (f"/acertos/{a['id']}/estornar", f"/pagamentos/{p['id']}/cancelar",
                f"/notas/{n['id']}/abatimentos/{u.json()['nota_abatimento_id']}/estornar",
                f"/creditos/{cr['id']}/reverter"):
        assert c.post(url, headers=h['admin'], json=undo()).status_code in (409, 422)
    assert balance(c, h, n['id']) == 0
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 0


def test_fornecedor_exige_prova_no_reconhecimento_e_uso(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, p, a = origin(c, h, 'fornecedor')
    for extra in ({'fornecedor_confirmou': False}, {'referencia_confirmacao': None}, {'referencia_confirmacao': '  '}):
        assert c.post('/creditos', headers=h['admin'], json=credit_payload(p, a, **extra)).status_code == 422
    cr = credit(c, h, p, a)
    n = note(c, h, pid, 'fornecedor', 500)
    for extra in ({'fornecedor_confirmou': False}, {'referencia_confirmacao': None}, {'referencia_confirmacao': '  '}):
        assert use(c, h, cr, n['id'], **extra).status_code == 422
    assert use(c, h, cr, n['id']).status_code == 201
    assert balance(c, h, n['id']) == 440
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 1100


def test_idempotencia_reconhecimento_uso_estorno_reversao(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, p, a = origin(c, h)
    body = credit_payload(p, a)
    first = c.post('/creditos', headers=h['admin'], json=body)
    second = c.post('/creditos', headers=h['admin'], json=body)
    assert first.status_code == second.status_code == 201 and first.json()['id'] == second.json()['id']
    cr = first.json()
    assert c.post('/creditos', headers=h['admin'], json={**body, 'valor': 99}).status_code == 409
    n = note(c, h, pid, value=500)
    key, ref = uuid4().hex, 'uso-idempotente'
    first = use(c, h, cr, n['id'], chave_idempotencia=key, referencia=ref)
    second = use(c, h, cr, n['id'], chave_idempotencia=key, referencia=ref)
    assert first.status_code == second.status_code == 201 and first.json()['id'] == second.json()['id']
    assert use(c, h, cr, n['id'], chave_idempotencia=key, referencia=ref, valor=50).status_code == 409
    url = f"/creditos/{cr['id']}/aplicacoes/{first.json()['id']}/estornar"
    for _ in range(2):
        assert c.post(url, headers=h['admin'], json=undo()).status_code == 200
    for _ in range(2):
        assert c.post(f"/creditos/{cr['id']}/reverter", headers=h['admin'], json=undo()).status_code == 200
    assert balance(c, h, n['id']) == 500
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 100


@pytest.mark.parametrize('value', [0, -1, 1.001, 'NaN', 'Infinity'])
def test_dinheiro_invalido(pagamentos_api, value):
    c, h, _ = pagamentos_api
    _, p, a = origin(c, h)
    assert c.post('/creditos', headers=h['admin'], json=credit_payload(p, a, valor=value)).status_code == 422


def test_datas_titular_relacao_e_limites_uso(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, p, a = origin(c, h)
    for date in ('2020-01-02', (hoje()+timedelta(days=1)).isoformat()):
        assert c.post('/creditos', headers=h['admin'], json=credit_payload(p, a, data=date)).status_code == 422
    cr = credit(c, h, p, a)
    n = note(c, h, pid, value=50)
    stranger = note(c, h, person(c, h))
    wrong_relation = note(c, h, pid, 'fornecedor')
    for nid, extras in ((n['id'], {'valor': 51}), (stranger['id'], {}), (wrong_relation['id'], {}),
                        (n['id'], {'data': '2020-01-03'}), (n['id'], {'data': (hoje()+timedelta(days=1)).isoformat()})):
        assert use(c, h, cr, nid, **extras).status_code == 422
    assert balance(c, h, n['id']) == 50


def test_permissoes_reversao_senha_motivo(pagamentos_api):
    c, h, _ = pagamentos_api
    _, p, a = origin(c, h)
    cr = credit(c, h, p, a)
    for role in ('consulta', 'operador'):
        assert c.get('/creditos', headers=h[role]).status_code == 200
        assert c.get(f"/creditos/{cr['id']}", headers=h[role]).status_code == 200
        assert c.post('/creditos', headers=h[role], json=credit_payload(p, a)).status_code == 403
        assert c.post(f"/creditos/{cr['id']}/reverter", headers=h[role], json=undo()).status_code == 403
    assert c.get('/creditos').status_code in (401, 403)
    url = f"/creditos/{cr['id']}/reverter"
    assert c.post(url, headers=h['admin'], json={**undo(), 'senha': 'errada'}).status_code == 403
    assert c.post(url, headers=h['admin'], json={**undo(), 'motivo': '  '}).status_code == 422
    assert fetch(c, h, cr['id'])['saldo_disponivel'] == 100


def test_concorrencia_reconhecimento_mesma_sobra(pagamentos_api):
    c, h, _ = pagamentos_api
    _, p, a = origin(c, h)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: c.post('/creditos', headers=h['admin'], json=credit_payload(p, a)), range(2)))
    assert sorted(r.status_code for r in responses) in ([201, 409], [201, 422]), [r.text for r in responses]
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 0
    assert len(c.get('/creditos', headers=h['admin']).json()) == 1


def test_concorrencia_uso_credito_em_duas_notas(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, p, a = origin(c, h)
    cr = credit(c, h, p, a)
    notes = [note(c, h, pid, value=100) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda n: use(c, h, cr, n['id'], valor=100), notes))
    assert sorted(r.status_code for r in responses) in ([201, 409], [201, 422]), [r.text for r in responses]
    assert sum(100-balance(c, h, n['id']) for n in notes) == 100
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 0


def test_concorrencia_reconhecimento_vs_aplicacao_fonte(pagamentos_api):
    from threading import Barrier
    c, h, _ = pagamentos_api
    pid, p, a = origin(c, h)
    n = note(c, h, pid, value=500)
    gate = Barrier(2)
    def reconhecer():
        gate.wait()
        return c.post('/creditos', headers=h['admin'], json=credit_payload(p, a))
    def aplicar():
        gate.wait()
        return apply(c, h, p['id'], n['id'], valor=100)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = [f.result() for f in (pool.submit(reconhecer), pool.submit(aplicar))]
    assert sorted(r.status_code for r in responses) in ([201, 409], [201, 422]), [r.text for r in responses]
    credits = c.get('/creditos', headers=h['admin']).json()
    assert (len(credits), balance(c, h, n['id'])) in ((1, 500), (0, 400))
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 0


def test_concorrencia_reconhecimento_vs_estorno_acerto(pagamentos_api):
    from threading import Barrier
    c, h, _ = pagamentos_api
    _, p, a = origin(c, h)
    gate = Barrier(2)
    def reconhecer():
        gate.wait()
        return c.post('/creditos', headers=h['admin'], json=credit_payload(p, a))
    def estornar():
        gate.wait()
        return c.post(f"/acertos/{a['id']}/estornar", headers=h['admin'], json=undo())
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = [f.result() for f in (pool.submit(reconhecer), pool.submit(estornar))]
    codes = sorted(r.status_code for r in responses)
    assert codes in ([200, 409], [200, 422], [201, 409], [201, 422]), [r.text for r in responses]
    credits = c.get('/creditos', headers=h['admin']).json()
    state = c.get(f"/acertos/{a['id']}", headers=h['admin']).json()['status']
    assert (len(credits), state) in ((1, 'efetivado'), (0, 'estornado'))


def test_concorrencia_uso_credito_vs_pagamento_mesma_nota(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, p, a = origin(c, h)
    cr = credit(c, h, p, a)
    n = note(c, h, pid, value=100)
    other = payment(c, h, cliente_id=pid, fornecedor_id=person(c, h), valor=100)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(use, c, h, cr, n['id'], valor=100), pool.submit(apply, c, h, other['id'], n['id'], valor=100)]
        responses = [f.result() for f in futures]
    assert sorted(r.status_code for r in responses) in ([201, 409], [201, 422]), [r.text for r in responses]
    assert balance(c, h, n['id']) == 0
    assert fetch(c, h, cr['id'])['saldo_disponivel'] + detail(c, h, other['id'])['orcamentos']['cliente']['saldo_disponivel'] == 100


def test_refs_documentais_bloqueiam_credito_nos_dois_sentidos(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, p, a = origin(c, h)
    n = note(c, h, pid, value=500)
    doc = {'valor': 10, 'data': '2020-01-04', 'referencia': 'DOC-ÁBC', 'observacao': 'Já documentado', 'chave_idempotencia': uuid4().hex}
    assert c.post(f"/notas/{n['id']}/abatimentos", headers=h['admin'], json=doc).status_code == 201
    assert c.post('/creditos', headers=h['admin'], json=credit_payload(p, a, referencia='doc-ábc')).status_code == 409
    cr = credit(c, h, p, a, referencia='CRÉDITO-ÁBC')
    assert c.post(f"/notas/{n['id']}/abatimentos", headers=h['admin'], json={**doc, 'referencia': 'crédito-ábc', 'chave_idempotencia': uuid4().hex}).status_code == 409
    assert use(c, h, cr, n['id'], referencia='doc-ábc').status_code == 409
    assert balance(c, h, n['id']) == 490


def test_migracao_notaab_creditofk_preserva_registros(pagamentos_api, monkeypatch):
    from sqlalchemy import inspect, text
    import app.database as database
    c, h, sessions = pagamentos_api
    _, p, a = origin(c, h)
    with sessions() as db:
        engine = db.get_bind()
        old = db.execute(text('SELECT id,nota_id,valor,origem,pagamento_aplicacao_id,estornado FROM nota_abatimentos')).all()
    with engine.begin() as conn:
        names = ','.join(col['name'] for col in inspect(conn).get_columns('nota_abatimentos') if col['name'] != 'credito_aplicacao_id')
        conn.execute(text(f'CREATE TABLE nota_ab_antigos AS SELECT {names} FROM nota_abatimentos'))
        conn.execute(text('DROP TABLE nota_abatimentos'))
        conn.execute(text('ALTER TABLE nota_ab_antigos RENAME TO nota_abatimentos'))
    monkeypatch.setattr(database, 'engine', engine)
    monkeypatch.setattr(database, 'SessionLocal', sessions)
    database.init_db()
    database.init_db()
    with engine.connect() as conn:
        assert 'credito_aplicacao_id' in {col['name'] for col in inspect(conn).get_columns('nota_abatimentos')}
        assert conn.execute(text('SELECT id,nota_id,valor,origem,pagamento_aplicacao_id,estornado FROM nota_abatimentos')).all() == old
        assert conn.execute(text('SELECT COUNT(*) FROM creditos_conta')).scalar() == 0
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 100
