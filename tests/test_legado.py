"""Classificação do legado em banco sintético: evidência sem conversão financeira."""
from datetime import date
import pytest
from tests.test_administracao import administracao_api
from app.models import Base, Pessoa, Movimentacao, Lancamento, Projecao, Conciliacao, Estorno


@pytest.fixture
def legado_api(administracao_api):
    c, h, sessions, users = administracao_api
    with sessions() as db:
        cliente = Pessoa(nome='Cliente com evidência', tipo='representante', ativo=True)
        fornecedor = Pessoa(nome='Fornecedor com evidência', tipo='fornecedor', ativo=True)
        db.add_all([cliente, fornecedor]); db.flush()
        pix = Movimentacao(codigo='PIX-TESTE', data_pix=date(2026, 1, 1), valor=500,
            saldo_disponivel=300, representante_id=cliente.id, fornecedor_id=fornecedor.id,
            link_token='SEGREDO-PIX-NAO-EXIBIR', comprovante_path='/privado/comprovante.pdf')
        desconhecido = Movimentacao(codigo='PIX-SEM-TITULAR', data_pix=date(2026, 1, 1),
            valor=70, saldo_disponivel=70, remetente='Nome declarado não prova identidade')
        debito = Lancamento(tipo='debito', valor=400, saldo_aberto=200, data=date(2026, 1, 1),
            representante_id=cliente.id, fornecedor_id=fornecedor.id)
        credito = Lancamento(tipo='credito', valor=90, saldo_aberto=90, data=date(2026, 1, 1),
            representante_id=cliente.id)
        projecao = Projecao(representante_id=cliente.id, fornecedor_id=fornecedor.id,
            valor_projetado=600, valor_conciliado=0)
        db.add_all([pix, desconhecido, debito, credito, projecao]); db.flush()
        conciliacao = Conciliacao(movimentacao_id=pix.id, alvo_tipo='lancamento',
            alvo_id=debito.id, valor=200, usuario_id=users['admin'])
        db.add(conciliacao); db.flush()
        ids = {name: obj.id for name, obj in {'cliente': cliente, 'fornecedor': fornecedor,
            'pix': pix, 'desconhecido': desconhecido, 'debito': debito, 'credito': credito,
            'projecao': projecao, 'conciliacao': conciliacao}.items()}
        db.commit()
    return c, h, sessions, ids


def snapshot(sessions, financial_only=False):
    with sessions() as db:
        return {t.name: [tuple(r) for r in db.execute(t.select().order_by(*t.primary_key.columns))]
            for t in Base.metadata.sorted_tables
            if not financial_only or not (t.name.startswith('legado_') or t.name == 'audit_logs')}


def inventory(c, h, fonte='movimentacao', **params):
    response = c.get('/legado/inventario', headers=h['admin'], params={'fonte': fonte, **params})
    assert response.status_code == 200, response.text
    return response.json()


def item(c, h, fonte, ident, **changes):
    row = next(r for r in inventory(c, h, fonte)['itens'] if r['fonte_id'] == ident)
    return {'fonte': fonte, 'fonte_id': ident, 'snapshot_hash': row['snapshot_hash'],
        'decisao': 'manter_legado', 'evidencia': 'Origem conferida no registro sintético', **changes}


def preview(c, h, items):
    r = c.post('/legado/previa', headers=h['admin'], json={'itens': items})
    assert r.status_code == 200, r.text
    return r.json()


def confirm(c, h, items, key='lote-teste-001', **changes):
    before = preview(c, h, items)
    return c.post('/legado/classificacoes', headers=h['admin'], json={
        'itens': items, 'hash_previa': before['hash_previa'], 'chave_idempotencia': key, **changes})


def test_inventario_previa_classificacao_preservam_todos_registros_financeiros(legado_api):
    c, h, sessions, ids = legado_api
    before = snapshot(sessions, True)
    for fonte in ('movimentacao', 'lancamento', 'projecao', 'conciliacao', 'estorno', 'abatimento_documental'):
        out = inventory(c, h, fonte)
        assert out['total'] >= 0
        assert 'SEGREDO-PIX-NAO-EXIBIR' not in str(out)
        assert '/privado/comprovante.pdf' not in str(out)
    batch = [item(c, h, 'movimentacao', ids['pix'])]
    out = preview(c, h, batch)
    assert out['conversao_habilitada'] is False and out['impacto_financeiro'] == 'nenhum'
    assert snapshot(sessions, True) == before
    response = confirm(c, h, batch)
    assert response.status_code in (200, 201), response.text
    assert snapshot(sessions, True) == before


