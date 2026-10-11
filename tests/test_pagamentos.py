"""Um fato financeiro com orçamentos independentes; bancos temporários por teste."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.auth import hash_pw, token_for
from app.cadastros import hoje
from app.database import get_db
from app.main import app
from app.models import Base, User


@pytest.fixture
def pagamentos_api(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'pagamentos.db'}", connect_args={'check_same_thread': False, 'timeout': 15})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        users = [User(nome=p, email=f'{p}@pagamentos.local', perfil=p, senha_hash=hash_pw('senha-teste'), ativo=True)
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
    r = c.post('/pessoas', headers=h['admin'], json={'nome': 'Titular pagamento', 'tipo': 'ambos', **extra})
    assert r.status_code == 201, r.text
    return r.json()['id']


def note(c, h, pid, relacao='cliente', value=1000):
    r = c.post('/notas', headers=h['admin'], json={'pessoa_id': pid, 'relacao': relacao,
        'numero_documento': uuid4().hex, 'valor_original': value, 'data_emissao': '2020-01-01',
        'descricao': 'Nota teste', 'modo_vencimento': 'sem_vencimento'})
    assert r.status_code == 201, r.text
    return r.json()


def payment_payload(**extra):
    return {'tipo': 'cliente_fornecedor', 'forma': 'PIX', 'valor': 300, 'data': '2020-01-03',
        'referencia_externa': 'ref-' + uuid4().hex, 'observacao': 'Pagamento ocorrido conferido',
        'chave_idempotencia': uuid4().hex, 'declaracao_novo_pagamento': True, **extra}


def payment(c, h, **extra):
    r = c.post('/pagamentos', headers=h['admin'], json=payment_payload(**extra))
    assert r.status_code == 201, r.text
    return r.json()


def apply(c, h, payment_id, note_id, relacao='cliente', **extra):
    return c.post(f'/pagamentos/{payment_id}/aplicacoes', headers=h['admin'], json={
        'nota_id': note_id, 'relacao': relacao, 'valor': 300, 'data': '2020-01-03',
        'referencia': 'Aplicação conferida', 'observacao': 'Baixa da nota por pagamento',
        'chave_idempotencia': uuid4().hex, **({'fornecedor_confirmou': True, 'referencia_confirmacao': 'Fornecedor conferiu externamente'} if relacao == 'fornecedor' else {}), **extra})


def detail(c, h, pid):
    r = c.get(f'/pagamentos/{pid}', headers=h['admin'])
    assert r.status_code == 200, r.text
    return r.json()


def balance(c, h, nid):
    return c.get(f'/notas/{nid}', headers=h['admin']).json()['saldo_aberto']


def test_um_pix_duas_baixas_independentes(pagamentos_api):
    c, h, sessions = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    venda, compra = note(c, h, cli), note(c, h, forn, 'fornecedor', 900)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    a = apply(c, h, p['id'], venda['id'])
    assert a.status_code == 201, a.text
    assert balance(c, h, venda['id']) == 700 and balance(c, h, compra['id']) == 900
    d = detail(c, h, p['id'])
    assert d['orcamentos']['cliente']['saldo_disponivel'] == 0
    assert d['orcamentos']['fornecedor']['saldo_disponivel'] == 300
    b = apply(c, h, p['id'], compra['id'], 'fornecedor')
    assert b.status_code == 201, b.text
    assert balance(c, h, venda['id']) == 700 and balance(c, h, compra['id']) == 600
    rows = c.get('/pagamentos', headers=h['admin']).json()
    assert len(rows) == 1
    from app.models import Movimentacao, Conciliacao, Lancamento, NotaAbatimento
    with sessions() as db:
        assert all(db.query(m).count() == 0 for m in (Movimentacao, Conciliacao, Lancamento))
        abas = db.query(NotaAbatimento).all()
        assert len(abas) == 2 and all(a.origem == 'pagamento' for a in abas)


def test_dinheiro_cliente_so_fornecedor_apos_repasse(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    venda, compra = note(c, h, cli), note(c, h, forn, 'fornecedor', 900)
    p = payment(c, h, tipo='cliente_loja', forma='dinheiro', valor=100, cliente_id=cli)
    assert apply(c, h, p['id'], venda['id'], valor=100).status_code == 201
    assert apply(c, h, p['id'], compra['id'], 'fornecedor', valor=100).status_code == 422
    assert balance(c, h, compra['id']) == 900
    child = payment(c, h, tipo='repasse_fornecedor', fornecedor_id=forn, pagamento_origem_id=p['id'], valor=100)
    assert apply(c, h, child['id'], compra['id'], 'fornecedor', valor=100).status_code == 201
    assert apply(c, h, child['id'], venda['id'], valor=1).status_code == 422
    assert balance(c, h, venda['id']) == 900 and balance(c, h, compra['id']) == 800
    d = detail(c, h, p['id'])
    assert d['valor_repassado'] == 100 and d['saldo_para_repasse'] == 0


def test_criacao_idempotente_e_ref_normalizada(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    body = payment_payload(cliente_id=cli, fornecedor_id=forn, referencia_externa=' REF-ÚNICA ')
    a = c.post('/pagamentos', headers=h['admin'], json=body)
    b = c.post('/pagamentos', headers=h['admin'], json=body)
    assert a.status_code == b.status_code == 201 and a.json()['id'] == b.json()['id']
    assert c.post('/pagamentos', headers=h['admin'], json={**body, 'valor': 200}).status_code == 409
    assert c.post('/pagamentos', headers=h['admin'], json={**body, 'chave_idempotencia': uuid4().hex,
        'referencia_externa': 'ref-única'}).status_code == 409
    assert len(c.get('/pagamentos', headers=h['admin']).json()) == 1


def test_aplicacao_idempotente_nota_titular_e_lado(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn, stranger = person(c, h), person(c, h), person(c, h)
    venda, compra, alien = note(c, h, cli), note(c, h, forn, 'fornecedor'), note(c, h, stranger)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    assert apply(c, h, p['id'], alien['id']).status_code == 422
    assert apply(c, h, p['id'], compra['id']).status_code == 422
    key = uuid4().hex
    a = apply(c, h, p['id'], venda['id'], chave_idempotencia=key)
    b = apply(c, h, p['id'], venda['id'], chave_idempotencia=key)
    assert a.status_code == b.status_code == 201 and a.json()['id'] == b.json()['id']
    assert apply(c, h, p['id'], venda['id'], chave_idempotencia=key, valor=20).status_code == 409
    assert balance(c, h, venda['id']) == 700


def test_limites_pagamento_e_nota(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    small, large = note(c, h, cli, value=20), note(c, h, cli)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=100)
    assert apply(c, h, p['id'], small['id'], valor=21).status_code == 422
    assert apply(c, h, p['id'], large['id'], valor=101).status_code == 422
    assert balance(c, h, small['id']) == 20 and balance(c, h, large['id']) == 1000
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 100


def test_estorno_um_lado_preserva_outro_e_bloqueia_estorno_isolado(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    venda, compra = note(c, h, cli), note(c, h, forn, 'fornecedor')
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    a = apply(c, h, p['id'], venda['id']).json()
    assert apply(c, h, p['id'], compra['id'], 'fornecedor').status_code == 201
    undo = {'senha': 'senha-teste', 'motivo': 'Correção documentada'}
    assert c.post(f"/notas/{venda['id']}/abatimentos/{a['nota_abatimento_id']}/estornar", headers=h['admin'], json=undo).status_code in (409, 422)
    url = f"/pagamentos/{p['id']}/aplicacoes/{a['id']}/estornar"
    assert c.post(url, headers=h['admin'], json={**undo, 'senha': 'incorreta'}).status_code == 403
    assert balance(c, h, venda['id']) == 700
    assert c.post(url, headers=h['admin'], json=undo).status_code == 200
    assert balance(c, h, venda['id']) == 1000 and balance(c, h, compra['id']) == 700
    d = detail(c, h, p['id'])
    assert d['orcamentos']['cliente']['saldo_disponivel'] == 300
    assert d['orcamentos']['fornecedor']['saldo_disponivel'] == 0
    assert c.post(url, headers=h['admin'], json=undo).status_code in (409, 422)


def test_cancelamento_com_dependentes_bloqueado(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, cli)
    p = payment(c, h, tipo='cliente_loja', cliente_id=cli, valor=100)
    a = apply(c, h, p['id'], n['id'], valor=100).json()
    undo = {'senha': 'senha-teste', 'motivo': 'Correção documentada'}
    url = f"/pagamentos/{p['id']}/cancelar"
    assert c.post(url, headers=h['admin'], json=undo).status_code in (409, 422)
    assert c.post(f"/pagamentos/{p['id']}/aplicacoes/{a['id']}/estornar", headers=h['admin'], json=undo).status_code == 200
    child = payment(c, h, tipo='repasse_fornecedor', fornecedor_id=forn, pagamento_origem_id=p['id'], valor=100)
    assert c.post(url, headers=h['admin'], json=undo).status_code in (409, 422)
    assert c.post(f"/pagamentos/{child['id']}/cancelar", headers=h['admin'], json=undo).status_code == 200
    assert c.post(url, headers=h['admin'], json=undo).status_code == 200
    assert apply(c, h, p['id'], n['id'], valor=1).status_code in (409, 422)


@pytest.mark.parametrize('valor', [0, -1, 1.001, 10000000000, 'NaN', 'Infinity'])
def test_dinheiro_invalido(pagamentos_api, valor):
    c, h, _ = pagamentos_api
    body = payment_payload(cliente_id=person(c, h), fornecedor_id=person(c, h), valor=valor)
    assert c.post('/pagamentos', headers=h['admin'], json=body).status_code == 422


def test_datas_formas_titulares_declaracao(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    base = payment_payload(cliente_id=cli, fornecedor_id=forn)
    for extra in ({'data': (hoje()+timedelta(days=1)).isoformat()}, {'forma': 'dinheiro'},
                  {'declaracao_novo_pagamento': False}, {'cliente_id': None}, {'fornecedor_id': None}):
        assert c.post('/pagamentos', headers=h['admin'], json={**base, **extra}).status_code == 422
    inactive = person(c, h)
    c.patch(f'/pessoas/{inactive}', headers=h['admin'], json={'ativo': False})
    assert c.post('/pagamentos', headers=h['admin'], json={**base, 'cliente_id': inactive}).status_code == 422
    supplier_only = person(c, h, tipo='fornecedor')
    assert c.post('/pagamentos', headers=h['admin'], json={**base, 'cliente_id': supplier_only}).status_code == 422


def test_datas_aplicacao_e_repasse(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, cli)
    p = payment(c, h, tipo='cliente_loja', cliente_id=cli)
    for date in ('2019-12-31', '2020-01-02', (hoje()+timedelta(days=1)).isoformat()):
        assert apply(c, h, p['id'], n['id'], data=date).status_code == 422
    child = payment_payload(tipo='repasse_fornecedor', fornecedor_id=forn, pagamento_origem_id=p['id'], data='2020-01-02')
    assert c.post('/pagamentos', headers=h['admin'], json=child).status_code == 422


def test_permissoes(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    for role in ('operador', 'consulta'):
        assert c.get('/pagamentos', headers=h[role]).status_code == 200
        assert c.get(f"/pagamentos/{p['id']}", headers=h[role]).status_code == 200
        assert c.post('/pagamentos', headers=h[role], json=payment_payload(cliente_id=cli, fornecedor_id=forn)).status_code == 403
        assert c.post(f"/pagamentos/{p['id']}/cancelar", headers=h[role], json={'senha': 'senha-teste', 'motivo': 'Teste'}).status_code == 403
    assert c.get('/pagamentos').status_code in (401, 403)


def test_concorrencia_orcamento_pagamento(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    notes = [note(c, h, cli) for _ in range(2)]
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=100)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda n: apply(c, h, p['id'], n['id'], valor=100), notes))
    assert sorted(r.status_code for r in responses) in ([201, 409], [201, 422]), [r.text for r in responses]
    assert sum(1000 - balance(c, h, n['id']) for n in notes) == 100


def test_concorrencia_saldo_nota(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, cli, value=100)
    payments = [payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=100) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda p: apply(c, h, p['id'], n['id'], valor=100), payments))
    assert sorted(r.status_code for r in responses) in ([201, 409], [201, 422]), [r.text for r in responses]
    assert balance(c, h, n['id']) == 0


def test_concorrencia_repasse_nao_excede_fonte(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    p = payment(c, h, tipo='cliente_loja', cliente_id=cli, valor=100)
    def create(_):
        return c.post('/pagamentos', headers=h['admin'], json=payment_payload(tipo='repasse_fornecedor',
            fornecedor_id=forn, pagamento_origem_id=p['id'], valor=100))
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(create, range(2)))
    assert sorted(r.status_code for r in responses) in ([201, 409], [201, 422]), [r.text for r in responses]
    assert detail(c, h, p['id'])['valor_repassado'] == 100


def test_referencia_documental_nao_vira_pagamento_duplicado(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, cli)
    a = c.post(f"/notas/{n['id']}/abatimentos", headers=h['admin'], json={'valor': 100, 'data': '2020-01-03',
        'referencia': 'ACERTO-EXTERNO-1', 'observacao': 'Já documentado antes', 'chave_idempotencia': uuid4().hex})
    assert a.status_code == 201
    r = c.post('/pagamentos', headers=h['admin'], json=payment_payload(cliente_id=cli, fornecedor_id=forn,
        referencia_externa=' acerto-externo-1 '))
    assert r.status_code == 409, r.text
    assert balance(c, h, n['id']) == 900
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    r = apply(c, h, p['id'], n['id'], referencia='acerto-externo-1', valor=100)
    assert r.status_code == 409, r.text
    assert balance(c, h, n['id']) == 900


def test_referencias_legadas_pix_e_gateway_bloqueadas(pagamentos_api):
    from app.models import Movimentacao, Comprovante
    from datetime import date
    c, h, sessions = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    with sessions() as db:
        pix = Movimentacao(codigo='PIX-999991', data_pix=date(2020, 1, 3), valor=100, saldo_disponivel=100, representante_id=cli, fornecedor_id=forn)
        db.add(pix)
        db.flush()
        comp = Comprovante(movimentacao_id=pix.id, arquivo_path='checkto:tx-old', arquivo_hash='ckto:tx-old')
        db.add(comp)
        db.commit()
    for ref in (' pix-999991 ', 'tx-old', 'ckto:tx-old'):
        r = c.post('/pagamentos', headers=h['admin'], json=payment_payload(cliente_id=cli, fornecedor_id=forn,
            referencia_externa=ref))
        assert r.status_code == 409, r.text
    assert c.get('/pagamentos', headers=h['admin']).json() == []


def test_anexos_pagamento_privados_ownership_limite(pagamentos_api, tmp_path, monkeypatch):
    import app.routers.pagamentos as router
    monkeypatch.setattr(router, 'UPLOAD_DIR', str(tmp_path / 'uploads'))
    monkeypatch.setattr(router, 'MAX_UPLOAD_MB', 1)
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    other = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    url = f"/pagamentos/{p['id']}/anexos"
    pdf = b'%PDF-1.4\nexemplo\n%%EOF'
    assert c.post(url, headers=h['consulta'], files={'f': ('nota.pdf', pdf, 'application/pdf')}).status_code == 403
    r = c.post(url, headers=h['admin'], files={'f': ('../../recibo.pdf', pdf, 'application/octet-stream')})
    assert r.status_code == 201, r.text
    aid = r.json()['id']
    file_url = f'{url}/{aid}/arquivo'
    assert c.get(file_url).status_code in (401, 403)
    downloaded = c.get(file_url, headers=h['consulta'])
    assert downloaded.content == pdf and downloaded.status_code == 200
    assert downloaded.headers['cache-control'] == 'private, no-store'
    assert downloaded.headers['x-content-type-options'] == 'nosniff'
    assert 'attachment' in downloaded.headers['content-disposition']
    assert c.get(f"/pagamentos/{other['id']}/anexos/{aid}/arquivo", headers=h['admin']).status_code == 404
    assert c.post(url, headers=h['admin'], files={'f': ('fake.pdf', b'fake', 'application/pdf')}).status_code == 422
    assert c.post(url, headers=h['admin'], files={'f': ('large.pdf', b'%PDF-'+b'x'*(1024*1024), 'application/pdf')}).status_code == 422
    assert c.delete(f'{url}/{aid}', headers=h['admin']).status_code == 200
    assert c.get(file_url, headers=h['admin']).status_code == 404


def test_referencia_externa_preserva_texto_original(pagamentos_api):
    c, h, _ = pagamentos_api
    p = payment(c, h, cliente_id=person(c, h), fornecedor_id=person(c, h), referencia_externa='  Recibo-ÁBC  ')
    assert p['referencia_externa'] == 'Recibo-ÁBC'
    assert p['codigo'] == f"PAG-{p['id']:06d}"


def test_centavos_orcamento_e_notas_quitadas(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, cli, value=0.3)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=0.3)
    for v in (0.1, 0.2):
        r = apply(c, h, p['id'], n['id'], valor=v)
        assert r.status_code == 201, r.text
    d = detail(c, h, p['id'])
    assert d['orcamentos']['cliente']['saldo_disponivel'] == 0
    assert d['orcamentos']['cliente']['status'] == 'utilizado'
    rows = c.get(f"/notas?pessoa_id={cli}&status=quitado", headers=h['admin']).json()
    assert [row['id'] for row in rows] == [n['id']]


def test_migracao_abatimentos_antigos_idempotente(pagamentos_api, monkeypatch):
    from sqlalchemy import text, inspect
    import app.database as database
    c, h, sessions = pagamentos_api
    pid = person(c, h)
    n = note(c, h, pid)
    r = c.post(f"/notas/{n['id']}/abatimentos", headers=h['admin'], json={'valor': 100, 'data': '2020-01-03',
        'referencia': 'Acerto legado', 'observacao': 'Registro anterior preservado', 'chave_idempotencia': 'antigo'})
    assert r.status_code == 201
    with sessions() as db:
        old = db.execute(text('SELECT id,nota_id,valor,referencia,origem,estornado FROM nota_abatimentos')).all()
        engine = db.get_bind()
    with engine.begin() as conn:
        # Simula schema pré-Sprint3 em banco exclusivamente descartável.
        columns = [col['name'] for col in inspect(conn).get_columns('nota_abatimentos') if col['name'] not in ('pagamento_aplicacao_id', 'referencia_chave')]
        names = ','.join(columns)
        conn.execute(text(f'CREATE TABLE nota_abatimentos_antigos AS SELECT {names} FROM nota_abatimentos'))
        conn.execute(text('DROP TABLE nota_abatimentos'))
        conn.execute(text('ALTER TABLE nota_abatimentos_antigos RENAME TO nota_abatimentos'))
    monkeypatch.setattr(database, 'engine', engine)
    monkeypatch.setattr(database, 'SessionLocal', sessions)
    database.init_db()
    database.init_db()
    with engine.connect() as conn:
        assert 'pagamento_aplicacao_id' in {col['name'] for col in inspect(conn).get_columns('nota_abatimentos')}
        assert conn.execute(text('SELECT id,nota_id,valor,referencia,origem,estornado FROM nota_abatimentos')).all() == old
        assert conn.execute(text('SELECT COUNT(*) FROM pagamentos')).scalar() == 0
    assert balance(c, h, n['id']) == 900


def test_aplicacao_fornecedor_exige_conferencia_documentada(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, forn, 'fornecedor')
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    for extra in ({'fornecedor_confirmou': False}, {'referencia_confirmacao': ''}, {'referencia_confirmacao': '   '}):
        r = apply(c, h, p['id'], n['id'], 'fornecedor', **extra)
        assert r.status_code == 422, r.text
    body = {'nota_id': n['id'], 'relacao': 'fornecedor', 'valor': 300, 'data': '2020-01-03',
        'referencia': 'Acerto', 'observacao': 'Conferência pendente', 'chave_idempotencia': uuid4().hex}
    assert c.post(f"/pagamentos/{p['id']}/aplicacoes", headers=h['admin'], json=body).status_code == 422
    assert balance(c, h, n['id']) == 1000
    assert detail(c, h, p['id'])['orcamentos']['fornecedor']['saldo_disponivel'] == 300


def test_pagamento_preserva_papeis_titulares_com_historico(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    assert c.patch(f'/pessoas/{cli}', headers=h['admin'], json={'tipo': 'fornecedor'}).status_code == 409
    assert c.patch(f'/pessoas/{forn}', headers=h['admin'], json={'tipo': 'cliente'}).status_code == 409
    assert c.patch(f'/pessoas/{cli}', headers=h['admin'], json={'ativo': False}).status_code == 200
    assert detail(c, h, p['id'])['cliente_id'] == cli


def test_cliente_nao_declara_confirmacao_fornecedor(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, cli)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    r = apply(c, h, p['id'], n['id'], fornecedor_confirmou=True, referencia_confirmacao='Confirmação indevida')
    assert r.status_code == 422
    assert balance(c, h, n['id']) == 1000


def test_pagamento_existente_impede_documento_manual_mesma_referencia(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, cli)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn, referencia_externa='PAGAMENTO-ÚNICO')
    r = c.post(f"/notas/{n['id']}/abatimentos", headers=h['admin'], json={'valor': 100, 'data': '2020-01-03',
        'referencia': ' pagamento-único ', 'observacao': 'Documento duplicaria evento', 'chave_idempotencia': uuid4().hex})
    assert r.status_code == 409, r.text
    assert balance(c, h, n['id']) == 1000
    a = apply(c, h, p['id'], n['id'], referencia='REFERÊNCIA-APLICAÇÃO', valor=100)
    assert a.status_code == 201
    r = c.post(f"/notas/{n['id']}/abatimentos", headers=h['admin'], json={'valor': 100, 'data': '2020-01-03',
        'referencia': ' referência-aplicação ', 'observacao': 'Também duplicaria aplicação', 'chave_idempotencia': uuid4().hex})
    assert r.status_code == 409, r.text
    assert balance(c, h, n['id']) == 900


def test_referencia_documental_unicode_casefold(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, cli)
    r = c.post(f"/notas/{n['id']}/abatimentos", headers=h['admin'], json={'valor': 100, 'data': '2020-01-03',
        'referencia': 'Acerto-ÁBC', 'observacao': 'Registro antigo unicode', 'chave_idempotencia': uuid4().hex})
    assert r.status_code == 201
    for ref in ('acerto-ábc', ' ACERTO-ÁBC '):
        r = c.post('/pagamentos', headers=h['admin'], json=payment_payload(cliente_id=cli, fornecedor_id=forn, referencia_externa=ref))
        assert r.status_code == 409, r.text
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    assert apply(c, h, p['id'], n['id'], referencia='acerto-ábc', valor=100).status_code == 409


def test_concorrencia_documento_vs_pagamento_mesma_referencia(pagamentos_api):
    from threading import Barrier
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, cli)
    gate = Barrier(2)
    def manual():
        gate.wait()
        return c.post(f"/notas/{n['id']}/abatimentos", headers=h['admin'], json={'valor': 100, 'data': '2020-01-03',
            'referencia': 'Recibo-ÁBC', 'observacao': 'Documental concorrente', 'chave_idempotencia': uuid4().hex})
    def novo():
        gate.wait()
        return c.post('/pagamentos', headers=h['admin'], json=payment_payload(cliente_id=cli, fornecedor_id=forn,
            referencia_externa='recibo-ábc'))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(manual), pool.submit(novo)]
        responses = [f.result() for f in futures]
    assert sorted(r.status_code for r in responses) == [201, 409], [r.text for r in responses]
    rows = c.get('/pagamentos', headers=h['admin']).json()
    assert (len(rows), balance(c, h, n['id'])) in ((1, 1000), (0, 900))


def test_concorrencia_documento_vs_aplicacao_mesma_referencia(pagamentos_api):
    from threading import Barrier
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    n = note(c, h, cli)
    p = payment(c, h, cliente_id=cli, fornecedor_id=forn)
    gate = Barrier(2)
    def manual():
        gate.wait()
        return c.post(f"/notas/{n['id']}/abatimentos", headers=h['admin'], json={'valor': 100, 'data': '2020-01-03',
            'referencia': 'Aplicação-ÁBC', 'observacao': 'Documental concorrente', 'chave_idempotencia': uuid4().hex})
    def aplicar():
        gate.wait()
        return apply(c, h, p['id'], n['id'], referencia='aplicação-ábc', valor=100)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(manual), pool.submit(aplicar)]
        responses = [f.result() for f in futures]
    assert sorted(r.status_code for r in responses) == [201, 409], [r.text for r in responses]
    assert balance(c, h, n['id']) == 900
