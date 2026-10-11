"""Alertas informativos e links privados com destino fixado preservado."""
from datetime import timedelta
import pytest
from tests.test_pagamentos import pagamentos_api, person, note
from app.cadastros import hoje
from app.models import PessoaChavePix, LinkPagamento, Pessoa, Movimentacao


def key(c, h, pid, name, **extra):
    r = c.post(f'/pessoas/{pid}/chaves-pix', headers=h['admin'], json={'chave': name, **extra})
    assert r.status_code == 201, r.text
    return r.json()['id']


def alerts(c, h, **params):
    r = c.get('/cadastros/alertas', headers=h['admin'], params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_divida_fornecedor_exige_principal_valida_sem_fallback_inativo(pagamentos_api):
    c, h, _ = pagamentos_api
    pid, cli = person(c, h), person(c, h)
    note(c, h, pid, 'fornecedor', 150)
    note(c, h, cli, 'cliente', 100)
    out = alerts(c, h, tipo='divida_sem_chave')
    assert out['total'] == 1 and out['itens'][0]['pessoa_id'] == pid
    assert out['itens'][0]['divida_aberta'] == 150
    kid = key(c, h, pid, 'chave válida', principal=True)
    assert alerts(c, h, tipo='divida_sem_chave')['total'] == 0
    assert c.delete(f'/pessoas/{pid}/chaves-pix/{kid}', headers=h['admin']).status_code == 200
    assert alerts(c, h, tipo='divida_sem_chave')['total'] == 1


def test_chaves_expiradas_trinta_dias_paginadas_sem_writes(pagamentos_api):
    c, h, sessions = pagamentos_api
    ids = []
    for delta in (-1, 0, 30, 31):
        pid = person(c, h)
        ids.append(key(c, h, pid, f'key{delta}', categoria='temporaria', principal=True,
            validade=(hoje() + timedelta(days=delta)).isoformat()))
    with sessions() as db:
        before = [(k.id, k.chave, k.ativo, k.principal) for k in db.query(PessoaChavePix).order_by(PessoaChavePix.id)]
    expired = alerts(c, h, tipo='chave_expirada')
    assert expired['total'] == 1 and expired['itens'][0]['chave_id'] == ids[0]
    soon = alerts(c, h, tipo='chave_a_vencer')
    assert {a['chave_id'] for a in soon['itens']} == set(ids[1:3])
    first = alerts(c, h, tipo='chave_a_vencer', limit=1)
    second = alerts(c, h, tipo='chave_a_vencer', limit=1, offset=1)
    assert first['tem_mais'] is True and second['tem_mais'] is False
    assert first['itens'][0]['id'] != second['itens'][0]['id']
    with sessions() as db:
        assert [(k.id, k.chave, k.ativo, k.principal) for k in db.query(PessoaChavePix).order_by(PessoaChavePix.id)] == before


def test_link_nova_principal_nao_retarget_e_bloqueado_original(pagamentos_api):
    c, h, sessions = pagamentos_api
    pid = person(c, h)
    original = key(c, h, pid, 'DESTINO-ORIGINAL', principal=True, titular='Titular original')
    r = c.post('/links', headers=h['admin'], json={'representante_id': pid, 'fornecedor_id': pid})
    assert r.status_code == 201, r.text
    lid = r.json()['id']
    key(c, h, pid, 'DESTINO-NOVO', principal=True, titular='Titular novo')
    url = f'/cadastros/{pid}/links'
    r = c.get(url, headers=h['consulta'], params={'status': 'semuso'})
    assert r.status_code == 200, r.text
    item = r.json()['itens'][0]
    assert item['id'] == lid and item['chave_destino'] == 'DESTINO-ORIGINAL'
    assert item['destino_fixado'] is True and item['destino_bloqueado'] is False
    assert c.delete(f'/pessoas/{pid}/chaves-pix/{original}', headers=h['admin']).status_code == 200
    r = c.get(url + '?status=bloqueado_destino', headers=h['admin'])
    assert r.status_code == 200 and r.json()['itens'][0]['chave_destino'] == 'DESTINO-ORIGINAL'
    with sessions() as db:
        l = db.get(LinkPagamento, lid)
        assert l.ativo is True and l.chave_snapshot == 'DESTINO-ORIGINAL'
    assert c.get(url).status_code == 401


@pytest.mark.parametrize('perfil', ['admin', 'financeiro', 'operador', 'consulta'])
def test_alertas_links_privados_todos_perfis(pagamentos_api, perfil):
    c, h, _ = pagamentos_api
    pid = person(c, h)
    for url in ('/cadastros/alertas', f'/cadastros/{pid}/links'):
        assert c.get(url, headers=h[perfil]).status_code == 200
        assert c.get(url).status_code == 401
    assert c.get('/cadastros/alertas?tipo=inventado', headers=h[perfil]).status_code == 422
    assert c.get(f'/cadastros/{pid}/links?status=inventado', headers=h[perfil]).status_code == 422


def test_fornecedor_inativo_com_divida_e_chave_nao_e_destino_valido(pagamentos_api):
    c, h, sessions = pagamentos_api
    pid = person(c, h)
    note(c, h, pid, 'fornecedor', 75)
    key(c, h, pid, 'principal', principal=True)
    assert alerts(c, h, tipo='divida_sem_chave')['total'] == 0
    with sessions() as db:
        db.get(Pessoa, pid).ativo = False
        db.commit()
    out = alerts(c, h, tipo='divida_sem_chave')
    assert out['total'] == 1 and out['itens'][0]['divida_aberta'] == 75


def test_links_usados_revogados_filtrados_antes_pagina_nao_reescrevem(pagamentos_api):
    c, h, sessions = pagamentos_api
    pid, other = person(c, h), person(c, h)
    key(c, h, pid, 'destino', principal=True)
    links = [c.post('/links', headers=h['admin'], json={'representante_id': pid, 'fornecedor_id': pid}).json() for _ in range(3)]
    with sessions() as db:
        db.add(Movimentacao(codigo='PIX-SYNTH-LINK', link_token=links[0]['token'], data_pix=hoje(),
            valor=1, saldo_disponivel=0, status='cancelada'))
        db.get(LinkPagamento, links[1]['id']).ativo = False
        db.commit()
        before = [(l.id, l.ativo, l.chave_snapshot) for l in db.query(LinkPagamento).order_by(LinkPagamento.id)]
    url = f'/cadastros/{pid}/links'
    out = c.get(url + '?status=usado&limit=1', headers=h['admin']).json()
    assert out['total'] == 1 and out['itens'][0]['id'] == links[0]['id']
    assert out['itens'][0]['movimentacoes_quantidade'] == 1
    out = c.get(url + '?status=revogado&limit=1', headers=h['admin']).json()
    assert out['total'] == 1 and out['itens'][0]['id'] == links[1]['id']
    assert c.get(f'/cadastros/{other}/links', headers=h['admin']).json()['total'] == 0
    with sessions() as db:
        assert [(l.id, l.ativo, l.chave_snapshot) for l in db.query(LinkPagamento).order_by(LinkPagamento.id)] == before
