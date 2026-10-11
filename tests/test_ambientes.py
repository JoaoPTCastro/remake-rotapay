"""Exercita a resolução real das sessões, sem override que esconda isolamento."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.main import app
from app import database, ambientes
from app.auth import hash_pw, token_for, check_pw
from app.models import Base, User
from app.organizacoes_models import Organizacao, VinculoOrganizacao


@pytest.fixture
def ambiente_api(tmp_path, monkeypatch, request):
    engine = create_engine(f"sqlite:///{tmp_path / 'controle.sqlite3'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessions)
    monkeypatch.setattr(ambientes, "database_root", tmp_path / "financeiro")
    with sessions() as db:
        db.add_all([User(id=1, nome="Admin original", email="original@teste.local", perfil="admin", senha_hash=hash_pw("senha-teste")),
                    User(id=2, nome="Admin lojas", email="lojas@teste.local", perfil="operador", senha_hash=hash_pw("senha-teste")),
                    User(id=3, nome="Consulta", email="consulta@teste.local", perfil="admin", senha_hash=hash_pw("senha-teste")),
                    User(id=4, nome="Fornecedor", email="fornecedor@teste.local", perfil="fornecedor", senha_hash=hash_pw("senha-teste"))])
        db.add_all([Organizacao(id=i, nome=f"Loja {i}") for i in (1, 2, 3, 4)])
        db.flush()
        db.add_all([VinculoOrganizacao(user_id=1, organizacao_id=1, perfil="admin"),
                    VinculoOrganizacao(user_id=2, organizacao_id=2, perfil="admin"),
                    VinculoOrganizacao(user_id=2, organizacao_id=3, perfil="admin"),
                    VinculoOrganizacao(user_id=3, organizacao_id=2, perfil="consulta"),
                    VinculoOrganizacao(user_id=4, organizacao_id=2, perfil="fornecedor")])
        db.commit()
        headers = {u.id: {"Authorization": f"Bearer {token_for(u)}"} for u in db.scalars(select(User))}
    # Não altera get_db: o resolvedor de produção precisa decidir qual banco abrir.
    previous = app.dependency_overrides.copy()
    app.dependency_overrides.clear()
    client = TestClient(app, client=(request.node.nodeid, 50000))
    try:
        yield client, headers, sessions, tmp_path
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def selecionar(c, headers, org):
    r = c.post(f"/organizacoes/{org}/selecionar", headers=headers)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def provisionar(c, headers, org):
    r = c.post(f"/organizacoes/{org}/provisionar", headers=headers)
    assert r.status_code in (200, 201), r.text
    return selecionar(c, headers, org)


def criar_cliente(c, h, nome):
    r = c.post("/pessoas", headers=h, json={"tipo": "cliente", "nome": nome})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def criar_nota(c, h, pessoa, numero, valor):
    r = c.post("/notas", headers=h, json={"pessoa_id": pessoa, "relacao": "cliente", "numero_documento": numero,
        "valor_original": valor, "data_emissao": "2026-10-03", "modo_vencimento": "sem_vencimento"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_ids_coincidentes_leituras_csv_e_mutacoes_isoladas(ambiente_api):
    c, h, _, _ = ambiente_api
    a, b = [provisionar(c, h[2], org) for org in (2, 3)]
    pa, pb = criar_cliente(c, a, "Cliente loja A"), criar_cliente(c, b, "Cliente loja B")
    assert pa == pb
    na, nb = criar_nota(c, a, pa, "DOC-IGUAL", 100), criar_nota(c, b, pb, "DOC-IGUAL", 900)
    assert na == nb
    for token, value in ((a, 25), (b, 75)):
        payment = c.post("/pagamentos", headers=token, json={"tipo": "cliente_loja", "forma": "dinheiro", "valor": value,
            "data": "2026-10-03", "cliente_id": pa, "referencia_externa": "MESMA-REFERENCIA",
            "observacao": "Pagamento independente", "chave_idempotencia": "mesma-chave", "declaracao_novo_pagamento": True})
        assert payment.status_code == 201, payment.text
        assert payment.json()["id"] == 1
    for token, nome, valor, proibido in ((a, "Cliente loja A", 100, "Cliente loja B"), (b, "Cliente loja B", 900, "Cliente loja A")):
        assert c.get(f"/pessoas/{pa}", headers=token).json()["nome"] == nome
        assert c.get(f"/notas/{na}", headers=token).json()["valor_original"] == valor
        resumo = c.get("/visao-geral/resumo", headers=token)
        assert resumo.status_code == 200, resumo.text
        assert resumo.json()["fluxo_caixa"]["entradas_cliente_loja"] == (25 if valor == 100 else 75)
        csv = c.get("/visao-geral/export.csv?relacao=cliente", headers=token)
        assert csv.status_code == 200 and nome in csv.text and proibido not in csv.text
    cancelar = c.post(f"/notas/{na}/cancelar", headers=a, json={"motivo": "Cancelar somente loja A", "senha": "senha-teste"})
    assert cancelar.status_code == 200, cancelar.text
    assert c.get(f"/notas/{nb}", headers=b).json()["status"] == "aberto"
    assert c.get("/pessoas", headers=h[1]).json() == []


def test_contexto_assinado_membro_revogado_e_headers_nao_escolhem_banco(ambiente_api):
    c, h, sessions, _ = ambiente_api
    a = provisionar(c, h[2], 2)
    assert c.get("/pessoas", headers={**h[1], "X-Organizacao-Id": "2"}).status_code == 403
    assert c.get("/pessoas", headers={**a, "X-Organizacao-Id": "3"}).status_code == 403
    assert c.post("/organizacoes/2/selecionar", headers=h[1]).status_code == 403
    with sessions() as db:
        db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id == 2, VinculoOrganizacao.organizacao_id == 2)).ativo = False
        db.commit()
    assert c.get("/pessoas", headers=a).status_code == 403
    assert c.post("/organizacoes/2/selecionar", headers=h[2]).status_code == 403


def test_perfil_do_vinculo_sem_promocao_global_e_sem_acesso_fornecedor(ambiente_api):
    c, h, _, _ = ambiente_api
    a = provisionar(c, h[2], 2)
    assert criar_cliente(c, a, "Permitido pelo vínculo") > 0
    consulta = selecionar(c, h[3], 2)
    assert c.get("/pessoas", headers=consulta).status_code == 200
    assert c.post("/pessoas", headers=consulta, json={"tipo": "cliente", "nome": "Não permitido"}).status_code == 403
    fornecedor = c.post("/organizacoes/2/selecionar", headers=h[4])
    assert fornecedor.status_code == 403
    assert c.get("/auth/users", headers=a).status_code == 403
    assert c.post("/auth/users", headers=a, json={"nome": "Intruso", "email": "intruso@teste.local", "senha": "senha-teste", "perfil": "admin"}).status_code == 403


def test_senha_e_identidade_central_apos_selecao_sem_segredos_copiados(ambiente_api):
    c, h, sessions, tmp = ambiente_api
    a = provisionar(c, h[2], 2)
    assert criar_cliente(c, a, "Identidade central") > 0
    r = c.post("/auth/me/password", headers=a, json={"senha_atual": "senha-teste", "nova": "senha-nova-segura"})
    assert r.status_code == 200, r.text
    with sessions() as db:
        assert check_pw("senha-nova-segura", db.get(User, 2).senha_hash)
    assert c.get("/pessoas", headers=a).status_code == 401
    novo = c.post("/auth/login", json={"email": "lojas@teste.local", "senha": "senha-nova-segura"})
    assert novo.status_code == 200, novo.text
    import sqlite3
    paths = list((tmp / "financeiro").rglob("*.sqlite3"))
    assert len(paths) == 1
    for path in paths:
        with sqlite3.connect(path) as conn:
            names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "users" in names:
                rows = conn.execute("SELECT senha_hash, email FROM users").fetchall()
                assert rows
                assert all(not password.startswith("pbkdf2$") and email != "lojas@teste.local" for password, email in rows)


def test_provisionamento_admin_idempotente_sem_reinicializar_dados(ambiente_api):
    c, h, _, _ = ambiente_api
    assert c.post("/organizacoes/2/provisionar", headers=h[3]).status_code == 403
    assert c.post("/organizacoes/2/provisionar", headers=h[1]).status_code == 403
    a = provisionar(c, h[2], 2)
    pid = criar_cliente(c, a, "Preservar após reinício")
    assert c.post("/organizacoes/2/provisionar", headers=h[2]).status_code in (200, 201)
    assert c.get(f"/pessoas/{pid}", headers=a).json()["nome"] == "Preservar após reinício"
    assert c.post("/organizacoes/4/selecionar", headers=h[2]).status_code == 403


def test_claim_invalido_e_organizacao_inativa_falham_fechados(ambiente_api):
    c, h, sessions, _ = ambiente_api
    from jose import jwt
    from app.config import SECRET_KEY, ALGORITHM
    raw = h[2]["Authorization"][7:]
    data = jwt.decode(raw, SECRET_KEY, algorithms=[ALGORITHM])
    for claim in (True, "2", -2, 0):
        signed = jwt.encode({**data, "org": claim}, SECRET_KEY, ALGORITHM)
        assert c.get("/pessoas", headers={"Authorization": f"Bearer {signed}"}).status_code == 401
    a = provisionar(c, h[2], 2)
    with sessions() as db:
        db.get(Organizacao, 2).ativo = False
        db.commit()
    assert c.get("/pessoas", headers=a).status_code == 403


def test_extratos_publicos_segredos_confinados_e_revogacao_do_autor(ambiente_api):
    c, h, sessions, _ = ambiente_api
    headers = [provisionar(c, h[2], org) for org in (2, 3)]
    secrets = []
    for org, token in zip((2, 3), headers):
        pessoa = criar_cliente(c, token, f"Cliente da loja {org}")
        criar_nota(c, token, pessoa, "NOTA-MESMO-ID", org * 100)
        r = c.post(f"/extratos/{pessoa}/compartilhamentos", headers=token,
            json={"relacao": "cliente", "destinatario": "Cliente", "validade_dias": 7})
        assert r.status_code == 201, r.text
        assert r.json()["organizacao_id"] == org
        secrets.append({"Authorization": f"Bearer {r.json()['token']}"})
    for org, secret in zip((2, 3), secrets):
        r = c.get(f"/lojas/{org}/publico/extratos", headers=secret)
        assert r.status_code == 200, r.text
        assert r.json()["notas"]["itens"][0]["valor_original"] == org * 100
        assert r.headers["cache-control"] == "private, no-store"
        assert c.get(f"/lojas/{5-org}/publico/extratos", headers=secret).status_code == 404
        assert c.get("/publico/extratos", headers=secret).status_code == 404
        assert c.get(f"/lojas/{org}/pessoas", headers=secret).status_code == 404
    with sessions() as db:
        db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id == 2, VinculoOrganizacao.organizacao_id == 2)).ativo = False
        db.commit()
    assert c.get("/lojas/2/publico/extratos", headers=secrets[0]).status_code == 404
    assert c.get("/lojas/3/publico/extratos", headers=secrets[1]).status_code == 200


def test_arquivos_notas_mesmos_ids_raizes_e_conteudo_distintos(ambiente_api, monkeypatch):
    c, h, _, tmp = ambiente_api
    from app.routers import notas
    from app.models import NotaAnexo
    monkeypatch.setattr(notas, "UPLOAD_DIR", str(tmp / "uploads"))
    headers = [provisionar(c, h[2], org) for org in (2, 3)]
    for org, token in zip((2, 3), headers):
        pessoa = criar_cliente(c, token, f"Cliente loja {org}")
        nota = criar_nota(c, token, pessoa, "DOC-MESMO-ID", 100)
        assert nota == 1
        content = f"%PDF-1.4 arquivo privado loja {org}".encode()
        r = c.post("/notas/1/anexos", headers=token, files={"f": ("../../nota.pdf", content, "application/pdf")})
        assert r.status_code == 201, r.text
        assert r.json()["id"] == 1 and r.json()["nome_original"] == "nota.pdf"
        download = c.get("/notas/1/anexos/1/arquivo", headers=token)
        assert download.status_code == 200 and download.content == content
        assert download.headers["cache-control"] == "private, no-store"
        assert download.headers["x-content-type-options"] == "nosniff"
    # Uma referência de banco adulterada para a outra raiz não permite leitura cruzada.
    factory = ambientes._sessions(str(tmp / "financeiro" / "organizacao-2.sqlite3"))
    other = next((tmp / "uploads" / "organizacoes" / "3" / "notas" / "1").iterdir())
    with factory() as db:
        db.get(NotaAnexo, 1).arquivo_path = str(other)
        db.commit()
    assert c.get("/notas/1/anexos/1/arquivo", headers=headers[0]).status_code == 404
    assert c.get("/notas/1/anexos/1/arquivo", headers=headers[1]).status_code == 200


def test_me_e_permissoes_refletem_papel_selecionado(ambiente_api):
    c, h, _, _ = ambiente_api
    admin = provisionar(c, h[2], 2)
    consulta = selecionar(c, h[3], 2)
    for headers, perfil in ((admin, "admin"), (consulta, "consulta")):
        me = c.get("/auth/me", headers=headers)
        assert me.status_code == 200 and me.json()["perfil"] == perfil
        assert me.json()["organizacao_id"] == 2
        permissoes = c.get("/auth/permissoes", headers=headers)
        assert permissoes.status_code == 200 and permissoes.json()["perfil"] == perfil
        acoes = permissoes.json()["acoes"]
        assert all(not item["permitido"] for item in acoes if item["rota"].startswith("/auth/users"))
        if perfil == "consulta":
            assert not any(item["metodo"] == "POST" and item["rota"] == "/pessoas" for item in acoes)


def test_links_manuais_publicos_sem_busca_cruzada_ou_integracao_global(ambiente_api, monkeypatch):
    c, h, sessions, _ = ambiente_api
    from app import checkto
    def proibido(**kwargs):
        raise AssertionError("Loja nova não pode chamar gateway global")
    monkeypatch.setattr(checkto, "criar_cobranca_pix", proibido)
    segredos = []
    for org in (2, 3):
        selected = provisionar(c, h[2], org)
        cliente = criar_cliente(c, selected, f"Cliente da loja {org}")
        fornecedor = c.post("/pessoas", headers=selected, json={"tipo": "fornecedor", "nome": f"Fornecedor da loja {org}",
            "chave_pix": f"fornecedor{org}@teste.local", "titular_chave": f"Fornecedor {org}"})
        assert fornecedor.status_code == 201, fornecedor.text
        link = c.post("/links", headers=selected, json={"representante_id": cliente, "fornecedor_id": fornecedor.json()["id"], "valor_fixo": 100})
        assert link.status_code == 201, link.text
        assert link.json()["id"] == 1 and link.json()["url"].startswith(f"/v/{org}/")
        assert not link.json()["tem_cobranca"]
        segredos.append(link.json()["token"])
        assert c.post("/links/1/cobrar", headers=selected).status_code == 503
    for org, token in zip((2, 3), segredos):
        correto = c.get(f"/lojas/{org}/links/v/{token}")
        assert correto.status_code == 200, correto.text
        assert correto.json()["chave_pix"] == f"fornecedor{org}@teste.local"
        assert correto.headers["cache-control"] == "private, no-store"
        assert c.get(f"/lojas/{5-org}/links/v/{token}").status_code == 404
        assert c.get(f"/links/v/{token}").status_code == 404
    with sessions() as db:
        db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id == 2, VinculoOrganizacao.organizacao_id == 2)).ativo = False
        db.commit()
    assert c.get(f"/lojas/2/links/v/{segredos[0]}").status_code == 404
    assert c.get(f"/lojas/3/links/v/{segredos[1]}").status_code == 200


def test_admin_original_nao_altera_identidade_interna_compartilhada(ambiente_api):
    c, h, sessions, _ = ambiente_api
    selected = provisionar(c, h[2], 2)
    with sessions() as db:
        db.add(VinculoOrganizacao(user_id=2, organizacao_id=1, perfil="operador"))
        original = db.get(User, 2)
        snapshot = (original.nome, original.email, original.perfil, original.ativo, original.senha_hash)
        db.commit()
    for payload in ({"nome": "Tomada da identidade"}, {"email": "atacante@teste.local"}, {"ativo": False}, {"perfil": "admin"}):
        denied = c.patch("/auth/users/2", headers=h[1], json=payload)
        assert denied.status_code == 403, denied.text
    reset = c.post("/auth/users/2/password", headers=h[1], json={"senha": "senha-do-atacante"})
    assert reset.status_code == 403, reset.text
    with sessions() as db:
        original = db.get(User, 2)
        assert (original.nome, original.email, original.perfil, original.ativo, original.senha_hash) == snapshot
    assert c.get("/pessoas", headers=selected).status_code == 200
    own = c.post("/auth/me/password", headers=selected, json={"senha_atual": "senha-teste", "nova": "senha-propria-nova"})
    assert own.status_code == 200, own.text
    with sessions() as db:
        assert check_pw("senha-propria-nova", db.get(User, 2).senha_hash)