@pytest.mark.parametrize('role', ['consulta', 'operador'])
def test_leitura_permitida_mas_confirmacao_negada(legado_api, role):
    c, h, sessions, ids = legado_api
    batch = [item(c, h, 'movimentacao', ids['pix'])]
    out = preview(c, h, batch)
    assert c.get('/legado/inventario', headers=h[role], params={'fonte': 'movimentacao'}).status_code == 200
    before = snapshot(sessions)
    assert c.post('/legado/classificacoes', headers=h[role], json={'itens': batch,
        'hash_previa': out['hash_previa'], 'chave_idempotencia': 'tentativa-perfil'}).status_code == 403
    assert snapshot(sessions) == before


@pytest.mark.parametrize('params', [{'limit': 101}, {'limit': 0}, {'offset': -1}, {'offset': 100001}, {'fonte': 'pessoas'}, {'fonte': '../../users'}])
def test_paginacao_e_fontes_invalidas_rejeitadas(legado_api, params):
    c, h, sessions, _ = legado_api
    before = snapshot(sessions)
    assert c.get('/legado/inventario', headers=h['admin'], params=params).status_code == 422
    assert snapshot(sessions) == before


def test_repeticao_lote_nao_duplica_e_chave_divergente_rejeita(legado_api):
    c, h, sessions, ids = legado_api
    batch = [item(c, h, 'movimentacao', ids['pix'])]
    out = preview(c, h, batch)
    payload = {'itens': batch, 'hash_previa': out['hash_previa'], 'chave_idempotencia': 'repeticao-lote-001'}
    changed = {**batch[0], 'evidencia': 'Documento diferente exige outra decisão'}
    out2 = preview(c, h, [changed])
    first = c.post('/legado/classificacoes', headers=h['admin'], json=payload)
    assert first.status_code in (200, 201), first.text
    before = snapshot(sessions)
    second = c.post('/legado/classificacoes', headers=h['admin'], json=payload)
    assert second.status_code in (200, 201), second.text
    assert snapshot(sessions) == before
    divergent = c.post('/legado/classificacoes', headers=h['admin'], json={**payload,
        'itens': [changed], 'hash_previa': out2['hash_previa']})
    assert divergent.status_code == 409, divergent.text
    assert snapshot(sessions) == before


def test_snapshot_alterado_e_hash_previa_forjado_rejeitados(legado_api):
    c, h, sessions, ids = legado_api
    batch = [item(c, h, 'movimentacao', ids['pix'])]
    out = preview(c, h, batch)
    assert c.post('/legado/classificacoes', headers=h['admin'], json={
        'itens': batch, 'hash_previa': '0' * 64, 'chave_idempotencia': 'hash-forjado-001'}).status_code == 409
    with sessions() as db:
        db.get(Movimentacao, ids['pix']).saldo_disponivel = 299
        db.commit()
    before = snapshot(sessions)
    stale = c.post('/legado/classificacoes', headers=h['admin'], json={
        'itens': batch, 'hash_previa': out['hash_previa'], 'chave_idempotencia': 'snapshot-antigo-001'})
    assert stale.status_code == 409, stale.text
    assert snapshot(sessions) == before


def test_fonte_repetida_e_identificadores_maliciosos_nao_persistem(legado_api):
    c, h, sessions, ids = legado_api
    row = item(c, h, 'movimentacao', ids['pix'])
    before = snapshot(sessions)
    duplicate = c.post('/legado/previa', headers=h['admin'], json={'itens': [row, row]})
    assert duplicate.status_code == 422, duplicate.text
    for changes in ({'fonte_id': -1}, {'fonte_id': True}, {'fonte_id': '1 OR 1=1'}, {'fonte': 'users'}, {'pessoa_id': 999999, 'relacao': 'cliente'}):
        r = c.post('/legado/previa', headers=h['admin'], json={'itens': [{**row, **changes}]})
        assert r.status_code in (404, 409, 422), r.text
    assert snapshot(sessions) == before


def test_conversao_financeira_nao_exposta(legado_api):
    c, h, sessions, _ = legado_api
    before = snapshot(sessions)
    for path in ('/legado/converter', '/legado/migrar', '/legado/consumir'):
        assert c.post(path, headers=h['admin'], json={}).status_code in (404, 405)
    assert snapshot(sessions) == before


