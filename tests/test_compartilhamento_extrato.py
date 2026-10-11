"""Compartilhamento revogável: token próprio, projeção mínima e leitura sem escrita."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
import pytest
from tests.test_administracao import administracao_api
from tests.test_pagamentos import person, note, payment, apply
from app.models import Base, User, Pessoa, AuditLog


def issue(c, h, pid, relacao='cliente', **extra):
    r = c.post(f'/extratos/{pid}/compartilhamentos', headers=h['admin'], json={
        'relacao': relacao, 'destinatario': 'Destinatário autorizado', 'validade_dias': 7, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def public(c, share_token, **params):
    return c.get('/publico/extratos', headers={'Authorization': f'Bearer {share_token}'}, params=params)


def db_snapshot(sessions):
    with sessions() as db:
        return {table.name: [tuple(row) for row in db.execute(table.select().order_by(*table.primary_key.columns))]
                for table in Base.metadata.sorted_tables}


def test_token_unico_sha256_armazenado_sem_segredo_em_listas_auditoria(administracao_api):
    import re
    from app.models import CompartilhamentoExtrato
    c, h, sessions, _ = administracao_api
    pid = person(c, h)
    issued = issue(c, h, pid)
    token = issued['token']
    assert re.fullmatch(r'[A-Za-z0-9_-]{43}', token)
    created = datetime.fromisoformat(issued['created_at'])
    expires = datetime.fromisoformat(issued['expira_em'])
    assert timedelta(days=7) - timedelta(seconds=1) <= expires - created <= timedelta(days=7) + timedelta(seconds=1)
    with sessions() as db:
        link = db.get(CompartilhamentoExtrato, issued['id'])
        digest = hashlib.sha256(token.encode()).hexdigest()
        assert link.token_hash == digest
        assert token not in repr(db_snapshot(sessions))
        logs = db.query(AuditLog).all()
        assert all(token not in a.antes + a.depois and digest not in a.antes + a.depois for a in logs)
    for response in (c.get(f'/extratos/{pid}/compartilhamentos', headers=h['admin']),
                     c.get('/auditoria', headers=h['admin']), c.get('/export/auditoria.csv', headers=h['admin'])):
        assert response.status_code == 200
        assert token not in response.text and digest not in response.text
    listed = c.get(f'/extratos/{pid}/compartilhamentos', headers=h['admin']).json()
    assert listed['total'] == 1 and 'token' not in listed['itens'][0]
    second = issue(c, h, pid)
    assert second['token'] != token


def test_isolamento_titulares_relacoes_e_leitura_sem_mutacoes(administracao_api):
    c, h, sessions, _ = administracao_api
    a, b = person(c, h), person(c, h)
    note(c, h, a, value=500)
    note(c, h, a, 'fornecedor', value=900)
    note(c, h, b, value=7777)
    cli, forn = issue(c, h, a), issue(c, h, a, 'fornecedor')
    baseline = db_snapshot(sessions)
    for issued, relation, value in ((cli, 'cliente', 500), (forn, 'fornecedor', 900)):
        r = public(c, issued['token'])
        assert r.status_code == 200, r.text
        out = r.json()
        assert out['relacao'] == relation and out['escopo'] == 'compartilhado_restrito'
        assert out['totais_globais']['notas']['saldo_aberto'] == value
        assert len(out['notas']['itens']) == 1
        assert out['notas']['itens'][0]['valor_original'] == value
        assert out['totais_globais']['notas']['saldo_vencido'] == 0
    assert db_snapshot(sessions) == baseline


@pytest.mark.parametrize('tamper', [{'pessoa_id': 999}, {'relacao': 'fornecedor'}, {'token': 'forjado'}, {'data_de': '2020-01-01'}, {'status': 'aberto'}, {'limit': 100}])
def test_query_nao_pode_alterar_escopo(administracao_api, tamper):
    c, h, _, _ = administracao_api
    issued = issue(c, h, person(c, h))
    r = public(c, issued['token'], **tamper)
    assert r.status_code == 422 and r.json() == {'detail': 'Parâmetros inválidos'}


@pytest.mark.parametrize('authorization', [None, '', 'Bearer errado', 'Bearer ' + 'x'*43, 'Basic ' + 'x'*43])
def test_sem_token_ou_token_invalido_404_uniforme(administracao_api, authorization):
    c, _, _, _ = administracao_api
    headers = {} if authorization is None else {'Authorization': authorization}
    r = c.get('/publico/extratos', headers=headers)
    assert r.status_code == 404 and r.json() == {'detail': 'Extrato indisponível'}


def test_jwt_da_conta_nao_autoriza_publico_e_query_repetida_rejeitada(administracao_api):
    c, h, _, _ = administracao_api
    issued = issue(c, h, person(c, h))
    r = c.get('/publico/extratos', headers=h['admin'])
    assert r.status_code == 404 and r.json() == {'detail': 'Extrato indisponível'}
    assert c.get('/publico/extratos?notas_limit=1&notas_limit=2', headers={'Authorization': 'Bearer '+issued['token']}).status_code == 422


@pytest.mark.parametrize('invalidity', ['expired', 'revoked', 'issuer_inactive', 'issuer_consulta', 'person_inactive'])
def test_vinculo_expiracao_revogacao_e_atores_invalidam_acesso(administracao_api, invalidity):
    from app.models import CompartilhamentoExtrato
    c, h, sessions, ids = administracao_api
    pid = person(c, h)
    issued = issue(c, h, pid)
    with sessions() as db:
        link = db.get(CompartilhamentoExtrato, issued['id'])
        if invalidity == 'expired':
            link.expira_em = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
        elif invalidity == 'revoked':
            link.revogado = True
        elif invalidity == 'issuer_inactive':
            db.get(User, ids['admin']).ativo = False
        elif invalidity == 'issuer_consulta':
            db.get(User, ids['admin']).perfil = 'consulta'
        else:
            db.get(Pessoa, pid).ativo = False
        db.commit()
    before = db_snapshot(sessions)
    r = public(c, issued['token'])
    assert r.status_code == 404 and r.json() == {'detail': 'Extrato indisponível'}
    assert db_snapshot(sessions) == before


@pytest.mark.parametrize('role', ['operador', 'consulta'])
def test_gestao_negada_perfis_sem_permissao(administracao_api, role):
    c, h, _, _ = administracao_api
    pid = person(c, h)
    issued = issue(c, h, pid)
    assert c.post(f'/extratos/{pid}/compartilhamentos', headers=h[role], json={'relacao': 'cliente', 'destinatario': 'Pessoa', 'validade_dias': 7}).status_code == 403
    assert c.get(f'/extratos/{pid}/compartilhamentos', headers=h[role]).status_code == 403
    assert c.post(f"/extratos/{pid}/compartilhamentos/{issued['id']}/revogar", headers=h[role], json={'motivo': 'Solicitado'}).status_code == 403


def test_revogacao_escopo_id_nao_cruza_titular_e_nao_repete_evento(administracao_api):
    c, h, sessions, _ = administracao_api
    a, b = person(c, h), person(c, h)
    issued = issue(c, h, a)
    assert c.post(f"/extratos/{b}/compartilhamentos/{issued['id']}/revogar", headers=h['financeiro'], json={'motivo': 'Solicitado'}).status_code == 404
    assert public(c, issued['token']).status_code == 200
    url = f"/extratos/{a}/compartilhamentos/{issued['id']}/revogar"
    assert c.post(url, headers=h['financeiro'], json={'motivo': ' x '}).status_code == 422
    assert c.post(url, headers=h['financeiro'], json={'motivo': 'Solicitado pelo titular'}).status_code == 200
    assert c.post(url, headers=h['financeiro'], json={'motivo': 'Solicitado pelo titular'}).status_code == 200
    assert public(c, issued['token']).status_code == 404
    with sessions() as db:
        assert db.query(AuditLog).filter(AuditLog.acao == 'extrato_compartilhamento_revogado').count() == 1


def test_projecao_exata_sem_pii_counterparty_referencia_ou_anexos(administracao_api):
    c, h, _, _ = administracao_api
    pid = person(c, h, nome='TITULAR-SENTINELA', email='sentinela@example.com', telefone='CONTATO-SENTINELA', chave_pix='CHAVE-SENTINELA')
    other = person(c, h, nome='CONTRAPARTE-SENTINELA')
    n = note(c, h, pid)
    p = payment(c, h, cliente_id=pid, fornecedor_id=other, observacao='OBSERVACAO-SENTINELA', referencia_externa='REFERENCIA-SENTINELA', remetente='REMETENTE-SENTINELA')
    assert apply(c, h, p['id'], n['id'], valor=100).status_code == 201
    issued = issue(c, h, pid)
    r = public(c, issued['token'])
    assert r.status_code == 200, r.text
    out = r.json()
    assert set(out) == {'relacao', 'escopo', 'expira_em', 'totais_globais', 'notas', 'pagamentos'}
    assert set(out['notas']['itens'][0]) == {'numero_documento', 'data_emissao', 'vencimento', 'valor_original', 'valor_abatido', 'saldo_aberto', 'status', 'em_atraso'}
    assert set(out['pagamentos']['itens'][0]) == {'data', 'forma', 'valor', 'valor_aplicado', 'destinado_credito', 'saldo_disponivel', 'status'}
    for marker in ('TITULAR-SENTINELA', 'CONTRAPARTE-SENTINELA', 'CONTATO-SENTINELA', 'CHAVE-SENTINELA', 'REFERENCIA-SENTINELA', 'OBSERVACAO-SENTINELA', 'REMETENTE-SENTINELA', 'sentinela@example.com'):
        assert marker not in r.text
    assert '/api/' not in r.text and '/anexos/' not in r.text


def test_pagamento_mesmo_evento_duas_relacoes_valores_separados(administracao_api):
    c, h, _, _ = administracao_api
    pid = person(c, h)
    cli, forn = note(c, h, pid), note(c, h, pid, 'fornecedor', 900)
    p = payment(c, h, cliente_id=pid, fornecedor_id=pid)
    assert apply(c, h, p['id'], cli['id'], valor=100).status_code == 201
    assert apply(c, h, p['id'], forn['id'], 'fornecedor', valor=200).status_code == 201
    for relation, used, remaining in (('cliente', 100, 200), ('fornecedor', 200, 100)):
        out = public(c, issue(c, h, pid, relation)['token']).json()
        totals = out['totais_globais']['pagamentos']
        assert totals['valor_elegivel'] == 300 and totals['valor_aplicado'] == used and totals['saldo_disponivel'] == remaining
        assert out['pagamentos']['total'] == 1 and out['pagamentos']['itens'][0]['valor_aplicado'] == used


def test_paginacao_nao_reduz_totais_globais(administracao_api):
    c, h, _, _ = administracao_api
    pid, other = person(c, h), person(c, h)
    for value in (100, 200, 300):
        note(c, h, pid, value=value)
        payment(c, h, cliente_id=pid, fornecedor_id=other, valor=value)
    issued = issue(c, h, pid)
    first = public(c, issued['token'], notas_limit=1, pagamentos_limit=1).json()
    second = public(c, issued['token'], notas_limit=1, notas_offset=1, pagamentos_limit=1, pagamentos_offset=1).json()
    assert first['totais_globais'] == second['totais_globais']
    assert first['totais_globais']['notas']['saldo_aberto'] == 600
    assert first['notas']['total'] == first['pagamentos']['total'] == 3
    assert first['notas']['tem_mais'] and first['pagamentos']['tem_mais']
    assert first['notas']['itens'][0]['valor_original'] == 300 and second['notas']['itens'][0]['valor_original'] == 200
    assert public(c, issued['token'], notas_limit=101).status_code == 422
    assert public(c, issued['token'], pagamentos_offset=-1).status_code == 422


@pytest.mark.parametrize('body', [{'relacao': 'ambos'}, {'destinatario': ' '}, {'validade_dias': 0}, {'validade_dias': 31}, {'validade_dias': True}, {'token_hash': 'forjado'}])
def test_emissao_strict_sem_gravar_lote_invalido(administracao_api, body):
    from app.models import CompartilhamentoExtrato
    c, h, sessions, _ = administracao_api
    pid = person(c, h)
    r = c.post(f'/extratos/{pid}/compartilhamentos', headers=h['admin'], json={'relacao': 'cliente', 'destinatario': 'Pessoa autorizada', 'validade_dias': 7, **body})
    assert r.status_code == 422
    with sessions() as db:
        assert db.query(CompartilhamentoExtrato).count() == 0


def test_headers_anti_cache_indexacao_referrer_sucesso_e_erro(administracao_api):
    c, h, _, _ = administracao_api
    token = issue(c, h, person(c, h))['token']
    for r in (public(c, token), public(c, 'x'*43), public(c, token, pessoa_id=999), public(c, token, notas_limit=101)):
        assert 'no-store' in r.headers['cache-control'] and 'private' in r.headers['cache-control']
        assert r.headers['referrer-policy'] == 'no-referrer'
        assert r.headers['x-content-type-options'] == 'nosniff'
        assert 'noindex' in r.headers['x-robots-tag']


def test_relacao_incompativel_e_cadastro_inativo_rejeitam_emissao(administracao_api):
    c, h, sessions, _ = administracao_api
    pid = person(c, h, tipo='cliente')
    assert c.post(f'/extratos/{pid}/compartilhamentos', headers=h['admin'], json={'relacao': 'fornecedor', 'destinatario': 'Pessoa'}).status_code == 422
    with sessions() as db:
        db.get(Pessoa, pid).ativo = False
        db.commit()
    assert c.post(f'/extratos/{pid}/compartilhamentos', headers=h['admin'], json={'relacao': 'cliente', 'destinatario': 'Pessoa'}).status_code == 422


def test_mudanca_papel_cadastro_bloqueia_vinculo_antigo(administracao_api):
    c, h, sessions, _ = administracao_api
    pid = person(c, h)
    issued = issue(c, h, pid, 'fornecedor')
    with sessions() as db:
        db.get(Pessoa, pid).tipo = 'cliente'
        db.commit()
    assert public(c, issued['token']).status_code == 404


def test_cancelados_preservam_historico_excluidos_dos_totais(administracao_api):
    from app.models import Pagamento, NotaObrigacao
    c, h, sessions, _ = administracao_api
    pid, other = person(c, h), person(c, h)
    active, cancelled = note(c, h, pid, value=100), note(c, h, pid, value=200)
    p = payment(c, h, cliente_id=pid, fornecedor_id=other, valor=300)
    with sessions() as db:
        db.get(NotaObrigacao, cancelled['id']).cancelada = True
        db.get(Pagamento, p['id']).cancelado = True
        db.commit()
    out = public(c, issue(c, h, pid)['token']).json()
    assert set(out['totais_globais']) == {'notas', 'pagamentos'}
    assert out['totais_globais']['notas']['valor_original'] == 100
    assert out['totais_globais']['pagamentos']['valor_elegivel'] == 0
    assert out['totais_globais']['pagamentos']['saldo_disponivel'] == 0
    assert out['notas']['total'] == 2 and out['pagamentos']['total'] == 1
    assert any(n['status'] == 'cancelado' for n in out['notas']['itens'])
    assert out['pagamentos']['itens'][0]['status'] == 'cancelado'


def test_offsets_limitados_e_listagem_por_relacao(administracao_api):
    c, h, _, _ = administracao_api
    pid = person(c, h)
    cli, forn = issue(c, h, pid), issue(c, h, pid, 'fornecedor')
    listed = c.get(f'/extratos/{pid}/compartilhamentos', headers=h['admin'], params={'relacao': 'fornecedor', 'limit': 1}).json()
    assert listed['total'] == 1 and listed['itens'][0]['id'] == forn['id']
    assert 'token' not in json.dumps(listed)
    for params in ({'notas_offset': 100001}, {'pagamentos_offset': 100001}):
        assert public(c, cli['token'], **params).status_code == 422
    assert c.get(f'/extratos/{pid}/compartilhamentos', headers=h['admin'], params={'offset': 100001}).status_code == 422


def test_cliente_legado_representante_compartilha_mesma_relacao(administracao_api):
    c, h, sessions, _ = administracao_api
    pid = person(c, h)
    note(c, h, pid, value=123)
    with sessions() as db:
        db.get(Pessoa, pid).tipo = 'representante'
        db.commit()
    issued = issue(c, h, pid, 'cliente')
    r = public(c, issued['token'])
    assert r.status_code == 200 and r.json()['totais_globais']['notas']['saldo_aberto'] == 123
    assert c.post(f'/extratos/{pid}/compartilhamentos', headers=h['admin'], json={'relacao': 'fornecedor', 'destinatario': 'Pessoa'}).status_code == 422
    with sessions() as db:
        db.get(Pessoa, pid).tipo = 'fornecedor'
        db.commit()
    assert public(c, issued['token']).status_code == 404
