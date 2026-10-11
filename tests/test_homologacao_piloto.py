"""Fluxos combinados do piloto com resolução real dos bancos sintéticos."""
import pytest
from tests.test_ambientes import ambiente_api, provisionar, selecionar
from tests.test_portal_fornecedor import portal, bind
from tests.test_pagamentos import person, note, payment, apply, balance, detail
from tests.test_acertos import draft, execute, payload
from tests.test_creditos import credit, fetch, undo


@pytest.mark.parametrize('trajeto', ['cliente_fornecedor', 'cliente_loja'])
def test_trajetos_parciais_sobras_declaracao_estorno_sem_credito(portal, trajeto):
    c, headers, _, _, stores = portal
    store = stores[2]
    h = {'admin': store['admin']}
    cliente, fornecedor = store['people'][:2]
    assert bind(c, headers[2], 2, 4, fornecedor).status_code == 200
    venda, compra = note(c, h, cliente, value=500), note(c, h, fornecedor, 'fornecedor', 400)
    entrada = payment(c, h, tipo=trajeto, cliente_id=cliente, valor=180,
                      **({'fornecedor_id': fornecedor} if trajeto == 'cliente_fornecedor' else {}))
    assert apply(c, h, entrada['id'], venda['id'], valor=100).status_code == 201
    recebido = entrada if trajeto == 'cliente_fornecedor' else payment(c, h, tipo='repasse_fornecedor', fornecedor_id=fornecedor, pagamento_origem_id=entrada['id'], valor=150)
    path = f"/organizacoes/2/portal-fornecedor/pagamentos/{recebido['id']}/confirmar-recebimento"
    body = {'referencia': 'Conferência humana piloto', 'observacao': 'Conferido externamente'}
    before = detail(c, h, recebido['id'])
    declaration = c.post(path, headers=headers[4], json=body)
    assert declaration.status_code == 200, declaration.text
    assert detail(c, h, recebido['id']) == before
    application = apply(c, h, recebido['id'], compra['id'], 'fornecedor', valor=80)
    assert application.status_code == 201, application.text
    assert balance(c, h, venda['id']) == 400 and balance(c, h, compra['id']) == 320
    assert detail(c, h, entrada['id'])['orcamentos']['cliente']['saldo_disponivel'] == 80
    assert detail(c, h, recebido['id'])['orcamentos']['fornecedor']['saldo_disponivel'] == recebido['valor'] - 80
    assert c.get('/creditos', headers=h['admin']).json() == []
    shown = c.get('/organizacoes/2/portal-fornecedor', headers=headers[4]).json()
    assert next(p for p in shown['pagamentos'] if p['id'] == recebido['id'])['recebimento'] == declaration.json()
    reversal = c.post(f"/pagamentos/{recebido['id']}/aplicacoes/{application.json()['id']}/estornar", headers=h['admin'], json=undo())
    assert reversal.status_code == 200, reversal.text
    assert balance(c, h, compra['id']) == 400 and balance(c, h, venda['id']) == 400
    assert detail(c, h, recebido['id'])['orcamentos']['fornecedor']['saldo_disponivel'] == recebido['valor']
    assert c.post(path, headers=headers[4], json=body).json() == declaration.json()


