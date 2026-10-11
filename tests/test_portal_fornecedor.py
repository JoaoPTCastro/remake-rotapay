"""Portal limitado: identidade central, cadastro local e declaração sem abatimento."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from app.auth import hash_pw, token_for
from app.models import User
from app.organizacoes_models import FornecedorIdentidade, FornecedorVinculo, VinculoOrganizacao
from tests.test_ambientes import ambiente_api, provisionar


@pytest.fixture
def portal(ambiente_api):
    c, h, sessions, tmp = ambiente_api
    with sessions() as db:
        db.add(User(id=5, nome="Outro fornecedor", email="outro@teste.local", perfil="fornecedor", senha_hash=hash_pw("senha-teste")))
        db.flush()
        for uid in (4, 5):
            identity = FornecedorIdentidade(user_id=uid)
            db.add(identity)
            db.flush()
            for org in (2, 3):
                if not db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id == uid, VinculoOrganizacao.organizacao_id == org)):
                    db.add(VinculoOrganizacao(user_id=uid, organizacao_id=org, perfil="fornecedor"))
                db.add(FornecedorVinculo(identidade_id=identity.id, organizacao_id=org))
        db.commit()
        h[5] = {"Authorization": f"Bearer {token_for(db.get(User, 5))}"}
    stores = {}
    for org in (2, 3):
        admin = provisionar(c, h[2], org)
        people = []
        for name, tipo in ((f"Cliente secreto loja {org}", "cliente"), (f"Fornecedor próprio loja {org}", "fornecedor"), (f"Outro fornecedor loja {org}", "fornecedor")):
            r = c.post("/pessoas", headers=admin, json={"tipo": tipo, "nome": name, "documento": "DADO-PRIVADO", "observacoes": "OBS-PRIVADA"})
            assert r.status_code == 201, r.text
            people.append(r.json()["id"])
        payments = []
        for supplier, value in ((people[1], org * 100), (people[2], org * 1000)):
            r = c.post("/pagamentos", headers=admin, json={"tipo": "cliente_fornecedor", "forma": "PIX", "valor": value,
                "data": "2026-10-03", "cliente_id": people[0], "fornecedor_id": supplier, "referencia_externa": f"externa-{supplier}",
                "observacao": "OBS-PAGAMENTO-PRIVADA", "chave_idempotencia": f"pagamento-{supplier}", "declaracao_novo_pagamento": True})
            assert r.status_code == 201, r.text
            payments.append(r.json()["id"])
        stores[org] = {"admin": admin, "people": people, "payments": payments}
    return c, h, sessions, tmp, stores


def bind(c, h, org, uid, pid):
    return c.put(f"/organizacoes/{org}/fornecedores/{uid}/cadastro", headers=h, json={"pessoa_id": pid})


def test_vinculo_explicito_obrigatorio_sem_adivinhar_ids(portal):
    c, h, _, _, stores = portal
    assert c.get("/organizacoes/2/portal-fornecedor", headers=h[4]).status_code in (403, 409)
    assert bind(c, h[4], 2, 4, stores[2]["people"][1]).status_code == 403
    assert bind(c, h[2], 2, 4, 99999).status_code in (404, 422)
    assert bind(c, h[2], 2, 4, stores[2]["people"][0]).status_code in (409, 422)
    r = bind(c, h[2], 2, 4, stores[2]["people"][1])
    assert r.status_code == 200, r.text
    assert bind(c, h[2], 2, 4, stores[2]["people"][2]).status_code == 409
    assert bind(c, h[2], 2, 5, stores[2]["people"][1]).status_code == 409


def test_portal_ids_iguais_em_lojas_distintas_sem_dados_de_terceiros(portal):
    c, h, _, _, stores = portal
    for org in (2, 3):
        assert bind(c, h[2], org, 4, stores[org]["people"][1]).status_code == 200
        r = c.get(f"/organizacoes/{org}/portal-fornecedor", headers=h[4])
        assert r.status_code == 200, r.text
        assert r.headers["cache-control"] == "private, no-store"
        assert f"Cliente secreto loja {org}" not in r.text
        assert "DADO-PRIVADO" not in r.text and "OBS-PAGAMENTO-PRIVADA" not in r.text
        assert f"Outro fornecedor loja {org}" not in r.text
    assert c.get("/organizacoes/4/portal-fornecedor", headers=h[4]).status_code == 403
    for path in ("/pessoas", "/pagamentos", "/notas", "/auth/users"):
        assert c.get(path, headers=h[4]).status_code == 403


def test_recebimento_nao_quita_notas_nao_gera_credito_e_nao_reescreve_pagamento(portal):
    c, h, _, _, stores = portal
    store = stores[2]
    assert bind(c, h[2], 2, 4, store["people"][1]).status_code == 200
    pid = store["payments"][0]
    before = c.get(f"/pagamentos/{pid}", headers=store["admin"]).json()
    wrong = c.post(f"/organizacoes/2/portal-fornecedor/pagamentos/{store['payments'][1]}/confirmar-recebimento", headers=h[4], json={"referencia": "Confirmado pelo próprio fornecedor", "observacao": "Recebi"})
    assert wrong.status_code == 404
    path = f"/organizacoes/2/portal-fornecedor/pagamentos/{pid}/confirmar-recebimento"
    r = c.post(path, headers=h[4], json={"referencia": "Conferido no meu banco", "observacao": "Recebimento declarado"})
    assert r.status_code in (200, 201), r.text
    after = c.get(f"/pagamentos/{pid}", headers=store["admin"]).json()
    assert before == after
    repeated = c.post(path, headers=h[4], json={"referencia": "Tentativa de substituir", "observacao": "Outro texto"})
    assert repeated.status_code == 409
    assert c.get("/creditos", headers=store["admin"]).json() == []


def test_revogacao_local_nao_altera_identidade_global_nem_outra_loja(portal):
    c, h, sessions, _, stores = portal
    for org in (2, 3):
        assert bind(c, h[2], org, 4, stores[org]["people"][1]).status_code == 200
    with sessions() as db:
        before = (db.get(User, 4).perfil, db.get(User, 4).senha_hash, db.get(User, 4).ativo)
    r = c.patch("/organizacoes/2/membros/4", headers=h[2], json={"perfil": "fornecedor", "ativo": False})
    assert r.status_code == 200, r.text
    assert c.get("/organizacoes/2/portal-fornecedor", headers=h[4]).status_code == 403
    assert c.get("/organizacoes/3/portal-fornecedor", headers=h[4]).status_code == 200
    with sessions() as db:
        assert before == (db.get(User, 4).perfil, db.get(User, 4).senha_hash, db.get(User, 4).ativo)
    assert c.patch("/organizacoes/2/membros/2", headers=h[2], json={"perfil": "operador", "ativo": True}).status_code == 409


def test_fornecedor_nao_promovido_e_consulta_nao_administra_vinculos(portal):
    c, h, _, _, stores = portal
    assert c.patch("/organizacoes/2/membros/4", headers=h[2], json={"perfil": "admin", "ativo": True}).status_code in (409, 422)
    assert c.patch("/organizacoes/2/membros/2", headers=h[3], json={"perfil": "operador", "ativo": True}).status_code == 403
    assert bind(c, h[3], 2, 4, stores[2]["people"][1]).status_code == 403


@pytest.mark.parametrize("revoke", ["usuario", "organizacao", "identidade", "cadastro"])
def test_autorizacoes_revalidadas_em_cada_operacao(portal, revoke):
    c, h, sessions, tmp, stores = portal
    from app import ambientes
    from app.models import Pessoa
    from app.organizacoes_models import Organizacao
    assert bind(c, h[2], 2, 4, stores[2]["people"][1]).status_code == 200
    assert c.get("/organizacoes/2/portal-fornecedor", headers=h[4]).status_code == 200
    if revoke == "cadastro":
        with ambientes._sessions(str(tmp / "financeiro" / "organizacao-2.sqlite3"))() as db:
            db.get(Pessoa, stores[2]["people"][1]).ativo = False
            db.commit()
    else:
        with sessions() as db:
            if revoke == "usuario":
                db.get(User, 4).ativo = False
            elif revoke == "organizacao":
                db.get(Organizacao, 2).ativo = False
            else:
                identity = db.scalar(select(FornecedorIdentidade).where(FornecedorIdentidade.user_id == 4))
                db.scalar(select(FornecedorVinculo).where(FornecedorVinculo.identidade_id == identity.id, FornecedorVinculo.organizacao_id == 2)).ativo = False
            db.commit()
    r = c.get("/organizacoes/2/portal-fornecedor", headers=h[4])
    assert r.status_code in (401, 403, 409), r.text
    path = f"/organizacoes/2/portal-fornecedor/pagamentos/{stores[2]['payments'][0]}/confirmar-recebimento"
    assert c.post(path, headers=h[4], json={"referencia": "Não autorizado", "observacao": "Revogado"}).status_code in (401, 403, 409)


def test_concorrencia_nao_remove_todos_administradores(portal):
    c, h, sessions, _, _ = portal
    with sessions() as db:
        db.get(User, 3).perfil = "admin"
        db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id == 3, VinculoOrganizacao.organizacao_id == 2)).perfil = "admin"
        db.commit()
    def revoke(uid):
        return c.patch(f"/organizacoes/2/membros/{uid}", headers=h[uid], json={"perfil": "admin", "ativo": False}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(revoke, (2, 3)))
    assert statuses.count(200) == 1 and all(status in (200, 403, 409) for status in statuses), statuses
    with sessions() as db:
        remaining = db.scalars(select(VinculoOrganizacao).where(VinculoOrganizacao.organizacao_id == 2, VinculoOrganizacao.perfil == "admin", VinculoOrganizacao.ativo.is_(True))).all()
        assert len(remaining) == 1


def test_chaves_proprias_principal_unico_sem_alterar_outro_cadastro(portal):
    c, h, _, _, stores = portal
    for uid, pid in ((4, stores[2]["people"][1]), (5, stores[2]["people"][2])):
        assert bind(c, h[2], 2, uid, pid).status_code == 200
    prefix = "/organizacoes/2/portal-fornecedor/chaves-pix"
    r = c.post(prefix, headers=h[5], json={"chave": "outro@pix.local", "tipo": "email", "principal": True})
    assert r.status_code == 201, r.text
    other = r.json()["id"]
    assert c.patch(f"{prefix}/{other}", headers=h[4], json={"chave": "invadida@pix.local", "tipo": "email", "principal": True}).status_code == 404
    def add_key(number):
        return c.post(prefix, headers=h[4], json={"chave": f"propria-{number}@pix.local", "tipo": "email", "principal": True})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(add_key, (1, 2)))
    assert all(r.status_code in (201, 409) for r in responses), [(r.status_code, r.text) for r in responses]
    assert any(r.status_code == 201 for r in responses)
    own = c.get("/organizacoes/2/portal-fornecedor", headers=h[4]).json()["chaves_pix"]
    assert sum(k["principal"] for k in own) == 1
    assert all(k["chave"] != "outro@pix.local" for k in own)
    remaining = c.get("/organizacoes/2/portal-fornecedor", headers=h[5]).json()["chaves_pix"]
    assert remaining[0]["chave"] == "outro@pix.local" and remaining[0]["principal"]
    assert c.post(prefix, headers=h[4], json={"chave": "forged", "pessoa_id": stores[2]["people"][2]}).status_code == 422


def test_declaracao_concorrente_unica_e_auditoria_de_autor(portal):
    c, h, _, tmp, stores = portal
    from app import ambientes
    from app.models import AuditLog, CreditoConta, PagamentoAplicacao
    from app.fornecedores_models import RecebimentoFornecedor
    assert bind(c, h[2], 2, 4, stores[2]["people"][1]).status_code == 200
    path = f"/organizacoes/2/portal-fornecedor/pagamentos/{stores[2]['payments'][0]}/confirmar-recebimento"
    def declare(i):
        return c.post(path, headers=h[4], json={"referencia": f"Declaração {i}", "observacao": "Eu conferi"}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(declare, (1, 2)))
    assert sorted(statuses) == [200, 409], statuses
    with ambientes._sessions(str(tmp / "financeiro" / "organizacao-2.sqlite3"))() as db:
        receipts = db.scalars(select(RecebimentoFornecedor)).all()
        assert len(receipts) == 1 and receipts[0].usuario_central_id == 4
        assert float(receipts[0].valor_declarado) == 200
        logs = db.scalars(select(AuditLog).where(AuditLog.acao == "recebimento_declarado_fornecedor")).all()
        assert len(logs) == 1 and logs[0].usuario_id == 4
        assert not db.scalars(select(CreditoConta)).all()
        assert not db.scalars(select(PagamentoAplicacao)).all()


def test_administracao_nao_altera_perfil_global_e_nega_pessoa_de_outra_loja(portal):
    c, h, sessions, _, stores = portal
    with sessions() as db:
        before = db.get(User, 3).perfil
    r = c.patch("/organizacoes/2/membros/3", headers=h[2], json={"perfil": "financeiro", "ativo": True})
    assert r.status_code == 200, r.text
    with sessions() as db:
        assert db.get(User, 3).perfil == before
    r = c.post("/pessoas", headers=stores[3]["admin"], json={"tipo": "fornecedor", "nome": "Somente outra loja"})
    pid = r.json()["id"]
    assert bind(c, h[2], 2, 4, pid).status_code == 422
    assert c.post("/organizacoes/2/membros", headers=h[2], json={"email": "fornecedor@teste.local", "perfil": "admin"}).status_code == 404


def test_cancelamento_e_fluxo_loja_nao_declaram_recebimento_do_fornecedor(portal):
    c, h, _, tmp, stores = portal
    from app import ambientes
    from app.models import Pagamento
    assert bind(c, h[2], 2, 4, stores[2]["people"][1]).status_code == 200
    pid = stores[2]["payments"][0]
    with ambientes._sessions(str(tmp / "financeiro" / "organizacao-2.sqlite3"))() as db:
        db.get(Pagamento, pid).cancelado = True
        db.commit()
    prefix = "/organizacoes/2/portal-fornecedor/pagamentos"
    assert c.post(f"{prefix}/{pid}/confirmar-recebimento", headers=h[4], json={"referencia": "Cancelado"}).status_code == 409
    r = c.post("/pagamentos", headers=stores[2]["admin"], json={"tipo": "cliente_loja", "forma": "dinheiro", "valor": 50,
        "data": "2026-10-03", "cliente_id": stores[2]["people"][0], "referencia_externa": "entrada-na-loja", "observacao": "Dinheiro loja",
        "chave_idempotencia": "entrada-na-loja", "declaracao_novo_pagamento": True})
    assert r.status_code == 201, r.text
    store_pid = r.json()["id"]
    portal_out = c.get("/organizacoes/2/portal-fornecedor", headers=h[4]).json()
    assert store_pid not in [p["id"] for p in portal_out["pagamentos"]]
    assert c.post(f"{prefix}/{store_pid}/confirmar-recebimento", headers=h[4], json={"referencia": "Dinheiro loja"}).status_code == 404


def test_notas_do_fornecedor_sem_outros_titulares_e_declaração_nao_abate(portal):
    c, h, _, _, stores = portal
    store = stores[2]
    assert bind(c, h[2], 2, 4, store["people"][1]).status_code == 200
    for supplier, document in ((store["people"][1], "COMPRA-PROPRIA"), (store["people"][2], "COMPRA-SECRETA")):
        r = c.post("/notas", headers=store["admin"], json={"pessoa_id": supplier, "relacao": "fornecedor", "numero_documento": document,
            "valor_original": 500, "data_emissao": "2026-10-03", "modo_vencimento": "sem_vencimento"})
        assert r.status_code == 201, r.text
    path = f"/organizacoes/2/portal-fornecedor/pagamentos/{store['payments'][0]}/confirmar-recebimento"
    assert c.post(path, headers=h[4], json={"referencia": "Declaração conferida"}).status_code == 200
    r = c.get("/organizacoes/2/portal-fornecedor", headers=h[4])
    assert "COMPRA-SECRETA" not in r.text
    assert len(r.json()["notas"]) == 1
    assert r.json()["notas"][0]["saldo"] == 500


def test_legado_pessoa_central_nao_concede_portal_e_vinculo_interno_legitimo(portal):
    c, h, sessions, _, stores = portal
    from app.models import Pessoa
    with sessions() as db:
        central_person = Pessoa(id=stores[2]["people"][1], tipo="fornecedor", nome="Cadastro antigo central")
        db.add(central_person)
        db.flush()
        identity = db.scalar(select(FornecedorIdentidade).where(FornecedorIdentidade.user_id == 4))
        db.scalar(select(FornecedorVinculo).where(FornecedorVinculo.identidade_id == identity.id, FornecedorVinculo.organizacao_id == 2)).pessoa_id = central_person.id
        db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id == 4, VinculoOrganizacao.organizacao_id == 2)).perfil = "consulta"
        db.commit()
    assert c.get("/organizacoes/2/portal-fornecedor", headers=h[4]).status_code == 409
    assert bind(c, h[2], 2, 4, stores[2]["people"][1]).status_code == 200
    assert c.get("/organizacoes/2/portal-fornecedor", headers=h[4]).status_code == 200


def test_portal_loja_original_compativel_sem_pessoa_de_banco_novo(portal):
    c, h, sessions, _, stores = portal
    with sessions() as db:
        identity = db.scalar(select(FornecedorIdentidade).where(FornecedorIdentidade.user_id == 4))
        db.add(VinculoOrganizacao(user_id=4, organizacao_id=1, perfil="fornecedor"))
        db.add(FornecedorVinculo(identidade_id=identity.id, organizacao_id=1))
        db.commit()
    r = c.post("/pessoas", headers=h[1], json={"tipo": "fornecedor", "nome": "Fornecedor original"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert bind(c, h[1], 1, 4, pid).status_code == 200
    r = c.get("/organizacoes/1/portal-fornecedor", headers=h[4])
    assert r.status_code == 200 and r.json()["fornecedor"]["nome"] == "Fornecedor original"
    assert r.json()["pagamentos"] == []
    r = c.post("/organizacoes/1/portal-fornecedor/chaves-pix", headers=h[4], json={"chave": "original@pix.local", "tipo": "email", "principal": True})
    assert r.status_code == 201, r.text
    assert bind(c, h[2], 2, 4, stores[2]["people"][1]).status_code == 200
    assert c.get("/organizacoes/2/portal-fornecedor", headers=h[4]).json()["chaves_pix"] == []


def test_org_explicita_nao_aceita_header_para_escolher_banco(portal):
    c, h, _, _, stores = portal
    for org in (2, 3):
        assert bind(c, h[2], org, 4, stores[org]["people"][1]).status_code == 200
    assert c.get("/organizacoes/2/portal-fornecedor", headers={**h[4], "X-Organizacao-Id": "3"}).status_code == 403
    assert c.get("/organizacoes/3/portal-fornecedor", headers=h[4]).json()["resumo"]["total_recebimentos"] == 300


def test_declaracao_preservada_com_divergencia_e_cancelamento_posteriores(portal):
    c, h, _, tmp, stores = portal
    from app import ambientes
    from app.models import Pagamento
    assert bind(c, h[2], 2, 4, stores[2]["people"][1]).status_code == 200
    pid = stores[2]["payments"][0]
    path = f"/organizacoes/2/portal-fornecedor/pagamentos/{pid}/confirmar-recebimento"
    body = {"referencia": "Recebi o valor original", "observacao": "Conferido"}
    first = c.post(path, headers=h[4], json=body)
    assert first.status_code == 200, first.text
    assert c.post(path, headers=h[4], json=body).json() == first.json()
    factory = ambientes._sessions(str(tmp / "financeiro" / "organizacao-2.sqlite3"))
    with factory() as db:
        payment = db.get(Pagamento, pid)
        payment.valor = 250
        payment.version += 1
        db.commit()
    out = c.get("/organizacoes/2/portal-fornecedor", headers=h[4]).json()
    receipt = out["pagamentos"][0]["recebimento"]
    assert receipt["situacao"] == "divergente" and receipt["valor_declarado"] == 200
    assert out["resumo"]["total_declarado"] == 0
    assert c.post(path, headers=h[4], json=body).status_code == 409
    with factory() as db:
        db.get(Pagamento, pid).cancelado = True
        db.commit()
    receipt = c.get("/organizacoes/2/portal-fornecedor", headers=h[4]).json()["pagamentos"][0]["recebimento"]
    assert receipt["situacao"] == "cancelado" and receipt["referencia"] == body["referencia"]


def test_payloads_nao_escolhem_org_pessoa_usuario_ou_valor(portal):
    c, h, _, _, stores = portal
    pid = stores[2]["people"][1]
    for extra in ({"organizacao_id": 3}, {"pessoa_id": True}, {"user_id": 5}):
        assert c.put("/organizacoes/2/fornecedores/4/cadastro", headers=h[2], json={"pessoa_id": pid, **extra}).status_code == 422
    assert bind(c, h[2], 2, 4, pid).status_code == 200
    path = f"/organizacoes/2/portal-fornecedor/pagamentos/{stores[2]['payments'][0]}/confirmar-recebimento"
    for extra in ({"valor": 1000}, {"usuario_id": 5}, {"organizacao_id": 3}):
        assert c.post(path, headers=h[4], json={"referencia": "Não pode adulterar", **extra}).status_code == 422


def test_loja_original_nao_promove_perfil_incompativel_com_autorizacao_legada(portal):
    c, h, sessions, _, _ = portal
    # User 2 é operador global, embora admin nas lojas novas. A original ainda
    # cruza a autorização local com o perfil legado: não pode ganhar admin falso.
    r = c.post("/organizacoes/1/membros", headers=h[1], json={"email": "lojas@teste.local", "perfil": "admin"})
    assert r.status_code == 409, r.text
    with sessions() as db:
        assert not db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id == 2, VinculoOrganizacao.organizacao_id == 1))
        assert db.get(User, 2).perfil == "operador"
    r = c.post("/organizacoes/1/membros", headers=h[1], json={"email": "lojas@teste.local", "perfil": "operador"})
    assert r.status_code == 201, r.text
    r = c.patch("/organizacoes/1/membros/2", headers=h[1], json={"perfil": "admin", "ativo": True})
    assert r.status_code == 409, r.text
    assert c.patch("/organizacoes/1/membros/1", headers=h[1], json={"perfil": "admin", "ativo": False}).status_code == 409
    # O novo ambiente continua usando seu próprio perfil e não muda identidade.
    r = c.post("/organizacoes/3/membros", headers=h[2], json={"email": "consulta@teste.local", "perfil": "operador"})
    assert r.status_code == 201, r.text
    r = c.patch("/organizacoes/3/membros/3", headers=h[2], json={"perfil": "admin", "ativo": True})
    assert r.status_code == 200, r.text
    with sessions() as db:
        assert db.get(User, 3).perfil == "admin"
        assert db.get(User, 2).perfil == "operador"


def test_admin_original_real_nao_substituido_por_vinculo_admin_sem_perfil_global(portal):
    c, h, sessions, _, _ = portal
    # Simula vínculo antigo incoerente: o contador deve considerar somente
    # administradores que possam realmente exercer a autorização da original.
    with sessions() as db:
        db.add(VinculoOrganizacao(user_id=2, organizacao_id=1, perfil="admin", ativo=True))
        db.commit()
    r = c.patch("/organizacoes/1/membros/1", headers=h[1], json={"perfil": "admin", "ativo": False})
    assert r.status_code == 409, r.text
    with sessions() as db:
        original = db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id == 1, VinculoOrganizacao.organizacao_id == 1))
        assert original.ativo and original.perfil == "admin"
    assert c.get("/auth/users", headers=h[1]).status_code == 200


def test_abatimento_e_estorno_nao_invalidam_recebimento_ja_declarado(portal):
    c, h, _, _, stores = portal
    store = stores[2]
    assert bind(c, h[2], 2, 4, store["people"][1]).status_code == 200
    pid = store["payments"][0]
    declaration_path = f"/organizacoes/2/portal-fornecedor/pagamentos/{pid}/confirmar-recebimento"
    declaration = {"referencia": "Recebimento conferido antes do abatimento", "observacao": "Dinheiro recebido"}
    declared = c.post(declaration_path, headers=h[4], json=declaration)
    assert declared.status_code == 200, declared.text
    note = c.post("/notas", headers=store["admin"], json={"pessoa_id": store["people"][1], "relacao": "fornecedor",
        "numero_documento": "COMPRA-ABATIMENTO-RECIBO", "valor_original": 500, "data_emissao": "2026-10-03", "modo_vencimento": "sem_vencimento"})
    assert note.status_code == 201, note.text
    application = c.post(f"/pagamentos/{pid}/aplicacoes", headers=store["admin"], json={"nota_id": note.json()["id"], "relacao": "fornecedor",
        "valor": 75, "data": "2026-10-03", "referencia": "Abatimento parcial", "observacao": "Conferido externamente",
        "chave_idempotencia": "abatimento-recibo", "fornecedor_confirmou": True, "referencia_confirmacao": "Concordância externa do fornecedor"})
    assert application.status_code == 201, application.text
    after = c.get("/organizacoes/2/portal-fornecedor", headers=h[4]).json()
    assert after["pagamentos"][0]["recebimento"] == declared.json()
    assert after["resumo"]["total_declarado"] == 200
    assert after["resumo"]["saldo_disponivel"] == 125
    assert after["resumo"]["total_aplicado"] == 75
    assert after["notas"][0]["saldo"] == 425
    assert c.post(declaration_path, headers=h[4], json=declaration).json() == declared.json()
    reversal = c.post(f"/pagamentos/{pid}/aplicacoes/{application.json()['id']}/estornar", headers=store["admin"],
        json={"motivo": "Desfazer aplicação para outra nota", "senha": "senha-teste"})
    assert reversal.status_code == 200, reversal.text
    after = c.get("/organizacoes/2/portal-fornecedor", headers=h[4]).json()
    assert after["pagamentos"][0]["recebimento"] == declared.json()
    assert after["resumo"]["total_declarado"] == 200
    assert after["resumo"]["saldo_disponivel"] == 200
    assert after["resumo"]["total_aplicado"] == 0
    assert after["notas"][0]["saldo"] == 500
