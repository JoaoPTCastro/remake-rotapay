"""Intercâmbio explícito e integral; prévias nunca persistem domínio financeiro."""
import csv
import io
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from tests.test_pagamentos import pagamentos_api, person, note
from app.models import Pessoa, NotaObrigacao, Movimentacao, Pagamento, CreditoConta


CAD = 'tipo;nome;documento;telefone;email;apelido;endereco;observacoes;prazo_dias\n'
NOT = 'documento_pessoa;relacao;numero_documento;valor_original;data_emissao;modo_vencimento;prazo_dias;vencimento;descricao\n'


def preview(c, h, kind, content, perfil='admin'):
    return c.post(f'/csv/{kind}/previa', headers=h[perfil], files={'f': ('lote.csv', content.encode('utf-8-sig'), 'text/csv')})


def imported(c, h, kind, content, token, key=None, perfil='admin', **extra):
    return c.post(f'/csv/{kind}/importar', headers=h[perfil],
        files={'f': ('lote.csv', content.encode('utf-8-sig'), 'text/csv')},
        data={'token_previa': token, 'chave_idempotencia': key or uuid4().hex, 'confirmacao': 'true', **extra})


def valid_preview(c, h, kind, content):
    r = preview(c, h, kind, content)
    assert r.status_code == 200, r.text
    assert r.json()['pode_importar'] is True, r.text
    return r.json()['token_previa']


def counts(sessions):
    with sessions() as db:
        return tuple(db.query(m).count() for m in (Pessoa, NotaObrigacao, Movimentacao, Pagamento, CreditoConta))


def test_previa_sem_escrita_importacao_idempotente_persistente(pagamentos_api):
    c, h, sessions = pagamentos_api
    body = CAD + 'cliente;Cliente CSV;12345678901;;;;;;30\n'
    before = counts(sessions)
    token = valid_preview(c, h, 'cadastros', body)
    assert counts(sessions) == before
    key = uuid4().hex
    first = imported(c, h, 'cadastros', body, token, key)
    assert first.status_code in (200, 201), first.text
    again = imported(c, h, 'cadastros', body, token, key)
    assert again.status_code in (200, 201), again.text
    assert again.json()['importacao_id'] == first.json()['importacao_id']
    assert again.json()['repetida'] is True
    assert counts(sessions) == (before[0] + 1, *before[1:])


@pytest.mark.parametrize('bad', [
    'inventado;Inválido;12345678901;;;;;;0',
    'cliente;Sem documento;;;;;;;0',
    'cliente;Documento curto;123;;;;;;0',
    'cliente;Prazo negativo;12345678901;;;;;;-1',
])
def test_lote_com_erro_nao_grava_linha_valida(pagamentos_api, bad):
    c, h, sessions = pagamentos_api
    body = CAD + 'cliente;Linha válida;98765432100;;;;;;0\n' + bad + '\n'
    before = counts(sessions)
    p = preview(c, h, 'cadastros', body)
    assert p.status_code == 200, p.text
    assert p.json()['pode_importar'] is False
    assert p.json()['resumo']['erros'] >= 1
    r = imported(c, h, 'cadastros', body, p.json()['token_previa'])
    assert r.status_code in (409, 422), r.text
    assert counts(sessions) == before


def test_documentos_normalizados_duplicados_e_conflito_existente(pagamentos_api):
    c, h, sessions = pagamentos_api
    body = CAD + 'cliente;Primeiro;123.456.789-01;;;;;;0\ncliente;Segundo;12345678901;;;;;;0\n'
    p = preview(c, h, 'cadastros', body)
    assert p.status_code == 200 and p.json()['pode_importar'] is False
    person(c, h, nome='Existente', documento='123.456.789-01')
    p = preview(c, h, 'cadastros', CAD + 'cliente;Outro nome;12345678901;;;;;;0\n')
    assert p.status_code == 200 and p.json()['pode_importar'] is False


def test_token_alterado_arquivo_usuario_e_cadastro_stale(pagamentos_api):
    c, h, sessions = pagamentos_api
    body = CAD + 'cliente;Novo CSV;12345678901;;;;;;0\n'
    token = valid_preview(c, h, 'cadastros', body)
    before = counts(sessions)
    for content, tok, perfil in ((body.replace('Novo CSV', 'Modificado'), token, 'admin'),
        (body, token + 'x', 'admin'), (body, token, 'financeiro')):
        assert imported(c, h, 'cadastros', content, tok, perfil=perfil).status_code in (409, 422)
        assert counts(sessions) == before
    person(c, h, documento='12345678901', nome='Cadastro concorrente')
    assert imported(c, h, 'cadastros', body, token).status_code in (409, 422)