def test_credito_explicito_acerto_misto_estorno_fontes_isoladas(ambiente_api):
    c, headers, _, _ = ambiente_api
    a, b = [provisionar(c, headers[2], org) for org in (2, 3)]
    h = {'admin': a}
    cliente, fornecedor = person(c, h), person(c, h)
    origem_nota = note(c, h, cliente, value=1000)
    origem = payment(c, h, cliente_id=cliente, fornecedor_id=fornecedor, valor=1100)
    inicial = draft(c, h, payload(cliente, [(origem['id'], origem_nota['id'], 1000)]))
    assert execute(c, h, inicial['id']).status_code == 200
    assert c.get('/creditos', headers=a).json() == []
    assert detail(c, h, origem['id'])['orcamentos']['cliente']['saldo_disponivel'] == 100
    credito = credit(c, h, origem, inicial)
    destino = note(c, h, cliente, value=500)
    novo = payment(c, h, cliente_id=cliente, fornecedor_id=fornecedor, valor=200)
    body = payload(cliente, [(novo['id'], destino['id'], 140)], data='2020-01-05')
    body['itens'].append({'credito_id': credito['id'], 'nota_id': destino['id'], 'valor': 60})
    lote = draft(c, h, body)
    assert execute(c, h, lote['id']).status_code == 200
    assert balance(c, h, destino['id']) == 300 and fetch(c, h, credito['id'])['saldo_disponivel'] == 40
    assert detail(c, h, novo['id'])['orcamentos']['cliente']['saldo_disponivel'] == 60
    assert c.post(f"/acertos/{lote['id']}/estornar", headers=a, json=undo()).status_code == 200
    assert balance(c, h, destino['id']) == 500 and balance(c, h, origem_nota['id']) == 0
    assert fetch(c, h, credito['id'])['saldo_disponivel'] == 100
    assert detail(c, h, novo['id'])['orcamentos']['cliente']['saldo_disponivel'] == 200
    assert detail(c, h, origem['id'])['orcamentos']['cliente']['saldo_disponivel'] == 0
    assert detail(c, h, origem['id'])['orcamentos']['fornecedor']['saldo_disponivel'] == 1100
    assert c.get('/creditos', headers=b).json() == []
    assert c.get(f"/acertos/{lote['id']}", headers=b).status_code == 404


def test_consulta_publico_anexos_revogacao_preserva_outra_loja(portal, monkeypatch):
    c, headers, _, tmp, stores = portal
    from app.routers import notas
    monkeypatch.setattr(notas, 'UPLOAD_DIR', str(tmp / 'uploads-piloto'))
    shares = {}
    for org, store in stores.items():
        admin = store['admin']
        assert bind(c, headers[2], org, 4, store['people'][1]).status_code == 200
        document = note(c, {'admin': admin}, store['people'][0], value=org * 100)
        content = f'%PDF-1.4 piloto privado loja {org}'.encode()
        attachment = c.post(f"/notas/{document['id']}/anexos", headers=admin, files={'f': ('piloto.pdf', content, 'application/pdf')})
        assert attachment.status_code == 201, attachment.text
        assert c.get(f"/notas/{document['id']}/anexos/{attachment.json()['id']}/arquivo", headers=admin).content == content
        shares[org] = c.post(f"/extratos/{store['people'][0]}/compartilhamentos", headers=admin, json={'relacao': 'cliente', 'destinatario': 'Cliente piloto', 'validade_dias': 7}).json()['token']
    consulta = selecionar(c, headers[3], 2)
    assert c.get('/notas', headers=consulta).status_code == 200
    assert c.post('/pagamentos', headers=consulta, json={}).status_code == 403
    for org in (2, 3):
        secret = {'Authorization': f'Bearer {shares[org]}'}
        shared = c.get(f'/lojas/{org}/publico/extratos', headers=secret)
        assert shared.status_code == 200 and shared.json()['notas']['itens'][0]['valor_original'] == org * 100
        assert 'piloto.pdf' not in shared.text
        assert c.get(f'/lojas/{5-org}/publico/extratos', headers=secret).status_code == 404
        assert c.get('/notas/1/anexos/1/arquivo', headers=secret).status_code in (401, 403)
    assert c.patch('/organizacoes/2/membros/3', headers=headers[2], json={'perfil': 'consulta', 'ativo': False}).status_code == 200
    assert c.get('/notas', headers=consulta).status_code == 403
    assert c.patch('/organizacoes/2/membros/4', headers=headers[2], json={'perfil': 'fornecedor', 'ativo': False}).status_code == 200
    assert c.get('/organizacoes/2/portal-fornecedor', headers=headers[4]).status_code == 403
    assert c.get('/organizacoes/3/portal-fornecedor', headers=headers[4]).status_code == 200
    assert c.get('/lojas/3/publico/extratos', headers={'Authorization': f"Bearer {shares[3]}"}).status_code == 200