def test_snapshot_detecta_alteracao_da_conciliacao_filha(legado_api):
    c, h, sessions, ids = legado_api
    batch = [item(c, h, 'movimentacao', ids['pix'])]
    out = preview(c, h, batch)
    with sessions() as db:
        db.get(Conciliacao, ids['conciliacao']).valor = 199
        db.commit()
    before = snapshot(sessions)
    r = c.post('/legado/classificacoes', headers=h['admin'], json={'itens': batch,
        'hash_previa': out['hash_previa'], 'chave_idempotencia': 'filho-alterado-001'})
    assert r.status_code == 409, r.text
    assert snapshot(sessions) == before


def test_previa_sem_autenticacao_e_sem_direito_financeiro(legado_api):
    c, h, sessions, ids = legado_api
    row = item(c, h, 'movimentacao', ids['pix'])
    before = snapshot(sessions)
    assert c.get('/legado/inventario', params={'fonte': 'movimentacao'}).status_code == 401
    assert c.post('/legado/previa', json={'itens': [row]}).status_code == 401
    for role in ('consulta', 'operador'):
        assert c.post('/legado/previa', headers=h[role], json={'itens': [row]}).status_code == 403
    assert snapshot(sessions) == before


@pytest.mark.parametrize('changes', [{'pessoa_id': 999999, 'relacao': 'cliente'}, {'pessoa_id': None, 'relacao': 'cliente'}, {'decisao': 'converter'}, {'snapshot_hash': 'invalido'}])
def test_previa_invalida_nao_escreve(legado_api, changes):
    c, h, sessions, ids = legado_api
    row = item(c, h, 'movimentacao', ids['pix'], **changes)
    before = snapshot(sessions)
    r = c.post('/legado/previa', headers=h['admin'], json={'itens': [row]})
    assert r.status_code in (404, 409, 422), r.text
    assert snapshot(sessions) == before


def test_desconhecido_fica_pendente_sem_inferir_pelo_nome(legado_api):
    c, h, sessions, ids = legado_api
    row = next(r for r in inventory(c, h)['itens'] if r['fonte_id'] == ids['desconhecido'])
    assert row['relacoes_conhecidas'] == []
    assert 'titular_relacao_nao_comprovados' in row['pendencias']
    bad = item(c, h, 'movimentacao', ids['desconhecido'], decisao='avaliar_transicao')
    before = snapshot(sessions)
    assert c.post('/legado/previa', headers=h['admin'], json={'itens': [bad]}).status_code == 422
    guessed = {**bad, 'decisao': 'pendente', 'pessoa_id': ids['cliente'], 'relacao': 'cliente'}
    assert c.post('/legado/previa', headers=h['admin'], json={'itens': [guessed]}).status_code == 422
    assert snapshot(sessions) == before
    result = confirm(c, h, [{**bad, 'decisao': 'pendente'}], key='origem-desconhecida-001')
    assert result.status_code == 201, result.text
    assert result.json()['itens'][0]['decisao'] == 'pendente'


def test_credito_e_projecao_nao_provam_obrigacao_ou_credito_novo(legado_api):
    c, h, sessions, ids = legado_api
    credit = next(r for r in inventory(c, h, 'lancamento')['itens'] if r['fonte_id'] == ids['credito'])
    projection = inventory(c, h, 'projecao')['itens'][0]
    assert 'origem_credito_nao_comprovada' in credit['pendencias']
    assert 'projecao_nao_e_obrigacao_documental' in projection['pendencias']
    before = snapshot(sessions, True)
    batch = [item(c, h, 'lancamento', ids['credito'], decisao='avaliar_transicao'),
             item(c, h, 'projecao', ids['projecao'], decisao='avaliar_transicao')]
    result = confirm(c, h, batch, key='creditos-projecoes-001')
    assert result.status_code == 201, result.text
    assert result.json()['conversao_habilitada'] is False
    assert snapshot(sessions, True) == before


def test_origem_classificada_em_outro_lote_reverte_lote_inteiro(legado_api):
    c, h, sessions, ids = legado_api
    pix = item(c, h, 'movimentacao', ids['pix'])
    debit = item(c, h, 'lancamento', ids['debito'])
    prior = preview(c, h, [pix, debit])
    assert confirm(c, h, [pix], key='primeiro-lote-001').status_code == 201
    before = snapshot(sessions)
    r = c.post('/legado/classificacoes', headers=h['admin'], json={'itens': [pix, debit],
        'hash_previa': prior['hash_previa'], 'chave_idempotencia': 'segundo-lote-001'})
    assert r.status_code == 409, r.text
    assert snapshot(sessions) == before
    untouched = next(r for r in inventory(c, h, 'lancamento')['itens'] if r['fonte_id'] == ids['debito'])
    assert untouched['classificacao'] is None


