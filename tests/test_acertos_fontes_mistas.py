"""Acerto misto: fontes independentes, execução/estorno integrais e migração."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import hashlib
import hmac
import json
from datetime import timedelta
import pytest
from tests.test_pagamentos import pagamentos_api, person, note, payment, apply, balance, detail
from tests.test_acertos import draft, execute, supplier_confirm, payload
from tests.test_creditos import origin, credit, use, fetch, undo
from app.cadastros import hoje


def setup(c, h, relacao='cliente'):
    pid, source, original = origin(c, h, relacao)
    cr = credit(c, h, source, original)
    n = note(c, h, pid, relacao, 500)
    opposite = person(c, h)
    p = payment(c, h, cliente_id=pid if relacao == 'cliente' else opposite,
        fornecedor_id=opposite if relacao == 'cliente' else pid, valor=200)
    return pid, source, original, cr, n, p


def mixed_body(pid, cr, n, p=None, relacao='cliente', **extra):
    items = [{'credito_id': cr['id'], 'nota_id': n['id'], 'valor': 60}]
    if p:
        items.append({'pagamento_id': p['id'], 'nota_id': n['id'], 'valor': 140})
    return {'pessoa_id': pid, 'relacao': relacao, 'data': '2020-01-05',
        'referencia': 'misto-'+uuid4().hex, 'observacao': 'Lote com fontes explícitas', 'itens': items, **extra}


def test_aceite_misto_estorno_integral_fontes_independentes(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, source, _, cr, n, p = setup(c, h)
    body = mixed_body(pid, cr, n, p)
    preview = c.post('/acertos/previa', headers=h['admin'], json=body)
    assert preview.status_code == 200, preview.text
    assert preview.json()['fontes'][0]['saldo_depois'] == 60
    assert preview.json()['creditos'][0]['saldo_depois'] == 40
    a = draft(c, h, body)
    assert execute(c, h, a['id']).status_code == 200
    assert balance(c, h, n['id']) == 300
    assert fetch(c, h, cr['id'])['saldo_disponivel'] == 40
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 60
    assert detail(c, h, source['id'])['orcamentos']['cliente']['saldo_disponivel'] == 0
    d = c.get(f"/acertos/{a['id']}", headers=h['admin']).json()
    assert {i['tipo_fonte'] for i in d['itens']} == {'pagamento', 'credito'}
    assert all(i['aplicacao_id'] for i in d['itens'])
    assert c.post(f"/acertos/{a['id']}/estornar", headers=h['admin'], json=undo()).status_code == 200
    assert balance(c, h, n['id']) == 500
    assert fetch(c, h, cr['id'])['saldo_disponivel'] == 100
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 200
    assert detail(c, h, source['id'])['orcamentos']['cliente']['saldo_disponivel'] == 0


def test_acerto_somente_credito_e_guards_individuais(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, source, orig, cr, n, _ = setup(c, h)
    a = draft(c, h, mixed_body(pid, cr, n))
    assert execute(c, h, a['id']).status_code == 200
    assert balance(c, h, n['id']) == 440
    app = fetch(c, h, cr['id'])['aplicacoes'][0]
    assert app['acerto_id'] == a['id']
    assert c.post(f"/creditos/{cr['id']}/aplicacoes/{app['id']}/estornar", headers=h['admin'], json=undo()).status_code == 422
    assert c.post(f"/notas/{n['id']}/abatimentos/{app['nota_abatimento_id']}/estornar", headers=h['admin'], json=undo()).status_code == 422
    assert c.post(f"/acertos/{orig['id']}/estornar", headers=h['admin'], json=undo()).status_code == 422
    assert c.post(f"/creditos/{cr['id']}/reverter", headers=h['admin'], json=undo()).status_code == 422
    assert detail(c, h, source['id'])['orcamentos']['cliente']['saldo_disponivel'] == 0
    resources = c.get(f"/creditos/recursos-origem?acerto_id={a['id']}", headers=h['admin'])
    assert resources.status_code == 200 and resources.json()['fontes'] == []


def test_fornecedor_credito_misto_exige_lifecycle_e_concordancia(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, source, _, cr, n, p = setup(c, h, 'fornecedor')
    a = draft(c, h, mixed_body(pid, cr, n, p, 'fornecedor'))
    assert execute(c, h, a['id']).status_code == 422
    supplier_confirm(c, h, a['id'])
    assert execute(c, h, a['id']).status_code == 200
    assert balance(c, h, n['id']) == 300
    app = fetch(c, h, cr['id'])['aplicacoes'][0]
    assert app['fornecedor_confirmou'] is True and len(app['referencia_confirmacao']) >= 3
    assert detail(c, h, source['id'])['orcamentos']['cliente']['saldo_disponivel'] == 1100


@pytest.mark.parametrize('variant', ['nenhuma', 'ambas', 'zero', 'nan', 'titular', 'relacao', 'data'])
def test_itens_mistos_invalidos(pagamentos_api, variant):
    c, h, _ = pagamentos_api
    pid, _, _, cr, n, p = setup(c, h)
    body = mixed_body(pid, cr, n, p)
    item = body['itens'][0]
    if variant == 'nenhuma':
        item.pop('credito_id')
    elif variant == 'ambas':
        item['pagamento_id'] = p['id']
    elif variant == 'zero':
        item['valor'] = 0
    elif variant == 'nan':
        item['valor'] = 'NaN'
    elif variant == 'titular':
        body['pessoa_id'] = person(c, h)
    elif variant == 'relacao':
        body['relacao'] = 'fornecedor'
    else:
        body['data'] = (hoje()+timedelta(days=1)).isoformat()
    r = c.post('/acertos/previa', headers=h['admin'], json=body)
    assert r.status_code == 422, r.text


def test_somas_agrupadas_credito_e_nota_e_datas(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, _, _, cr, n, p = setup(c, h)
    other = note(c, h, pid, value=500)
    body = mixed_body(pid, cr, n, p)
    for items in ([{'credito_id': cr['id'], 'nota_id': n['id'], 'valor': 60}, {'credito_id': cr['id'], 'nota_id': other['id'], 'valor': 60}],
                  [{'credito_id': cr['id'], 'nota_id': n['id'], 'valor': 100}, {'pagamento_id': p['id'], 'nota_id': n['id'], 'valor': 401}]):
        assert c.post('/acertos/previa', headers=h['admin'], json={**body, 'itens': items}).status_code == 422
    assert c.post('/acertos/previa', headers=h['admin'], json={**body, 'data': '2020-01-03'}).status_code == 422


@pytest.mark.parametrize('change', ['uso', 'reversao'])
def test_credito_alterado_desde_previa_rejeita_lote_inteiro(pagamentos_api, change):
    c, h, _ = pagamentos_api
    pid, _, _, cr, n, p = setup(c, h)
    body = mixed_body(pid, cr, n, p)
    preview = c.post('/acertos/previa', headers=h['admin'], json=body).json()
    a = draft(c, h, body)
    if change == 'uso':
        other = note(c, h, pid, value=500)
        assert use(c, h, cr, other['id'], valor=1).status_code == 201
    else:
        assert c.post(f"/creditos/{cr['id']}/reverter", headers=h['admin'], json=undo()).status_code == 200
    r = c.post('/acertos', headers=h['admin'], json={**body, 'token_previa': preview['token_previa'], 'chave_idempotencia': uuid4().hex})
    assert r.status_code in (409, 422), r.text
    assert execute(c, h, a['id']).status_code == 409
    assert balance(c, h, n['id']) == 500
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 200


def test_idempotencia_mista_e_resumo_privado(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, _, _, cr, n, p = setup(c, h)
    body = mixed_body(pid, cr, n, p)
    preview = c.post('/acertos/previa', headers=h['admin'], json=body).json()
    full = {**body, 'token_previa': preview['token_previa'], 'chave_idempotencia': uuid4().hex}
    a = c.post('/acertos', headers=h['admin'], json=full)
    b = c.post('/acertos', headers=h['admin'], json=full)
    assert a.status_code == b.status_code == 201 and a.json()['id'] == b.json()['id']
    aid = a.json()['id']
    assert execute(c, h, aid).status_code == 200
    assert execute(c, h, aid).status_code == 200
    assert balance(c, h, n['id']) == 300
    url = f'/acertos/{aid}/relacao'
    assert c.get(url).status_code in (401, 403)
    summary = c.get(url, headers=h['consulta'])
    assert summary.status_code == 200 and len(summary.json()['creditos']) == 1
    assert c.post(f'/acertos/{aid}/estornar', headers=h['consulta'], json=undo()).status_code == 403


def test_concorrencia_misto_vs_uso_manual_credito(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, _, _, cr, n, p = setup(c, h)
    a = draft(c, h, mixed_body(pid, cr, n, p))
    other = note(c, h, pid, value=500)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(execute, c, h, a['id']), pool.submit(use, c, h, cr, other['id'], valor=100)]
        results = [f.result() for f in futures]
    assert sorted(r.status_code for r in results) in ([200, 409], [200, 422], [201, 409]), [r.text for r in results]
    state = c.get(f"/acertos/{a['id']}", headers=h['admin']).json()['status']
    if state == 'efetivado':
        assert balance(c, h, n['id']) == 300 and balance(c, h, other['id']) == 500
    else:
        assert balance(c, h, n['id']) == 500 and balance(c, h, other['id']) == 400
    assert fetch(c, h, cr['id'])['saldo_disponivel'] in (0, 40)


def test_concorrencia_misto_vs_aplicacao_pagamento(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, _, _, cr, n, p = setup(c, h)
    a = draft(c, h, mixed_body(pid, cr, n, p))
    other = note(c, h, pid, value=500)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(execute, c, h, a['id']), pool.submit(apply, c, h, p['id'], other['id'], valor=200)]
        results = [f.result() for f in futures]
    assert sorted(r.status_code for r in results) in ([200, 409], [200, 422], [201, 409]), [r.text for r in results]
    state = c.get(f"/acertos/{a['id']}", headers=h['admin']).json()['status']
    if state == 'efetivado':
        assert balance(c, h, n['id']) == 300 and balance(c, h, other['id']) == 500
    else:
        assert balance(c, h, n['id']) == 500 and balance(c, h, other['id']) == 300
        assert fetch(c, h, cr['id'])['saldo_disponivel'] == 100


def test_token_pagamento_antigo_continua_compativel(pagamentos_api):
    from app.config import SECRET_KEY
    c, h, _ = pagamentos_api
    pid, forn = person(c, h), person(c, h)
    n = note(c, h, pid, value=500)
    p = payment(c, h, cliente_id=pid, fornecedor_id=forn, valor=200)
    body = payload(pid, [(p['id'], n['id'], 100)])
    preview = c.post('/acertos/previa', headers=h['admin'], json=body)
    assert preview.status_code == 200, preview.text
    data = preview.json()
    legacy_body = {**body, 'itens': [{'pagamento_id': p['id'], 'nota_id': n['id'], 'valor': '100'}]}
    snapshot = {'fontes': data['fontes'], 'notas': data['notas']}
    old_token = hmac.new(SECRET_KEY.encode(), json.dumps({'proposta': legacy_body, 'snapshot': snapshot},
        sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode(), hashlib.sha256).hexdigest()
    r = c.post('/acertos', headers=h['admin'], json={**body, 'token_previa': old_token, 'chave_idempotencia': uuid4().hex})
    assert r.status_code == 201, r.text
    assert execute(c, h, r.json()['id']).status_code == 200
    assert balance(c, h, n['id']) == 400


def test_creditos_recursos_filtrados_antes_pagina(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, p, original = origin(c, h)
    available = credit(c, h, p, original, valor=40)
    used = credit(c, h, p, original, valor=60)
    n = note(c, h, pid, value=500)
    assert use(c, h, used, n['id'], valor=60).status_code == 201
    r = c.get(f'/acertos/recursos?pessoa_id={pid}&relacao=cliente&limit=1', headers=h['admin'])
    assert r.status_code == 200, r.text
    assert [cr['id'] for cr in r.json()['creditos']] == [available['id']]
    assert r.json()['creditos_tem_mais'] is False


def test_migracao_old_notnull_preserva_itens_e_token_duas_vezes(pagamentos_api, monkeypatch):
    from sqlalchemy import inspect, text
    import app.database as database
    c, h, sessions = pagamentos_api
    pid, forn = person(c, h), person(c, h)
    n = note(c, h, pid, value=500)
    p = payment(c, h, cliente_id=pid, fornecedor_id=forn, valor=200)
    a = draft(c, h, payload(pid, [(p['id'], n['id'], 100)]))
    cols = 'id,acerto_id,pagamento_id,nota_id,valor,pagamento_version,nota_version,saldo_pagamento_snapshot,saldo_nota_snapshot'
    with sessions() as db:
        engine = db.get_bind()
        before = db.execute(text(f'SELECT {cols} FROM acerto_itens')).all()
    with engine.begin() as conn:
        conn.execute(text('''CREATE TABLE acerto_itens_old (
          id INTEGER PRIMARY KEY, acerto_id INTEGER NOT NULL,
          pagamento_id INTEGER NOT NULL, nota_id INTEGER NOT NULL, valor NUMERIC(12,2) NOT NULL,
          pagamento_version INTEGER NOT NULL, nota_version INTEGER NOT NULL,
          saldo_pagamento_snapshot NUMERIC(12,2) NOT NULL, saldo_nota_snapshot NUMERIC(12,2) NOT NULL,
          CONSTRAINT uq_acerto_par UNIQUE (acerto_id,pagamento_id,nota_id),
          FOREIGN KEY(acerto_id) REFERENCES acertos(id), FOREIGN KEY(pagamento_id) REFERENCES pagamentos(id),
          FOREIGN KEY(nota_id) REFERENCES notas_obrigacoes(id))'''))
        conn.execute(text(f'INSERT INTO acerto_itens_old ({cols}) SELECT {cols} FROM acerto_itens'))
        conn.execute(text('DROP TABLE acerto_itens'))
        conn.execute(text('ALTER TABLE acerto_itens_old RENAME TO acerto_itens'))
    monkeypatch.setattr(database, 'engine', engine)
    monkeypatch.setattr(database, 'SessionLocal', sessions)
    database.init_db()
    database.init_db()
    with engine.connect() as conn:
        columns = {col['name']: col for col in inspect(conn).get_columns('acerto_itens')}
        assert columns['pagamento_id']['nullable'] is True and 'credito_id' in columns
        assert conn.execute(text(f'SELECT {cols} FROM acerto_itens')).all() == before
        assert conn.execute(text('SELECT credito_id FROM acerto_itens')).scalar() is None
    assert execute(c, h, a['id']).status_code == 200
    assert balance(c, h, n['id']) == 400


def test_valor_decimal_string_equivalente_efetiva(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, forn = person(c, h), person(c, h)
    n = note(c, h, pid, value=500)
    p = payment(c, h, cliente_id=pid, fornecedor_id=forn, valor=200)
    body = payload(pid, [(p['id'], n['id'], '100.00')])
    a = draft(c, h, body)
    r = execute(c, h, a['id'])
    assert r.status_code == 200, r.text


def test_concorrencia_misto_vs_outro_pagamento_mesma_nota(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, _, _, cr, n, p = setup(c, h)
    other = payment(c, h, cliente_id=pid, fornecedor_id=person(c, h), valor=500)
    a = draft(c, h, mixed_body(pid, cr, n, p))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(execute, c, h, a['id']), pool.submit(apply, c, h, other['id'], n['id'], valor=500)]
        results = [f.result() for f in futures]
    assert sorted(r.status_code for r in results) in ([200, 409], [200, 422], [201, 409]), [r.text for r in results]
    assert balance(c, h, n['id']) in (0, 300)
    if balance(c, h, n['id']) == 0:
        assert fetch(c, h, cr['id'])['saldo_disponivel'] == 100
        assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 200