def test_csv_notas_nova_obrigacao_nunca_pagamento(pagamentos_api):
    c, h, sessions = pagamentos_api
    pid = person(c, h, documento='12345678901')
    body = NOT + '12345678901;cliente;CSV-01;123,45;2020-01-01;sem_vencimento;;;Nota importada\n'
    token = valid_preview(c, h, 'notas', body)
    before = counts(sessions)
    r = imported(c, h, 'notas', body, token)
    assert r.status_code in (200, 201), r.text
    assert counts(sessions) == (before[0], before[1] + 1, *before[2:])
    n = c.get('/notas', headers=h['admin'], params={'pessoa_id': pid}).json()[0]
    assert n['valor_original'] == n['saldo_aberto'] == 123.45 and n['valor_abatido'] == 0
    p = preview(c, h, 'notas', body)
    assert p.status_code == 200 and p.json()['resumo']['ignorados'] == 1
    assert preview(c, h, 'notas', body.replace('123,45', '123,46')).json()['pode_importar'] is False


@pytest.mark.parametrize('value,date', [('NaN', '2020-01-01'), ('0', '2020-01-01'), ('1,001', '2020-01-01'), ('1,00', 'nao-data')])
def test_notas_monetario_data_invalidos(pagamentos_api, value, date):
    c, h, _ = pagamentos_api
    person(c, h, documento='12345678901')
    p = preview(c, h, 'notas', NOT + f'12345678901;cliente;INV;{value};{date};sem_vencimento;;;Inválida\n')
    assert p.status_code == 200 and p.json()['pode_importar'] is False


def test_campos_financeiros_proibidos_e_permissoes(pagamentos_api):
    c, h, sessions = pagamentos_api
    body = CAD + 'cliente;Cliente CSV;12345678901;;;;;;0\n'
    for perfil in ('operador', 'consulta'):
        assert preview(c, h, 'cadastros', body, perfil).status_code == 403
        assert imported(c, h, 'cadastros', body, 'token', perfil=perfil).status_code == 403
    assert c.post('/csv/cadastros/previa', files={'f': ('lote.csv', body)}).status_code == 401
    forbidden = body.replace('prazo_dias\n', 'prazo_dias;saldo_aberto\n').replace(';;;;;;0\n', ';;;;;;0;100\n')
    r = preview(c, h, 'cadastros', forbidden)
    assert r.status_code == 422 or (r.status_code == 200 and r.json()['pode_importar'] is False)


def test_concorrencia_documento_nao_duplica(pagamentos_api):
    c, h, sessions = pagamentos_api
    bodies = [CAD + f'cliente;Concorrente {i};12345678901;;;;;;0\n' for i in range(2)]
    tokens = [valid_preview(c, h, 'cadastros', b) for b in bodies]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pair: imported(c, h, 'cadastros', *pair), zip(bodies, tokens)))
    assert sum(r.status_code in (200, 201) for r in results) == 1, [r.text for r in results]
    with sessions() as db:
        assert db.query(Pessoa).count() == 1


def test_exports_bom_formula_safe_filtros(pagamentos_api):
    c, h, _ = pagamentos_api
    pid = person(c, h, nome='=2+3', documento='12345678901')
    person(c, h, nome='Outro', tipo='fornecedor')
    note(c, h, pid, value=123.45)
    r = c.get('/csv/exportar/cadastros?q=%3D2%2B3&tipo=ambos&ativo=true', headers=h['consulta'])
    assert r.status_code == 200, r.text
    assert r.content.startswith(b'\xef\xbb\xbf')
    rows = list(csv.DictReader(io.StringIO(r.content.decode('utf-8-sig')), delimiter=';'))
    assert len(rows) == 1 and rows[0]['nome'].startswith("'")
    r = c.get(f'/csv/exportar/notas?pessoa_id={pid}&relacao=cliente&status=aberto', headers=h['admin'])
    assert r.status_code == 200 and r.content.startswith(b'\xef\xbb\xbf')
    rows = list(csv.DictReader(io.StringIO(r.content.decode('utf-8-sig')), delimiter=';'))
    assert len(rows) == 1 and rows[0]['valor_original'] == '123,45'
    assert c.get('/csv/exportar/cadastros').status_code == 401


def test_limites_arquivo_linhas_e_confirmacao_explicita(pagamentos_api):
    c, h, sessions = pagamentos_api
    before = counts(sessions)
    oversized = preview(c, h, 'cadastros', 'x' * (1024 * 1024 + 1))
    assert oversized.status_code in (413, 422)
    lines = CAD + ''.join(f'cliente;Cliente {i};{10000000000+i};;;;;;0\n' for i in range(501))
    too_many = preview(c, h, 'cadastros', lines)
    assert too_many.status_code in (413, 422) or (too_many.status_code == 200 and not too_many.json()['pode_importar'])
    body = CAD + 'cliente;Conferir;12345678901;;;;;;0\n'
    token = valid_preview(c, h, 'cadastros', body)
    assert imported(c, h, 'cadastros', body, token, confirmacao='false').status_code == 422
    assert counts(sessions) == before