def test_abatimento_documental_vinculo_sem_inferir_evento_e_snapshot_nota(legado_api):
    from tests.test_notas import note, abat
    from app.models import NotaObrigacao
    c, h, sessions, ids = legado_api
    n = note(c, h, ids['cliente'])
    a = abat(c, h, n['id'])
    assert a.status_code == 201, a.text
    row = inventory(c, h, 'abatimento_documental')['itens'][0]
    assert row['vinculos']['nota_id'] == n['id']
    assert row['relacoes_conhecidas'] == [{'pessoa_id': ids['cliente'], 'relacao': 'cliente'}]
    assert 'evento_financeiro_origem_nao_comprovado' in row['pendencias']
    batch = [item(c, h, 'abatimento_documental', a.json()['id'])]
    out = preview(c, h, batch)
    with sessions() as db:
        db.get(NotaObrigacao, n['id']).valor_original = 110
        db.commit()
    before = snapshot(sessions)
    r = c.post('/legado/classificacoes', headers=h['admin'], json={'itens': batch,
        'hash_previa': out['hash_previa'], 'chave_idempotencia': 'nota-alterada-001'})
    assert r.status_code == 409, r.text
    assert snapshot(sessions) == before


def test_estorno_e_divergencia_saldo_explicitam_pendencias(legado_api):
    c, h, sessions, ids = legado_api
    with sessions() as db:
        db.add(Estorno(conciliacao_id=ids['conciliacao'], motivo='Motivo livre sensível', usuario_id=1))
        db.commit()
    out = inventory(c, h, 'estorno')
    assert out['total'] == 1
    assert 'estorno_divergente' in out['itens'][0]['pendencias']
    assert 'Motivo livre sensível' not in str(out)
    before = snapshot(sessions)
    wrong = item(c, h, 'estorno', out['itens'][0]['fonte_id'], decisao='avaliar_transicao')
    assert c.post('/legado/previa', headers=h['admin'], json={'itens': [wrong]}).status_code == 422
    assert snapshot(sessions) == before


def test_pagina_nao_perde_total_nem_repete_origem(legado_api):
    c, h, sessions, _ = legado_api
    before = snapshot(sessions)
    first = inventory(c, h, limit=1, offset=0)
    second = inventory(c, h, limit=1, offset=1)
    beyond = inventory(c, h, limit=1, offset=2)
    assert first['total'] == second['total'] == beyond['total'] == 2
    assert first['tem_mais'] is True and second['tem_mais'] is False
    assert first['itens'][0]['fonte_id'] != second['itens'][0]['fonte_id']
    assert beyond['itens'] == []
    assert snapshot(sessions) == before


def test_recibo_repetido_permanece_imutavel_apos_origem_mudar(legado_api):
    c, h, sessions, ids = legado_api
    batch = [item(c, h, 'movimentacao', ids['pix'])]
    out = preview(c, h, batch)
    payload = {'itens': batch, 'hash_previa': out['hash_previa'], 'chave_idempotencia': 'recibo-historico-001'}
    first = c.post('/legado/classificacoes', headers=h['financeiro'], json=payload)
    assert first.status_code == 201, first.text
    with sessions() as db:
        db.get(Movimentacao, ids['pix']).saldo_disponivel = 298
        db.commit()
    before = snapshot(sessions)
    replay = c.post('/legado/classificacoes', headers=h['financeiro'], json=payload)
    assert replay.status_code == 200, replay.text
    assert replay.json()['repetido'] is True
    assert replay.json()['id'] == first.json()['id']
    assert replay.json()['itens'] == first.json()['itens']
    assert snapshot(sessions) == before


@pytest.mark.parametrize('kind', ['empty', 'large', 'extra_field', 'invalid_key'])
def test_contrato_lote_recusa_tamanho_e_campos_indevidos(legado_api, kind):
    c, h, sessions, ids = legado_api
    row = item(c, h, 'movimentacao', ids['pix'])
    body = {'itens': [row]}
    path = '/legado/previa'
    if kind == 'empty':
        body['itens'] = []
    elif kind == 'large':
        body['itens'] = [{**row, 'fonte_id': x} for x in range(1, 102)]
    elif kind == 'extra_field':
        body['itens'] = [{**row, 'valor_credito': 1000}]
    else:
        path = '/legado/classificacoes'
        body.update(hash_previa=preview(c, h, [row])['hash_previa'], chave_idempotencia='../../../secret')
    before = snapshot(sessions)
    assert c.post(path, headers=h['admin'], json=body).status_code == 422
    assert snapshot(sessions) == before


