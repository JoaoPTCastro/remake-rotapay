"""Acertos atômicos: múltiplas fontes/notas, conferência e sem consumo legado."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from tests.test_pagamentos import pagamentos_api, person, note, payment, apply, balance, detail


def payload(pid, items, **extra):
    return {'pessoa_id': pid, 'relacao': 'cliente', 'data': '2020-01-03',
        'referencia': 'acerto-' + uuid4().hex, 'observacao': 'Acerto conferido na loja',
        'itens': [{'pagamento_id': p, 'nota_id': n, 'valor': v} for p, n, v in items], **extra}


def draft(c, h, body, key=None):
    preview = c.post('/acertos/previa', headers=h['admin'], json=body)
    assert preview.status_code == 200, preview.text
    r = c.post('/acertos', headers=h['admin'], json={**body, 'token_previa': preview.json()['token_previa'],
        'chave_idempotencia': key or uuid4().hex})
    assert r.status_code == 201, r.text
    return r.json()


def fetch(c, h, aid):
    r = c.get(f'/acertos/{aid}', headers=h['admin'])
    assert r.status_code == 200, r.text
    return r.json()


def execute(c, h, aid):
    return c.post(f'/acertos/{aid}/efetivar', headers=h['admin'], json={'confirmacao': True})


def supplier_confirm(c, h, aid):
    r = c.post(f'/acertos/{aid}/enviar', headers=h['admin'], json={'referencia_envio': 'Mensagem externa 123',
        'observacao_envio': 'Relação entregue ao fornecedor'})
    assert r.status_code == 200, r.text
    r = c.post(f'/acertos/{aid}/confirmar', headers=h['admin'], json={'referencia_confirmacao': 'Resposta externa 456',
        'observacao_confirmacao': 'Fornecedor conferiu e concordou'})
    assert r.status_code == 200, r.text


def setup_pair(c, h, note_value=1000, payment_value=300):
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, cli, value=note_value)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=payment_value)
    return cli, forn, n, p


def test_multiplos_pares_previa_sem_reserva_e_efetivacao(pagamentos_api):
    c, h, sessions = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n1, n2 = note(c, h, cli, value=1000), note(c, h, cli, value=500)
    p1, p2 = payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=500), payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=400)
    body = payload(cli, [(p1['id'], n1['id'], 300), (p1['id'], n2['id'], 200), (p2['id'], n2['id'], 100)])
    preview = c.post('/acertos/previa', headers=h['admin'], json=body)
    assert preview.status_code == 200, preview.text
    d = preview.json()
    assert d['total_aplicar'] == 600 and d['sem_reserva'] is True
    assert sum(f['saldo_depois'] for f in d['fontes']) == 300
    assert sum(n['saldo_depois'] for n in d['notas']) == 900
    a = draft(c, h, body)
    assert a['status'] == 'rascunho'
    assert balance(c, h, n1['id']) == 1000 and balance(c, h, n2['id']) == 500
    assert execute(c, h, a['id']).status_code == 200
    assert balance(c, h, n1['id']) == 700 and balance(c, h, n2['id']) == 200
    d = fetch(c, h, a['id'])
    assert d['status'] == 'efetivado' and len(d['itens']) == 3
    assert all(item['aplicacao_id'] for item in d['itens'])
    assert detail(c, h, p1['id'])['orcamentos']['fornecedor']['saldo_disponivel'] == 500
    assert detail(c, h, p2['id'])['orcamentos']['cliente']['saldo_disponivel'] == 300
    from app.models import Movimentacao, Lancamento, Conciliacao
    with sessions() as db:
        assert all(db.query(m).count() == 0 for m in (Movimentacao, Lancamento, Conciliacao))


def test_fornecedor_lifecycle_exige_evidencias_e_preserva_cliente(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, forn, 'fornecedor', 900)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    a = draft(c, h, payload(forn, [(p['id'], n['id'], 300)], relacao='fornecedor'))
    assert execute(c, h, a['id']).status_code in (409, 422)
    confirm = {'referencia_confirmacao': 'Resposta 456', 'observacao_confirmacao': 'Concordância documentada'}
    assert c.post(f"/acertos/{a['id']}/confirmar", headers=h['admin'], json=confirm).status_code in (409, 422)
    assert c.post(f"/acertos/{a['id']}/enviar", headers=h['admin'], json={'referencia_envio': '   ', 'observacao_envio': 'Teste'}).status_code == 422
    sent = {'referencia_envio': 'Mensagem 123', 'observacao_envio': 'Enviado por canal externo'}
    assert c.post(f"/acertos/{a['id']}/enviar", headers=h['admin'], json=sent).status_code == 200
    assert execute(c, h, a['id']).status_code in (409, 422)
    assert c.post(f"/acertos/{a['id']}/confirmar", headers=h['admin'], json=confirm).status_code == 200
    assert execute(c, h, a['id']).status_code == 200
    assert balance(c, h, n['id']) == 600
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 300
    d = fetch(c, h, a['id'])
    assert d['referencia_envio'] == sent['referencia_envio']
    assert d['referencia_confirmacao'] == confirm['referencia_confirmacao']


def test_stale_previa_nao_cria_e_stale_rascunho_rejeita_integral(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn, n, p = setup_pair(c, h)
    other = note(c, h, cli)
    body = payload(cli, [(p['id'], n['id'], 100), (p['id'], other['id'], 100)])
    preview = c.post('/acertos/previa', headers=h['admin'], json=body).json()
    a = draft(c, h, body)
    assert apply(c, h, p['id'], n['id'], valor=50).status_code == 201
    r = c.post('/acertos', headers=h['admin'], json={**body, 'token_previa': preview['token_previa'], 'chave_idempotencia': uuid4().hex})
    assert r.status_code == 409, r.text
    assert execute(c, h, a['id']).status_code == 409
    assert balance(c, h, n['id']) == 950 and balance(c, h, other['id']) == 1000
    assert fetch(c, h, a['id'])['status'] == 'rascunho'
    assert len(detail(c, h, p['id'])['aplicacoes']) == 1


def test_limites_agrupados_por_nota_e_pagamento(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn, n, p = setup_pair(c, h, note_value=100, payment_value=100)
    n2 = note(c, h, cli)
    p2 = payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=100)
    for items in ([(p['id'], n['id'], 60), (p['id'], n2['id'], 60)],
                  [(p['id'], n['id'], 60), (p2['id'], n['id'], 60)]):
        r = c.post('/acertos/previa', headers=h['admin'], json=payload(cli, items))
        assert r.status_code == 422, r.text
    assert balance(c, h, n['id']) == 100


def test_titular_relacao_pares_e_valores_invalidos(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn, n, p = setup_pair(c, h)
    alien = note(c, h, person(c, h))
    base = payload(cli, [(p['id'], n['id'], 100)])
    for extra in ({'pessoa_id': forn}, {'relacao': 'fornecedor'}, {'itens': []},
                  {'itens': [base['itens'][0], base['itens'][0]]},
                  {'itens': [{'pagamento_id': p['id'], 'nota_id': alien['id'], 'valor': 100}]},
                  {'itens': [{'pagamento_id': p['id'], 'nota_id': n['id'], 'valor': 0}]},
                  {'itens': [{'pagamento_id': p['id'], 'nota_id': n['id'], 'valor': 'NaN'}]}):
        r = c.post('/acertos/previa', headers=h['admin'], json={**base, **extra})
        assert r.status_code == 422, r.text


def test_estorno_integral_so_acerto_preserva_outro_lado(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn, n, p = setup_pair(c, h)
    n2 = note(c, h, cli)
    comp = note(c, h, forn, 'fornecedor')
    assert apply(c, h, p['id'], comp['id'], 'fornecedor', valor=100).status_code == 201
    a = draft(c, h, payload(cli, [(p['id'], n['id'], 100), (p['id'], n2['id'], 100)]))
    assert execute(c, h, a['id']).status_code == 200
    d = fetch(c, h, a['id'])
    application_id = d['itens'][0]['aplicacao_id']
    undo = {'senha': 'senha-teste', 'motivo': 'Correção integral do acerto'}
    assert c.post(f"/pagamentos/{p['id']}/aplicacoes/{application_id}/estornar", headers=h['admin'], json=undo).status_code in (409, 422)
    assert c.post(f"/acertos/{a['id']}/estornar", headers=h['admin'], json={**undo, 'senha': 'errada'}).status_code == 403
    assert balance(c, h, n['id']) == 900 and balance(c, h, n2['id']) == 900
    r = c.post(f"/acertos/{a['id']}/estornar", headers=h['admin'], json=undo)
    assert r.status_code == 200, r.text
    assert balance(c, h, n['id']) == balance(c, h, n2['id']) == 1000
    assert balance(c, h, comp['id']) == 900
    d = detail(c, h, p['id'])
    assert d['orcamentos']['cliente']['saldo_disponivel'] == 300
    assert d['orcamentos']['fornecedor']['saldo_disponivel'] == 200
    assert fetch(c, h, a['id'])['status'] == 'estornado'
    assert c.post(f"/acertos/{a['id']}/estornar", headers=h['admin'], json=undo).status_code == 200


def test_idempotencia_criacao_efetivacao_e_itens_imutaveis(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, _, n, p = setup_pair(c, h)
    body = payload(cli, [(p['id'], n['id'], 100)])
    preview = c.post('/acertos/previa', headers=h['admin'], json=body).json()
    full = {**body, 'token_previa': preview['token_previa'], 'chave_idempotencia': uuid4().hex}
    a = c.post('/acertos', headers=h['admin'], json=full)
    b = c.post('/acertos', headers=h['admin'], json=full)
    assert a.status_code == b.status_code == 201 and a.json()['id'] == b.json()['id']
    aid = a.json()['id']
    assert c.post('/acertos', headers=h['admin'], json={**full, 'observacao': 'Payload diferente'}).status_code == 409
    assert execute(c, h, aid).status_code == 200
    assert execute(c, h, aid).status_code == 200
    assert balance(c, h, n['id']) == 900
    assert len(detail(c, h, p['id'])['aplicacoes']) == 1
    assert c.patch(f'/acertos/{aid}', headers=h['admin'], json={'itens': []}).status_code == 405


def test_cancelamento_rascunho_e_permissoes_resumo(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, _, n, p = setup_pair(c, h)
    body = payload(cli, [(p['id'], n['id'], 100)])
    a = draft(c, h, body)
    for role in ('consulta', 'operador'):
        assert c.get('/acertos', headers=h[role]).status_code == 200
        assert c.get(f"/acertos/{a['id']}/relacao", headers=h[role]).status_code == 200
        assert c.post('/acertos/previa', headers=h[role], json=body).status_code == 403
        assert c.post(f"/acertos/{a['id']}/efetivar", headers=h[role], json={'confirmacao': True}).status_code == 403
    assert c.get(f"/acertos/{a['id']}/relacao").status_code in (401, 403)
    r = c.post(f"/acertos/{a['id']}/cancelar", headers=h['admin'], json={'senha': 'senha-teste', 'motivo': 'Rascunho descartado'})
    assert r.status_code == 200, r.text
    assert fetch(c, h, a['id'])['status'] == 'cancelado'
    assert balance(c, h, n['id']) == 1000
    assert execute(c, h, a['id']).status_code in (409, 422)


def test_concorrencia_efetivacao_mesmo_orcamento(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, _, n, p = setup_pair(c, h, payment_value=100)
    n2 = note(c, h, cli)
    a = draft(c, h, payload(cli, [(p['id'], n['id'], 100)]))
    b = draft(c, h, payload(cli, [(p['id'], n2['id'], 100)]))
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda x: execute(c, h, x['id']), (a, b)))
    assert sorted(r.status_code for r in responses) == [200, 409], [r.text for r in responses]
    assert sum(1000-balance(c, h, x['id']) for x in (n, n2)) == 100


def test_sobra_disponivel_sem_credito_novo(pagamentos_api):
    c, h, sessions = pagamentos_api
    cli, _, n, p = setup_pair(c, h, note_value=100, payment_value=300)
    a = draft(c, h, payload(cli, [(p['id'], n['id'], 100)]))
    assert execute(c, h, a['id']).status_code == 200
    assert balance(c, h, n['id']) == 0
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 200
    from app.models import Lancamento
    with sessions() as db:
        assert db.query(Lancamento).count() == 0


def test_token_previa_nao_aceita_payload_adulterado(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, _, n, p = setup_pair(c, h)
    other = note(c, h, cli)
    body = payload(cli, [(p['id'], n['id'], 100)])
    preview = c.post('/acertos/previa', headers=h['admin'], json=body)
    assert preview.status_code == 200
    for items in ([{'pagamento_id': p['id'], 'nota_id': n['id'], 'valor': 90}],
                  [{'pagamento_id': p['id'], 'nota_id': other['id'], 'valor': 100}]):
        r = c.post('/acertos', headers=h['admin'], json={**body, 'itens': items,
            'token_previa': preview.json()['token_previa'], 'chave_idempotencia': uuid4().hex})
        assert r.status_code == 409, r.text
    assert c.get('/acertos', headers=h['admin']).json() == []
    assert balance(c, h, n['id']) == 1000


def test_datas_e_titular_inativo_na_previa(pagamentos_api):
    from app.cadastros import hoje
    from datetime import timedelta
    c, h, _ = pagamentos_api
    cli, _, n, p = setup_pair(c, h)
    body = payload(cli, [(p['id'], n['id'], 100)])
    for data in ('2019-12-31', '2020-01-02', (hoje()+timedelta(days=1)).isoformat()):
        r = c.post('/acertos/previa', headers=h['admin'], json={**body, 'data': data})
        assert r.status_code == 422, r.text
    assert c.patch(f'/pessoas/{cli}', headers=h['admin'], json={'ativo': False}).status_code == 200
    r = c.post('/acertos/previa', headers=h['admin'], json=body)
    assert r.status_code == 422, r.text


def test_replay_evidencia_identica_e_alterada(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, forn, 'fornecedor')
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    a = draft(c, h, payload(forn, [(p['id'], n['id'], 100)], relacao='fornecedor'))
    sent = {'referencia_envio': 'Envio externo 1', 'observacao_envio': 'Relação comunicada externamente'}
    confirmed = {'referencia_confirmacao': 'Confirmação 1', 'observacao_confirmacao': 'Concordância documentada'}
    for suffix, body in (('enviar', sent), ('confirmar', confirmed)):
        url = f"/acertos/{a['id']}/{suffix}"
        assert c.post(url, headers=h['admin'], json=body).status_code == 200
        assert c.post(url, headers=h['admin'], json=body).status_code == 200
        field = 'referencia_envio' if suffix == 'enviar' else 'referencia_confirmacao'
        assert c.post(url, headers=h['admin'], json={**body, field: 'Outro documento'}).status_code == 409
    assert fetch(c, h, a['id'])['status'] == 'confirmado'
    assert balance(c, h, n['id']) == 1000


def test_total_lote_limite_contratual(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    notes = [note(c, h, cli, value=5000000000) for _ in range(2)]
    pays = [payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=5000000000) for _ in range(2)]
    body = payload(cli, [(p['id'], n['id'], 5000000000) for p, n in zip(pays, notes)])
    r = c.post('/acertos/previa', headers=h['admin'], json=body)
    assert r.status_code == 422, r.text


def test_soma_centavos_quita_nota_sem_residuo(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, cli, value=.3)
    pays = [payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=v) for v in (.1, .2)]
    a = draft(c, h, payload(cli, [(p['id'], n['id'], v) for p, v in zip(pays, (.1, .2))]))
    assert a['total_aplicar'] == .3
    assert execute(c, h, a['id']).status_code == 200
    assert balance(c, h, n['id']) == 0
    assert all(detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 0 for p in pays)


def test_recursos_filtram_usados_antes_limite(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    open_note = note(c, h, cli, value=100)
    available = payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=100)
    for _ in range(2):
        n = note(c, h, cli, value=100)
        p = payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=100)
        assert apply(c, h, p['id'], n['id'], valor=100).status_code == 201
    r = c.get(f'/acertos/recursos?pessoa_id={cli}&relacao=cliente&limit=1', headers=h['admin'])
    assert r.status_code == 200, r.text
    d = r.json()
    assert [p['id'] for p in d['pagamentos']] == [available['id']]
    assert [n['id'] for n in d['notas']] == [open_note['id']]
    assert d['pagamentos_tem_mais'] is False and d['notas_tem_mais'] is False
    assert c.get(f'/acertos/recursos?pessoa_id={cli}&relacao=cliente&limit=1').status_code in (401, 403)


def test_migracao_app_stage3_preserva_historico_duas_vezes(pagamentos_api, monkeypatch):
    from sqlalchemy import inspect, text
    import app.database as database
    c, h, sessions = pagamentos_api
    cli, _, n, p = setup_pair(c, h)
    a = apply(c, h, p['id'], n['id'], valor=100)
    assert a.status_code == 201
    with sessions() as db:
        engine = db.get_bind()
        old = db.execute(text('SELECT id,pagamento_id,nota_id,valor,estornada FROM pagamento_aplicacoes')).all()
    with engine.begin() as conn:
        names = ','.join(col['name'] for col in inspect(conn).get_columns('pagamento_aplicacoes') if col['name'] != 'acerto_id')
        conn.execute(text(f'CREATE TABLE pg_apps_antigas AS SELECT {names} FROM pagamento_aplicacoes'))
        conn.execute(text('DROP TABLE pagamento_aplicacoes'))
        conn.execute(text('ALTER TABLE pg_apps_antigas RENAME TO pagamento_aplicacoes'))
    monkeypatch.setattr(database, 'engine', engine)
    monkeypatch.setattr(database, 'SessionLocal', sessions)
    database.init_db()
    database.init_db()
    with engine.connect() as conn:
        assert 'acerto_id' in {col['name'] for col in inspect(conn).get_columns('pagamento_aplicacoes')}
        assert conn.execute(text('SELECT id,pagamento_id,nota_id,valor,estornada FROM pagamento_aplicacoes')).all() == old
        assert conn.execute(text('SELECT acerto_id FROM pagamento_aplicacoes')).scalar() is None
    assert balance(c, h, n['id']) == 900
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 200
