"""Suíte MVP isolada: banco sqlite temporário via dependency override.

Cobre: parcial/integral, excedente sem crédito automático, RN-002/003/006/008,
permissões por perfil e auditoria. Não toca no pix.db de dev.
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_URL = f"sqlite:///{tmp.name}"

from app.main import app
from app.database import get_db
from app.models import Base, User
from app.auth import token_for

engine = create_engine(TEST_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=engine)


def _override():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override
c = TestClient(app)


@pytest.fixture(scope="module")
def auth():
    assert c.post("/auth/seed-admin").status_code == 200
    tok = c.post("/auth/login",
                 json={"email": "admin@local", "senha": "admin123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_fluxo_parcial_estorno(auth):
    r = c.post("/representantes", json={"tipo": "representante", "nome": "Rep A"}, headers=auth)
    assert r.status_code == 201, r.text
    R = r.json()["id"]
    F = c.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn X"}, headers=auth).json()["id"]

    lan = c.post("/lancamentos", json={"tipo": "debito", "valor": 1000, "data": "2026-09-01",
                                       "fornecedor_id": F}, headers=auth).json()
    pix = c.post("/movimentacoes", json={"data_pix": "2026-09-02", "valor": 700,
                                         "representante_id": R, "fornecedor_id": F},
                 headers=auth).json()
    assert pix["codigo"].startswith("PIX-") and pix["codigo"] != "PIX-TMP"
    assert pix["saldo_disponivel"] == 700

    cc = c.post("/conciliacoes", json={"movimentacao_id": pix["id"], "alvo_tipo": "lancamento",
                                       "alvo_id": lan["id"], "valor": 700}, headers=auth)
    assert cc.status_code == 201, cc.text

    # RN-003
    bad = c.post("/conciliacoes", json={"movimentacao_id": pix["id"], "alvo_tipo": "lancamento",
                                        "alvo_id": lan["id"], "valor": 1}, headers=auth)
    assert bad.status_code == 422

    # RN-006
    assert c.post("/projecoes", json={"representante_id": R, "fornecedor_id": F,
                                      "valor_projetado": 500}, headers=auth).status_code == 201
    dup = c.post("/projecoes", json={"representante_id": R, "fornecedor_id": F,
                                     "valor_projetado": 100}, headers=auth)
    assert dup.status_code == 422

    d = c.get("/dashboard", headers=auth).json()
    assert d["total_a_pagar"] == 300 and d["pix_conciliados"] == 1

    # RN-008
    sem_senha = c.post(f"/conciliacoes/{cc.json()['id']}/estornar",
                       json={"motivo": "t"}, headers=auth)
    assert sem_senha.status_code == 403
    errada = c.post(f"/conciliacoes/{cc.json()['id']}/estornar",
                    json={"motivo": "t", "senha": "errada"}, headers=auth)
    assert errada.status_code == 403
    assert c.post(f"/conciliacoes/{cc.json()['id']}/estornar",
                  json={"motivo": "t", "senha": "admin123"}, headers=auth).status_code == 200
    assert c.get("/dashboard", headers=auth).json()["total_a_pagar"] == 1000


def test_excedente_sem_credito_auto(auth):
    F = c.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn Y"}, headers=auth).json()["id"]
    lan = c.post("/lancamentos", json={"tipo": "debito", "valor": 100, "data": "2026-09-01",
                                       "fornecedor_id": F}, headers=auth).json()
    pix = c.post("/movimentacoes", json={"data_pix": "2026-09-02", "valor": 500,
                                         "fornecedor_id": F}, headers=auth).json()
    # tentar conciliar 200 numa obrigação de 100 -> recusado, sem crédito automático
    r = c.post("/conciliacoes", json={"movimentacao_id": pix["id"], "alvo_tipo": "lancamento",
                                      "alvo_id": lan["id"], "valor": 200}, headers=auth)
    assert r.status_code == 422
    ok = c.post("/conciliacoes", json={"movimentacao_id": pix["id"], "alvo_tipo": "lancamento",
                                       "alvo_id": lan["id"], "valor": 100}, headers=auth)
    assert ok.status_code == 201
    det = c.get(f"/movimentacoes/{pix['id']}", headers=auth).json()
    assert det["saldo_disponivel"] == 400 and det["status"] == "parcial"


def test_valor_zero_recusado(auth):
    r = c.post("/movimentacoes", json={"data_pix": "2026-09-02", "valor": 0}, headers=auth)
    assert r.status_code == 422


def test_auditoria(auth):
    rows = c.get("/auditoria", headers=auth).json()
    acoes = {a["acao"] for a in rows}
    assert {"conciliacao_criada", "conciliacao_estornada", "movimentacao_criada"} <= acoes


def test_chave_pix_publica(auth):
    f = c.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn Chave",
                                      "chave_pix": "pag@forn.com", "banco": "Nubank",
                                      "conta": "123-4", "prazo_dias": 7}, headers=auth).json()
    # pública: sem token
    r = c.get(f"/chave-pix/{f['id']}")
    assert r.status_code == 200, r.text
    assert r.json()["chave_pix"] == "pag@forn.com"
    assert r.json()["titular"] == "Forn Chave"
    assert c.get("/chave-pix/999999").status_code == 404
    # representante não expõe chave
    rep = c.post("/representantes", json={"tipo": "representante", "nome": "Rep C",
                                          "chave_pix": "x"}, headers=auth).json()
    assert c.get(f"/chave-pix/{rep['id']}").status_code == 404
    # patch de campos novos
    assert c.patch(f"/pessoas/{f['id']}", json={"prazo_dias": 14}, headers=auth).status_code == 200


def test_links_vendedor(auth):
    rep = c.post("/representantes", json={"tipo": "representante", "nome": "Vendedor Link"},
                 headers=auth).json()
    forn = c.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn Link",
                                         "chave_pix": "link@forn.com"}, headers=auth).json()
    # sem chave cadastrada -> recusa
    sem = c.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn Sem Chave"},
                 headers=auth).json()
    assert c.post("/links", json={"representante_id": rep["id"],
                                  "fornecedor_id": sem["id"]}, headers=auth).status_code == 422
    l = c.post("/links", json={"representante_id": rep["id"],
                               "fornecedor_id": forn["id"]}, headers=auth).json()
    assert l["url"] == f"/v/{l['token']}"
    # público resolve
    r = c.get(f"/links/v/{l['token']}")
    assert r.status_code == 200, r.text
    assert r.json()["chave_pix"] == "link@forn.com"
    # revogado some do público, mas histórico permanece
    assert c.post(f"/links/{l['id']}/revogar", headers=auth).status_code == 200
    assert c.get(f"/links/v/{l['token']}").status_code == 404
    assert any(x["id"] == l["id"] for x in c.get("/links", headers=auth).json())


def test_tolerancia_e_simulacao(auth):
    rep = c.post("/representantes", json={"tipo": "representante", "nome": "Rep Tol"},
                 headers=auth).json()
    forn = c.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn Tol",
                                         "tolerancia_credito": 50}, headers=auth).json()
    R, F = rep["id"], forn["id"]
    lan = c.post("/lancamentos", json={"tipo": "debito", "valor": 100, "data": "2026-09-01",
                                       "fornecedor_id": F}, headers=auth).json()
    pix = c.post("/movimentacoes", json={"data_pix": "2026-09-02", "valor": 500,
                                         "representante_id": R, "fornecedor_id": F},
                 headers=auth).json()
    # simulação antes: pode 100 sem exceder, 150 no total (100 + 50 tolerância)
    s = c.get(f"/simulacao?representante_id={R}&fornecedor_id={F}", headers=auth).json()
    assert s["pix_disponivel"] == 500 and s["divida_aberta"] == 100
    assert s["pode_pagar_sem_exceder"] == 100 and s["pode_pagar_total"] == 150
    # além da tolerância -> 422
    bad = c.post("/conciliacoes", json={"movimentacao_id": pix["id"], "alvo_tipo": "lancamento",
                                        "alvo_id": lan["id"], "valor": 151}, headers=auth)
    assert bad.status_code == 422
    # dentro da tolerância -> quita + crédito explícito de 30
    ok = c.post("/conciliacoes", json={"movimentacao_id": pix["id"], "alvo_tipo": "lancamento",
                                       "alvo_id": lan["id"], "valor": 130}, headers=auth)
    assert ok.status_code == 201, ok.text
    lancs = c.get("/lancamentos", headers=auth).json()
    tol = [l for l in lancs if l["tipo"] == "credito" and l["valor"] == 30]
    assert len(tol) == 1 and tol[0]["saldo_aberto"] == 30
    # estorno cancela o crédito junto E devolve só o consumido (sem criar dinheiro)
    assert c.post(f"/conciliacoes/{ok.json()['id']}/estornar",
                  json={"motivo": "t", "senha": "admin123"}, headers=auth).status_code == 200
    lancs2 = c.get("/lancamentos", headers=auth).json()
    assert [l for l in lancs2 if l["tipo"] == "credito" and l["valor"] == 30][0]["status"] == "cancelado"
    debito = [l for l in lancs2 if l["id"] == lan["id"]][0]
    assert debito["saldo_aberto"] == 100 and debito["status"] == "aberto"
    mov2 = c.get(f"/movimentacoes/{pix['id']}", headers=auth).json()
    assert mov2["saldo_disponivel"] == 500 and mov2["status"] == "disponivel"


def test_mov_colunas_planilha(auth):
    m = c.post("/movimentacoes", json={"data_pix": "2026-09-02", "valor": 10,
                                       "autor": "ANNA CLARA", "forma_pagamento": "PIX",
                                       "natureza": "DESPESA"}, headers=auth).json()
    assert m["autor"] == "ANNA CLARA" and m["forma_pagamento"] == "PIX"
    assert m["natureza"] == "DESPESA"
    det = c.get(f"/movimentacoes/{m['id']}", headers=auth).json()
    assert det["autor"] == "ANNA CLARA"


def test_upload_comprovante_e_fila(auth):
    m = c.post("/movimentacoes", json={"data_pix": "2026-09-02", "valor": 15},
               headers=auth).json()
    # extensão inválida
    bad = c.post(f"/movimentacoes/{m['id']}/comprovante", headers=auth,
                 files={"f": ("x.exe", b"data")})
    assert bad.status_code == 422
    # upload válido cria comprovante + job
    ok = c.post(f"/movimentacoes/{m['id']}/comprovante", headers=auth,
                files={"f": ("comp.pdf", b"%PDF-1.4 fake")})
    assert ok.status_code == 200, ok.text
    comps = c.get(f"/movimentacoes/{m['id']}/comprovantes", headers=auth).json()
    assert len(comps) == 1 and comps[0]["etapa"] == "registrado"
    assert comps[0]["enviado_por"] == "Admin"
    jobs = c.get("/jobs?status=pendente", headers=auth).json()
    assert any(j["ref_id"] == comps[0]["id"] for j in jobs)
    # avança/volta etapa
    assert c.patch(f"/movimentacoes/comprovantes/{comps[0]['id']}",
                   json={"etapa": "recebido"}, headers=auth).status_code == 200
    assert c.patch(f"/movimentacoes/comprovantes/{comps[0]['id']}",
                   json={"etapa": "x"}, headers=auth).status_code == 422
    # worker consome a fila
    r = c.post("/jobs/processar", headers=auth).json()
    assert r["processados"] >= 1
    assert c.get("/jobs?status=pendente", headers=auth).json() == []


def test_ocr_sugestao_revisao_e_dedup(auth):
    rep = c.post("/representantes", json={"tipo": "representante", "nome": "Rep OCR"},
                 headers=auth).json()
    forn = c.post("/fornecedores", json={"tipo": "fornecedor", "nome": "JOAO TESTE SILVA"},
                  headers=auth).json()
    m = c.post("/movimentacoes", json={"data_pix": "2026-09-02", "valor": 42,
                                       "remetente": "JOAO TESTE", "representante_id": rep["id"]},
               headers=auth).json()
    up = c.post(f"/movimentacoes/{m['id']}/comprovante", headers=auth,
                files={"f": ("c.pdf", b"%PDF-1.4 ocr1")})
    assert up.status_code == 200, up.text
    # duplicado (mesmo arquivo) em outra mov -> 422
    m2 = c.post("/movimentacoes", json={"data_pix": "2026-09-02", "valor": 43},
                headers=auth).json()
    dup = c.post(f"/movimentacoes/{m2['id']}/comprovante", headers=auth,
                 files={"f": ("c.pdf", b"%PDF-1.4 ocr1")})
    assert dup.status_code == 422
    # worker extrai + sugere
    assert c.post("/jobs/processar", headers=auth).json()["processados"] >= 1
    fila = c.get("/movimentacoes/revisao/fila", headers=auth).json()
    item = [x for x in fila if x["comprovante_id"] == up.json()["comprovante_id"]]
    assert len(item) == 1 and item[0]["sugestao_fornecedor_id"] == forn["id"]
    # aceitar aplica o fornecedor na mov
    r = c.post(f"/movimentacoes/comprovantes/{up.json()['comprovante_id']}/sugestao",
               json={"acao": "aceitar"}, headers=auth)
    assert r.json()["sugestao_status"] == "aceita"
    det = c.get(f"/movimentacoes/{m['id']}", headers=auth).json()
    assert det["fornecedor_id"] == forn["id"]
    assert c.get("/movimentacoes/revisao/fila", headers=auth).json() == [] or \
        all(x["comprovante_id"] != up.json()["comprovante_id"]
            for x in c.get("/movimentacoes/revisao/fila", headers=auth).json())


def test_webhook_checkto(auth, monkeypatch):
    import app.routers.webhooks as wh
    import app.checkto as ck
    monkeypatch.setattr(wh, "CHECKTO_WEBHOOK_TOKEN", "segredo-teste")
    rep = c.post("/representantes", json={"tipo": "representante", "nome": "Rep CK",
                                          "email": "rep@ck.com", "telefone": "(11) 99999-9999",
                                          "documento": "123.456.789-00"},
                 headers=auth).json()
    forn = c.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn CK",
                                         "chave_pix": "ck@forn.com"}, headers=auth).json()
    link = c.post("/links", json={"representante_id": rep["id"],
                                  "fornecedor_id": forn["id"],
                                  "valor_fixo": 100}, headers=auth).json()
    # cobrar sem chaves configuradas -> 422 claro
    assert c.post(f"/links/{link['id']}/cobrar", headers=auth).status_code == 422
    # cobrar com gateway mockado (links.py importa dentro da função)
    monkeypatch.setattr(ck, "criar_cobranca_pix", lambda **kw: {
        "transactionId": "tx-1", "webhookToken": "tok-link-1",
        "pix": {"code": "000201pix", "image": "http://img/qr"}})
    r = c.post(f"/links/{link['id']}/cobrar", headers=auth)
    assert r.status_code == 201, r.text
    assert r.json()["pix_code"] == "000201pix"

    def payload(token, event="TRANSACTION_PAID", status="COMPLETED", tx="tx-9", ident=None):
        return {"event": event, "token": token,
                "transaction": {"id": tx, "identifier": ident or f"link-{link['token']}",
                                "status": status, "amount": 100,
                                "payedAt": "2026-09-08T10:00:00",
                                "paymentMethod": "PIX"},
                "client": {"name": "Cliente CK"}}

    # token errado -> rejeitado (2XX sem efeito)
    bad = c.post("/webhooks/checkto", json=payload("errado"))
    assert bad.json()["ok"] is False
    # evento não-pago -> ignorado
    assert c.post("/webhooks/checkto",
                  json=payload("segredo-teste", event="TRANSACTION_CREATED")).json()["ignored"] == "TRANSACTION_CREATED"
    # pago válido (via token do painel) -> registra mov + comprovante
    ok = c.post("/webhooks/checkto", json=payload("segredo-teste"))
    assert ok.json()["ok"] is True, ok.text
    m = c.get(f"/movimentacoes/{ok.json()['movimentacao_id']}", headers=auth).json()
    assert m["autor"] == "CHECKTO" and m["valor"] == 100
    comps = c.get(f"/movimentacoes/{m['id']}/comprovantes", headers=auth).json()
    assert comps[0]["origem"] == "gateway"
    # repetição -> idempotente
    dup = c.post("/webhooks/checkto", json=payload("segredo-teste"))
    assert dup.json().get("duplicate") is True


def test_rate_limit_login(auth):
    for _ in range(9):  # +1 login do fixture = 10 dentro da janela
        c.post("/auth/login", json={"email": "admin@local", "senha": "x"})
    r = c.post("/auth/login", json={"email": "admin@local", "senha": "x"})
    assert r.status_code == 429


def test_metricas(auth):
    m = c.get("/metricas", headers=auth).json()
    assert {"comprovantes_por_dia", "conciliacoes_por_dia", "auto_gateway",
            "manual_upload", "creditos_em_aberto"} <= set(m.keys())


def test_modulos_removidos_nao_expoem_rotas(auth):
    assert c.get("/caixa-entrada", headers=auth).status_code == 404
    assert c.post("/integracao/whatsapp/anexo", headers={"x-wa-secret": "segredo"}).status_code == 404
    assert c.post("/comprovantes/1/criar-movimentacao", headers=auth).status_code == 404


def test_seed_admin_prod_exige_token(monkeypatch):
    from app.models import User
    db = TestSession()
    db.query(User).delete()
    db.commit()
    db.close()
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("SETUP_TOKEN", "troca-uma-vez")
    assert c.post("/auth/seed-admin").status_code == 403
    assert c.post("/auth/seed-admin", json={"setup_token": "errado"}).status_code == 403
    ok = c.post("/auth/seed-admin", json={"setup_token": "troca-uma-vez"})
    assert ok.status_code == 200, ok.text
    assert c.post("/auth/seed-admin", json={"setup_token": "troca-uma-vez"}).status_code == 409
    monkeypatch.delenv("ENV")
    monkeypatch.delenv("SETUP_TOKEN")


def _auth_fresco():
    """Token novo sem passar pelo rate-limit de login (usado após reseed)."""
    db = TestSession()
    u = db.query(User).filter_by(email="admin@local").first()
    db.close()
    return {"Authorization": "Bearer " + token_for(u)}


def test_link_token_e_paineis(auth):
    # após reseed do teste anterior o token do fixture expira (salt novo): token fresco
    auth = _auth_fresco()
    rep = c.post("/representantes", json={"tipo": "representante", "nome": "Rep Link"},
                 headers=auth).json()
    forn = c.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn Link2"},
                  headers=auth).json()
    c.post("/lancamentos", json={"tipo": "despesa", "valor": 200, "data": "2026-09-05",
                                 "fornecedor_id": forn["id"]}, headers=auth)
    m = c.post("/movimentacoes", json={"data_pix": "2026-09-06", "valor": 50,
                                       "representante_id": rep["id"],
                                       "fornecedor_id": forn["id"],
                                       "link_token": "tok-abc"}, headers=auth).json()
    assert m["link_token"] == "tok-abc"
    d = c.get("/dashboard", headers=auth).json()
    pf = [x for x in d["por_fornecedor"] if x["fornecedor_id"] == forn["id"]][0]
    assert pf["ultima_compra"] == {"data": "2026-09-05", "valor": 200.0}, pf
    pl = c.get("/pix-de-links", headers=auth).json()
    assert any(x["id"] == m["id"] and x["link_token"] == "tok-abc" for x in pl)


def test_export_csv(auth):
    auth = _auth_fresco()
    for path, header in [
        ("/export/movimentacoes.csv", "codigo;data_pix"),
        ("/export/conciliacoes.csv", "id;movimentacao_id"),
        ("/export/lancamentos.csv", "id;tipo"),
        ("/export/projecoes.csv", "id;representante"),
        ("/export/posicao-fornecedores.csv", "fornecedor_id;fornecedor"),
    ]:
        r = c.get(path, headers=auth)
        assert r.status_code == 200, path
        assert "text/csv" in r.headers["content-type"]
        text = r.content.decode("utf-8-sig")  # BOM
        assert text.splitlines()[0].startswith(header), path
        assert 'attachment; filename=' in r.headers["content-disposition"]
    rows = c.get("/auditoria", headers=auth).json()
    assert "relatorio_exportado" in {a["acao"] for a in rows}



def test_notas_documentais_nao_alteram_saldo_pix(auth):
    """Novo extrato documental não duplica acertos no motor PIX legado."""
    auth = _auth_fresco()
    pid = c.post('/pessoas', headers=auth, json={'nome': 'Titular nota MVP', 'tipo': 'ambos'}).json()['id']
    antes = c.get('/dashboard', headers=auth).json()['total_a_pagar']
    nota = c.post('/notas', headers=auth, json={'pessoa_id': pid, 'relacao': 'fornecedor',
        'numero_documento': 'MVP-01', 'valor_original': 100, 'data_emissao': '2020-01-01',
        'descricao': 'Documento independente', 'modo_vencimento': 'sem_vencimento'})
    assert nota.status_code == 201, nota.text
    nid = nota.json()['id']
    pago = c.post(f'/notas/{nid}/abatimentos', headers=auth, json={'valor': 40,
        'data': '2020-01-02', 'referencia': 'Acerto externo', 'observacao': 'Conferido na loja',
        'chave_idempotencia': 'mvp-nota-acerto'})
    assert pago.status_code == 201, pago.text
    assert c.get(f'/notas/{nid}', headers=auth).json()['saldo_aberto'] == 60
    assert c.get('/dashboard', headers=auth).json()['total_a_pagar'] == antes


def test_pagamento_real_duas_contas_sem_duplicar_motor_legado(auth):
    """Um PIX novo baixa cliente e fornecedor sem entrar no dashboard legado."""
    auth = _auth_fresco()
    cli = c.post('/pessoas', headers=auth, json={'nome': 'Cliente pagamento MVP', 'tipo': 'cliente'}).json()['id']
    forn = c.post('/pessoas', headers=auth, json={'nome': 'Fornecedor pagamento MVP', 'tipo': 'fornecedor'}).json()['id']
    before = c.get('/dashboard', headers=auth).json()['total_a_pagar']
    ids = []
    for pid, relacao, value in ((cli, 'cliente', 1000), (forn, 'fornecedor', 900)):
        r = c.post('/notas', headers=auth, json={'pessoa_id': pid, 'relacao': relacao, 'numero_documento': 'MVP-pagamento',
            'valor_original': value, 'data_emissao': '2020-01-01', 'descricao': 'Nota independente', 'modo_vencimento': 'sem_vencimento'})
        assert r.status_code == 201, r.text
        ids.append(r.json()['id'])
    p = c.post('/pagamentos', headers=auth, json={'tipo': 'cliente_fornecedor', 'forma': 'PIX', 'valor': 300,
        'data': '2020-01-03', 'cliente_id': cli, 'fornecedor_id': forn, 'referencia_externa': 'PAG-MVP-1',
        'observacao': 'Pagamento externo confirmado', 'chave_idempotencia': 'pag-mvp-1', 'declaracao_novo_pagamento': True})
    assert p.status_code == 201, p.text
    for nid, relacao in zip(ids, ('cliente', 'fornecedor')):
        r = c.post(f"/pagamentos/{p.json()['id']}/aplicacoes", headers=auth, json={'nota_id': nid, 'relacao': relacao,
            'valor': 300, 'data': '2020-01-03', 'referencia': 'MVP pagamento', 'observacao': 'Aplicação conferida',
            'chave_idempotencia': f'pag-mvp-{relacao}', **({'fornecedor_confirmou': True, 'referencia_confirmacao': 'Conferência externa MVP'} if relacao == 'fornecedor' else {})})
        assert r.status_code == 201, r.text
    assert c.get(f'/notas/{ids[0]}', headers=auth).json()['saldo_aberto'] == 700
    assert c.get(f'/notas/{ids[1]}', headers=auth).json()['saldo_aberto'] == 600
    assert c.get('/dashboard', headers=auth).json()['total_a_pagar'] == before


def test_acerto_multiplas_notas_preserva_origem_e_motor_legado(auth):
    """Acerto usa um pagamento em duas notas mantendo o PIX legado intacto."""
    auth = _auth_fresco()
    cli = c.post('/pessoas', headers=auth, json={'nome': 'Cliente acerto MVP', 'tipo': 'cliente'}).json()['id']
    forn = c.post('/pessoas', headers=auth, json={'nome': 'Fornecedor acerto MVP', 'tipo': 'fornecedor'}).json()['id']
    before = c.get('/dashboard', headers=auth).json()['total_a_pagar']
    notas = []
    for index in range(2):
        r = c.post('/notas', headers=auth, json={'pessoa_id': cli, 'relacao': 'cliente', 'numero_documento': f'MVP-acerto-{index}',
            'valor_original': 200, 'data_emissao': '2020-01-01', 'descricao': 'Nota do acerto', 'modo_vencimento': 'sem_vencimento'})
        assert r.status_code == 201, r.text
        notas.append(r.json()['id'])
    p = c.post('/pagamentos', headers=auth, json={'tipo': 'cliente_fornecedor', 'forma': 'PIX', 'valor': 300,
        'data': '2020-01-03', 'cliente_id': cli, 'fornecedor_id': forn, 'referencia_externa': 'PAG-ACERTO-MVP',
        'observacao': 'Pagamento externo registrado', 'chave_idempotencia': 'pag-acerto-mvp', 'declaracao_novo_pagamento': True})
    assert p.status_code == 201, p.text
    body = {'pessoa_id': cli, 'relacao': 'cliente', 'data': '2020-01-03', 'referencia': 'ACERTO-MVP',
        'observacao': 'Duas notas em um acerto', 'itens': [{'pagamento_id': p.json()['id'], 'nota_id': nid, 'valor': 100} for nid in notas]}
    preview = c.post('/acertos/previa', headers=auth, json=body)
    assert preview.status_code == 200, preview.text
    acerto = c.post('/acertos', headers=auth, json={**body, 'token_previa': preview.json()['token_previa'], 'chave_idempotencia': 'acerto-mvp'})
    assert acerto.status_code == 201, acerto.text
    r = c.post(f"/acertos/{acerto.json()['id']}/efetivar", headers=auth, json={'confirmacao': True})
    assert r.status_code == 200, r.text
    assert all(c.get(f'/notas/{nid}', headers=auth).json()['saldo_aberto'] == 100 for nid in notas)
    assert c.get('/dashboard', headers=auth).json()['total_a_pagar'] == before


def test_credito_de_sobra_nao_duplica_pagamento_nem_dashboard(auth):
    """Reconhecer e usar sobra muda só crédito/nota, preservando a fonte e legado."""
    from tests.test_creditos import origin, credit, use, fetch
    auth = _auth_fresco()
    headers = {'admin': auth}
    before = c.get('/dashboard', headers=auth).json()['total_a_pagar']
    pid, pagamento, acerto = origin(c, headers)
    cr = credit(c, headers, pagamento, acerto)
    nota = c.post('/notas', headers=auth, json={'pessoa_id': pid, 'relacao': 'cliente', 'numero_documento': 'MVP-crédito-futuro',
        'valor_original': 500, 'data_emissao': '2020-01-05', 'descricao': 'Nota futura', 'modo_vencimento': 'sem_vencimento'})
    assert nota.status_code == 201, nota.text
    assert use(c, headers, cr, nota.json()['id']).status_code == 201
    assert c.get(f"/notas/{nota.json()['id']}", headers=auth).json()['saldo_aberto'] == 440
    assert fetch(c, headers, cr['id'])['saldo_disponivel'] == 40
    pg = c.get(f"/pagamentos/{pagamento['id']}", headers=auth).json()
    assert pg['orcamentos']['cliente']['saldo_disponivel'] == 0
    assert c.get('/dashboard', headers=auth).json()['total_a_pagar'] == before


def test_acerto_fontes_mistas_preserva_credito_fonte_e_legado(auth):
    from tests.test_acertos_fontes_mistas import setup, mixed_body
    from tests.test_acertos import draft, execute
    from tests.test_creditos import fetch
    auth = _auth_fresco()
    headers = {'admin': auth}
    before = c.get('/dashboard', headers=auth).json()['total_a_pagar']
    pid, source, _, cr, n, pagamento = setup(c, headers)
    acerto = draft(c, headers, mixed_body(pid, cr, n, pagamento))
    r = execute(c, headers, acerto['id'])
    assert r.status_code == 200, r.text
    assert c.get(f"/notas/{n['id']}", headers=auth).json()['saldo_aberto'] == 300
    assert fetch(c, headers, cr['id'])['saldo_disponivel'] == 40
    assert c.get(f"/pagamentos/{source['id']}", headers=auth).json()['orcamentos']['cliente']['saldo_disponivel'] == 0
    assert c.get('/dashboard', headers=auth).json()['total_a_pagar'] == before


def test_extrato_consolidado_leitura_preserva_motor_legado(auth):
    from tests.test_acertos_fontes_mistas import setup, mixed_body
    from tests.test_acertos import draft, execute
    auth = _auth_fresco()
    headers = {'admin': auth}
    before = c.get('/dashboard', headers=auth).json()['total_a_pagar']
    pid, _, _, cr, n, pg = setup(c, headers)
    a = draft(c, headers, mixed_body(pid, cr, n, pg))
    assert execute(c, headers, a['id']).status_code == 200
    r = c.get(f'/extratos/{pid}?relacao=cliente', headers=auth)
    assert r.status_code == 200, r.text
    t = r.json()['totais_globais']
    assert t['notas']['saldo_aberto'] == 300
    assert t['pagamentos']['saldo_disponivel'] == 60
    assert t['creditos']['saldo_disponivel'] == 40
    assert t['disponibilidade_total_para_abater'] == 100
    assert c.get('/dashboard', headers=auth).json()['total_a_pagar'] == before


def test_csv_importacao_explicita_nota_preserva_dashboard_legado(auth):
    from tests.test_intercambio import NOT, valid_preview, imported
    auth = _auth_fresco()
    headers = {'admin': auth}
    before = c.get('/dashboard', headers=auth).json()['total_a_pagar']
    pid = c.post('/pessoas', headers=auth, json={'nome': 'Titular CSV MVP', 'tipo': 'cliente',
        'documento': '19876543210'}).json()['id']
    body = NOT + '19876543210;cliente;CSV-MVP;150,00;2020-01-01;sem_vencimento;;;Obrigação explícita\n'
    token = valid_preview(c, headers, 'notas', body)
    r = imported(c, headers, 'notas', body, token)
    assert r.status_code in (200, 201), r.text
    t = c.get(f'/extratos/{pid}?relacao=cliente', headers=auth).json()['totais_globais']
    assert t['notas']['saldo_aberto'] == 150 and t['pagamentos']['saldo_disponivel'] == 0
    assert t['creditos']['saldo_disponivel'] == 0
    assert c.get('/dashboard', headers=auth).json()['total_a_pagar'] == before


def test_catalogo_prazo_e_preferencia_nao_alteram_motor_legado(auth):
    from tests.test_configuracoes import catalog, prefs
    from tests.test_pagamentos import person
    auth = _auth_fresco()
    headers = {'admin': auth}
    before = c.get('/dashboard', headers=auth).json()['total_a_pagar']
    prazo = catalog(c, headers, 'condicoes', nome='Prazo MVP catálogo', prazo_dias=15)
    pid = person(c, headers)
    r = c.post('/notas', headers=auth, json={'pessoa_id': pid, 'relacao': 'cliente',
        'numero_documento': 'CATALOGO-MVP', 'valor_original': 200, 'data_emissao': '2020-01-01',
        'descricao': 'Snapshot do catálogo', 'condicao_id': prazo['id']})
    assert r.status_code == 201, r.text
    assert r.json()['vencimento'] == '2020-01-16' and r.json()['saldo_aberto'] == 200
    assert c.put('/configuracoes/tabelas/notas', headers=auth, json=prefs()).status_code == 200
    assert c.get('/dashboard', headers=auth).json()['total_a_pagar'] == before


def test_rastreabilidade_metadados_declarados_preserva_financeiro_legado(auth):
    from tests.test_pagamentos import person, payment_payload
    auth = _auth_fresco()
    headers = {'admin': auth}
    before = c.get('/dashboard', headers=auth).json()['total_a_pagar']
    cli, forn = person(c, headers), person(c, headers)
    r = c.post('/pagamentos', headers=auth, json=payment_payload(cliente_id=cli, fornecedor_id=forn,
        data_hora_transacao='2020-01-03T12:00:00-03:00', remetente='Nome declarado MVP'))
    assert r.status_code == 201, r.text
    p = r.json()
    assert p['origem_registro'] == 'manual' and p['created_by']
    assert p['data_hora_transacao'] == '2020-01-03T15:00:00+00:00'
    assert p['orcamentos']['cliente']['saldo_disponivel'] == 300
    assert c.get('/dashboard', headers=auth).json()['total_a_pagar'] == before


from tests.test_administracao import administracao_api


def test_administracao_propria_identidade_nao_altera_financeiro(administracao_api):
    from app.models import Movimentacao, Conciliacao, Lancamento, Pagamento, NotaObrigacao
    c, h, sessions, _ = administracao_api
    r = c.patch('/auth/me', headers=h['consulta'], json={'nome': 'Consulta atualizada'})
    assert r.status_code == 200 and r.json()['perfil'] == 'consulta'
    assert c.patch('/auth/me', headers=h['consulta'], json={'perfil': 'admin'}).status_code == 422
    assert c.get('/loja', headers=h['consulta']).status_code == 200
    assert c.patch('/loja', headers=h['consulta'], json={'nome': 'Não autorizada'}).status_code == 403
    with sessions() as db:
        assert all(db.query(model).count() == 0 for model in (Movimentacao, Conciliacao, Lancamento, Pagamento, NotaObrigacao))


def test_extrato_compartilhado_relacao_fixa_sem_mutacao_financeira(administracao_api):
    from tests.test_compartilhamento_extrato import issue, public, db_snapshot
    from tests.test_pagamentos import person, note
    c, h, sessions, _ = administracao_api
    pid = person(c, h)
    note(c, h, pid, value=500)
    note(c, h, pid, 'fornecedor', value=900)
    issued = issue(c, h, pid)
    before = db_snapshot(sessions)
    r = public(c, issued['token'])
    assert r.status_code == 200 and r.json()['relacao'] == 'cliente'
    assert r.json()['totais_globais']['notas']['saldo_aberto'] == 500
    assert public(c, issued['token'], relacao='fornecedor').status_code == 422
    assert db_snapshot(sessions) == before


def test_classificacao_legado_nao_cria_credito_nota_pagamento(administracao_api):
    from datetime import date
    from app.models import Movimentacao
    from tests.test_legado import inventory, item, confirm, snapshot
    client, headers, sessions, _ = administracao_api
    with sessions() as db:
        source = Movimentacao(codigo='PIX-MVP-LEGADO', data_pix=date(2026, 1, 1),
            valor=120, saldo_disponivel=120)
        db.add(source)
        db.commit()
        source_id = source.id
    before = snapshot(sessions, True)
    row = item(client, headers, 'movimentacao', source_id, decisao='pendente')
    response = confirm(client, headers, [row], key='mvp-pendente-001')
    assert response.status_code in (200, 201), response.text
    assert snapshot(sessions, True) == before
    out = inventory(client, headers, 'movimentacao')
    assert out['conversao_habilitada'] is False


def test_visao_global_mvp_privada_com_cobertura_explicita(auth):
    auth = _auth_fresco()
    response = c.get('/visao-geral/resumo', headers=auth)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['escopo'] == 'dominio_novo'
    assert data['cobertura'] == {'legado_integrado': False, 'consumo_integrado_habilitado': False}
    assert set(data['contas']) == {'cliente', 'fornecedor'}
    assert response.headers['cache-control'] == 'private, no-store'
    assert c.get('/visao-geral/resumo').status_code == 401