def test_documento_ambiguo_e_nota_titular_relacao_invalida(pagamentos_api):
    c, h, sessions = pagamentos_api
    person(c, h, documento='12345678901')
    with sessions() as db:
        db.add(Pessoa(nome='Legado ambíguo', tipo='ambos', documento='123.456.789-01', ativo=True))
        db.commit()
    p = preview(c, h, 'cadastros', CAD + 'cliente;Ambíguo;12345678901;;;;;;0\n')
    assert p.status_code == 200 and not p.json()['pode_importar']
    for doc, relation in (('99999999999', 'cliente'), ('12345678901', 'invalida')):
        p = preview(c, h, 'notas', NOT + f'{doc};{relation};NOTA;1,00;2020-01-01;sem_vencimento;;;Inválida\n')
        assert p.status_code == 200 and not p.json()['pode_importar']


def test_manual_documento_duplicado_e_mesmo_csv_outra_chave(pagamentos_api):
    c, h, sessions = pagamentos_api
    body = CAD + 'cliente;Identidade única;12345678901;;;;;;0\n'
    token = valid_preview(c, h, 'cadastros', body)
    first = imported(c, h, 'cadastros', body, token)
    assert first.status_code in (200, 201), first.text
    second = imported(c, h, 'cadastros', body, token)
    assert second.status_code in (200, 201) and second.json()['importacao_id'] == first.json()['importacao_id']
    duplicate = c.post('/pessoas', headers=h['admin'], json={'nome': 'Mesmo documento', 'tipo': 'cliente', 'documento': '123.456.789-01'})
    assert duplicate.status_code == 409
    other = person(c, h, documento='98765432100')
    assert c.patch(f'/pessoas/{other}', headers=h['admin'], json={'documento': '123.456.789-01'}).status_code == 409
    with sessions() as db:
        assert db.query(Pessoa).count() == 2


def test_legado_documento_ambiguo_nome_editavel_importacao_bloqueada(pagamentos_api):
    c, h, sessions = pagamentos_api
    with sessions() as db:
        rows = [Pessoa(nome=f'Legado {i}', tipo='ambos', documento=doc, ativo=True)
            for i, doc in enumerate(('12345678901', '123.456.789-01'))]
        db.add_all(rows)
        db.commit()
        pid = rows[0].id
    r = c.patch(f'/pessoas/{pid}', headers=h['admin'], json={'nome': 'Nome corrigido', 'documento': '123.456.789-01'})
    assert r.status_code == 200, r.text
    assert c.get(f'/pessoas/{pid}', headers=h['admin']).json()['nome'] == 'Nome corrigido'
    p = preview(c, h, 'cadastros', CAD + 'cliente;Mesmo legado;12345678901;;;;;;0\n')
    assert p.status_code == 200 and p.json()['pode_importar'] is False


def test_previa_expirada_e_prazo_cadastro_alterado_sem_writes(pagamentos_api, monkeypatch):
    from app.routers import intercambio
    c, h, sessions = pagamentos_api
    pid = person(c, h, documento='12345678901', prazo_dias=30)
    body = NOT + '12345678901;cliente;PRAZO;100,00;2020-01-01;prazo_cadastro;;;Prazo congelado\n'
    token = valid_preview(c, h, 'notas', body)
    before = counts(sessions)
    assert c.patch(f'/pessoas/{pid}', headers=h['admin'], json={'prazo_dias': 60}).status_code == 200
    assert imported(c, h, 'notas', body, token).status_code == 409
    fresh = valid_preview(c, h, 'notas', body)
    current = intercambio.time.time()
    monkeypatch.setattr(intercambio.time, 'time', lambda: current + 901)
    assert imported(c, h, 'notas', body, fresh).status_code == 409
    assert counts(sessions) == before


def test_export_dinheiro_inteiro_duas_casas_ids_e_prazos_inteiros(pagamentos_api):
    c, h, _ = pagamentos_api
    pid = person(c, h, documento='12345678901', prazo_dias=30)
    n = c.post('/notas', headers=h['admin'], json={'pessoa_id': pid, 'relacao': 'cliente',
        'numero_documento': 'CSV-INTEIRO', 'valor_original': 500, 'data_emissao': '2020-01-01',
        'modo_vencimento': 'prazo_cadastro', 'descricao': 'Original inteiro para exportação'})
    assert n.status_code == 201, n.text
    r = c.get(f'/csv/exportar/notas?pessoa_id={pid}&relacao=cliente', headers=h['admin'])
    assert r.status_code == 200, r.text
    rows = list(csv.DictReader(io.StringIO(r.content.decode('utf-8-sig')), delimiter=';'))
    assert len(rows) == 1
    row = rows[0]
    assert (row['valor_original'], row['valor_abatido'], row['saldo_aberto']) == ('500,00', '0,00', '500,00')
    assert row['id'] == str(n.json()['id']) and row['prazo_dias_snapshot'] == '30'
    r = c.get('/csv/exportar/cadastros', headers=h['admin'])
    rows = list(csv.DictReader(io.StringIO(r.content.decode('utf-8-sig')), delimiter=';'))
    assert rows[0]['prazo_dias'] == '30'
