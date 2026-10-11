"""Metadados declarados e comprovantes privados não alteram fatos financeiros."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from tests.test_pagamentos import pagamentos_api, person, payment_payload, payment, detail
from tests.test_configuracoes import prefs
from app.models import Pagamento, PagamentoAnexo


def test_autoria_origemsistema_datetime_normalizado_e_idempotencia(pagamentos_api):
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    body = payment_payload(cliente_id=cli, fornecedor_id=forn, data_hora_transacao='2020-01-03T12:30:00-03:00',
        remetente='Remetente declarado', favorecido='Favorecido declarado', intermediador='Intermediador declarado')
    r = c.post('/pagamentos', headers=h['financeiro'], json=body)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p['origem_registro'] == 'manual' and p['autor_nome'] == 'financeiro'
    assert p['created_by'] and p['data_hora_transacao'] == '2020-01-03T15:30:00+00:00'
    assert p['created_at'].endswith('+00:00') and p['updated_at'].endswith('+00:00')
    assert p['remetente'] == body['remetente'] and p['favorecido'] == body['favorecido']
    again = c.post('/pagamentos', headers=h['financeiro'], json=body)
    assert again.status_code == 201 and again.json()['id'] == p['id']
    same_instant = c.post('/pagamentos', headers=h['financeiro'], json={**body, 'data_hora_transacao': '2020-01-03T15:30:00Z'})
    assert same_instant.status_code == 201 and same_instant.json()['id'] == p['id']
    for field, value in (('remetente', 'Outro remetente'), ('favorecido', 'Outro favorecido'),
        ('intermediador', 'Outro intermediador'), ('data_hora_transacao', '2020-01-03T13:30:00-03:00')):
        assert c.post('/pagamentos', headers=h['financeiro'], json={**body, field: value}).status_code == 409
    assert detail(c, h, p['id'])['orcamentos']['cliente']['saldo_disponivel'] == 300


@pytest.mark.parametrize('extra', [{'data_hora_transacao': '2020-01-03T12:00:00'},
    {'data_hora_transacao': '2020-01-03T00:00:00Z'}, {'data_hora_transacao': '2020-01-04T12:00:00Z'},
    {'data_hora_transacao': 'nao-data'}, {'remetente': 'x' * 161}, {'origem_registro': 'gateway'},
    {'created_by': 999999}, {'autor_nome': 'Autor forjado'},
    {'data_hora_transacao': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}])
def test_metadados_invalidos_sem_pagamento_parcial(pagamentos_api, extra):
    c, h, sessions = pagamentos_api
    body = payment_payload(cliente_id=person(c, h), fornecedor_id=person(c, h))
    r = c.post('/pagamentos', headers=h['admin'], json={**body, **extra})
    assert r.status_code == 422, r.text
    with sessions() as db:
        assert db.query(Pagamento).count() == 0


def test_datetime_omitido_legado_nao_inventa_origem_ou_horario(pagamentos_api):
    c, h, sessions = pagamentos_api
    body = payment_payload(cliente_id=person(c, h), fornecedor_id=person(c, h))
    r = c.post('/pagamentos', headers=h['admin'], json=body)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p['data_hora_transacao'] is None and p['origem_registro'] == 'manual'
    with sessions() as db:
        db.get(Pagamento, p['id']).origem_registro = None
        db.commit()
    current = detail(c, h, p['id'])
    assert current['origem_registro'] == 'nao_informada' and current['data_hora_transacao'] is None
    replay = c.post('/pagamentos', headers=h['admin'], json=body)
    assert replay.status_code == 201 and replay.json()['id'] == p['id']
    assert replay.json()['origem_registro'] == 'nao_informada' and replay.json()['data_hora_transacao'] is None
    assert c.patch(f"/pagamentos/{p['id']}", headers=h['admin'], json={'origem_registro': 'manual'}).status_code in (404, 405)


def test_transacao_calendario_sp_e_futuro_mesma_data(pagamentos_api):
    from zoneinfo import ZoneInfo
    from datetime import time
    c, h, _ = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    body = payment_payload(cliente_id=cli, fornecedor_id=forn, data='2020-01-03', data_hora_transacao='2020-01-04T01:00:00Z')
    r = c.post('/pagamentos', headers=h['admin'], json=body)
    assert r.status_code == 201, r.text
    assert r.json()['data_hora_transacao'] == '2020-01-04T01:00:00+00:00'
    sp = ZoneInfo('America/Sao_Paulo')
    today = datetime.now(sp).date()
    future = datetime.combine(today, time(23, 59, 59), tzinfo=sp)
    if future <= datetime.now(sp):
        pytest.skip('Último segundo do dia local')
    r = c.post('/pagamentos', headers=h['admin'], json=payment_payload(cliente_id=cli, fornecedor_id=forn,
        data=today.isoformat(), data_hora_transacao=future.isoformat()))
    assert r.status_code == 422, r.text


def test_valor_origem_filtros_antes_pagina_preferencias_whitelist(pagamentos_api):
    c, h, sessions = pagamentos_api
    cli, forn = person(c, h), person(c, h)
    wanted = payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=100)
    old = payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=100)
    with sessions() as db:
        db.get(Pagamento, old['id']).origem_registro = None
        db.commit()
    for value in (99.99, 100.01, 200):
        payment(c, h, cliente_id=cli, fornecedor_id=forn, valor=value)
    r = c.get('/pagamentos', headers=h['consulta'], params={'valor_min': '100.00', 'valor_max': '100.00',
        'origem_registro': 'manual', 'limit': 1})
    assert r.status_code == 200 and [p['id'] for p in r.json()] == [wanted['id']]
    r = c.get('/pagamentos', headers=h['admin'], params={'origem_registro': 'nao_informada'})
    assert r.status_code == 200 and [p['id'] for p in r.json()] == [old['id']]
    p = prefs('pagamentos', filtros={'valor_min': 100, 'valor_max': 200, 'origem_registro': 'manual'})
    assert c.put('/configuracoes/tabelas/pagamentos', headers=h['consulta'], json=p).status_code == 200
    assert c.get('/configuracoes/tabelas/pagamentos', headers=h['consulta']).json()['filtros'] == p['filtros']


@pytest.mark.parametrize('params', [{'valor_min': -1}, {'valor_min': 'NaN'}, {'valor_max': 'Infinity'},
    {'valor_min': '1.001'}, {'valor_min': 200, 'valor_max': 100}, {'origem_registro': 'gateway'}])
def test_filtro_valor_origem_invalido(pagamentos_api, params):
    c, h, _ = pagamentos_api
    assert c.get('/pagamentos', headers=h['admin'], params=params).status_code == 422
    p = prefs('pagamentos', filtros=params)
    assert c.put('/configuracoes/tabelas/pagamentos', headers=h['admin'], json=p).status_code == 422


@pytest.mark.parametrize('suffix,raw,mime', [('pdf', b'%PDF-1.4\nfixture', 'application/pdf'),
    ('png', b'\x89PNG\r\n\x1a\nfixture', 'image/png'), ('jpg', b'\xff\xd8\xfffixture', 'image/jpeg'),
    ('webp', b'RIFF\x10\x00\x00\x00WEBPfixture', 'image/webp')])
def test_comprovante_inline_privado_mime_real_ocultar_sem_cancelar(pagamentos_api, tmp_path, monkeypatch, suffix, raw, mime):
    from app.routers import pagamentos as router
    c, h, sessions = pagamentos_api
    monkeypatch.setattr(router, 'UPLOAD_DIR', tmp_path)
    p = payment(c, h, cliente_id=person(c, h), fornecedor_id=person(c, h))
    base = f"/pagamentos/{p['id']}/anexos"
    uploaded = c.post(base, headers=h['financeiro'], files={'f': (f'../../prova.{suffix}', raw, 'text/html')})
    assert uploaded.status_code == 201, uploaded.text
    a = uploaded.json()
    assert a['tipo_mime'] == mime and a['created_by'] and a['created_at'].endswith('+00:00')
    url = f"{base}/{a['id']}/arquivo"
    assert a['url_visualizacao'].endswith('?inline=true')
    before = detail(c, h, p['id'])['orcamentos']
    for perfil in ('admin', 'financeiro', 'operador', 'consulta'):
        response = c.get(url + '?inline=true', headers=h[perfil])
        assert response.status_code == 200 and response.content == raw
        assert response.headers['content-type'].split(';')[0] == mime
        assert response.headers['content-disposition'].startswith('inline')
        assert response.headers['x-content-type-options'] == 'nosniff'
        assert 'no-store' in response.headers['cache-control'] and 'sandbox' in response.headers['content-security-policy']
    assert c.get(url + '?inline=true').status_code == 401
    assert c.get(url, headers=h['admin']).headers['content-disposition'].startswith('attachment')
    assert c.delete(f"{base}/{a['id']}", headers=h['consulta']).status_code == 403
    assert c.delete(f"{base}/{a['id']}", headers=h['admin']).status_code == 200
    assert c.get(url + '?inline=true', headers=h['admin']).status_code == 404
    current = detail(c, h, p['id'])
    assert current['orcamentos'] == before and current['cancelado'] is False
    with sessions() as db:
        assert db.get(PagamentoAnexo, a['id']).ativo is False


def test_inline_arquivo_corrompido_path_fora_e_crossownership(pagamentos_api, tmp_path, monkeypatch):
    from app.routers import pagamentos as router
    c, h, sessions = pagamentos_api
    monkeypatch.setattr(router, 'UPLOAD_DIR', tmp_path)
    pid, forn = person(c, h), person(c, h)
    p, other = payment(c, h, cliente_id=pid, fornecedor_id=forn), payment(c, h, cliente_id=pid, fornecedor_id=forn)
    base = f"/pagamentos/{p['id']}/anexos"
    r = c.post(base, headers=h['admin'], files={'f': ('prova.pdf', b'%PDF-1.4 fixture', 'application/pdf')})
    assert r.status_code == 201, r.text
    aid = r.json()['id']
    assert c.get(f"/pagamentos/{other['id']}/anexos/{aid}/arquivo?inline=true", headers=h['admin']).status_code == 404
    with sessions() as db:
        a = db.get(PagamentoAnexo, aid)
        from pathlib import Path
        stored = Path(a.arquivo_path)
    stored.write_bytes(b'<html>executavel</html>')
    assert c.get(f'{base}/{aid}/arquivo?inline=true', headers=h['admin']).status_code == 415
    outside = tmp_path.parent / f'fora-{uuid4().hex}.pdf'
    try:
        outside.write_bytes(b'%PDF-1.4 arquivo externo')
        with sessions() as db:
            db.get(PagamentoAnexo, aid).arquivo_path = str(outside)
            db.commit()
        assert c.get(f'{base}/{aid}/arquivo?inline=true', headers=h['admin']).status_code == 404
    finally:
        outside.unlink(missing_ok=True)