def test_recibos_privados_e_perfil_atual_do_token(legado_api):
    from app.models import User
    c, h, sessions, ids = legado_api
    assert confirm(c, h, [item(c, h, 'movimentacao', ids['pix'])], key='recibo-privado-001').status_code == 201
    for role in ('consulta', 'operador'):
        assert c.get('/legado/classificacoes', headers=h[role]).status_code == 403
    for role in ('admin', 'financeiro'):
        r = c.get('/legado/classificacoes', headers=h[role], params={'limit': 1})
        assert r.status_code == 200 and r.json()['total'] == 1
        assert 'SEGREDO-PIX-NAO-EXIBIR' not in r.text and '/privado/comprovante.pdf' not in r.text
    with sessions() as db:
        db.query(User).filter_by(perfil='financeiro').one().perfil = 'consulta'
        db.commit()
    assert c.get('/legado/classificacoes', headers=h['financeiro']).status_code == 403


@pytest.mark.parametrize('same_key', [False, True])
def test_confirmacoes_concorrentes_nao_duplicam_nem_deixam_recibo_orfao(legado_api, same_key):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.models import LegadoLote, LegadoClassificacao
    c, h, sessions, ids = legado_api
    row = item(c, h, 'movimentacao', ids['pix'])
    out = preview(c, h, [row])
    before = snapshot(sessions, True)
    barrier = Barrier(2)
    def run(index):
        barrier.wait(timeout=10)
        return c.post('/legado/classificacoes', headers=h['admin'], json={'itens': [row],
            'hash_previa': out['hash_previa'], 'chave_idempotencia': f'corrida-lote-{0 if same_key else index:03}'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(run, (0, 1)))
    expected = [200, 201] if same_key else [201, 409]
    assert sorted(r.status_code for r in responses) == expected, [(r.status_code, r.text) for r in responses]
    with sessions() as db:
        assert db.query(LegadoLote).count() == 1
        assert db.query(LegadoClassificacao).count() == 1
        assert db.query(LegadoClassificacao).one().lote_id == db.query(LegadoLote).one().id
    assert snapshot(sessions, True) == before


@pytest.mark.parametrize('fonte,key,field,value', [('lancamento', 'debito', 'saldo_aberto', 399), ('projecao', 'projecao', 'valor_conciliado', 601)])
def test_saldo_alvo_inconsistente_deve_permanecer_pendente(legado_api, fonte, key, field, value):
    c, h, sessions, ids = legado_api
    with sessions() as db:
        model = Lancamento if fonte == 'lancamento' else Projecao
        setattr(db.get(model, ids[key]), field, value)
        db.commit()
    row = next(r for r in inventory(c, h, fonte)['itens'] if r['fonte_id'] == ids[key])
    assert 'saldo_alvo_divergente' in row['pendencias']
    before = snapshot(sessions)
    bad = item(c, h, fonte, ids[key], decisao='avaliar_transicao')
    assert c.post('/legado/previa', headers=h['admin'], json={'itens': [bad]}).status_code == 422
    assert snapshot(sessions) == before
    good = {**bad, 'decisao': 'pendente'}
    assert confirm(c, h, [good], key='saldo-inconsistente-001').status_code == 201


def test_titular_conciliacao_divergente_nao_inventa_intersecao(legado_api):
    c, h, sessions, ids = legado_api
    with sessions() as db:
        outro = Pessoa(nome='Outro cliente', tipo='representante', ativo=True)
        db.add(outro); db.flush()
        db.get(Lancamento, ids['debito']).representante_id = outro.id
        db.commit()
    row = inventory(c, h, 'conciliacao')['itens'][0]
    assert 'titulares_conciliacao_divergentes' in row['pendencias']
    before = snapshot(sessions)
    bad = item(c, h, 'conciliacao', ids['conciliacao'], decisao='avaliar_transicao')
    assert c.post('/legado/previa', headers=h['admin'], json={'itens': [bad]}).status_code == 422
    assert snapshot(sessions) == before
