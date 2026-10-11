"""Link público: payload copia-e-cola local + flag de pago após registro."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.models import Base, User
from app.auth import hash_pw, token_for
from app.routers.pessoas import r as pessoas_router
from app.routers.links import r as links_router
from app.routers.movimentacoes import r as mov_router


@pytest.fixture
def api_link():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = factory()
    db.add(User(nome="Admin", email="admin@local",
                senha_hash=hash_pw("admin123"), perfil="admin"))
    db.commit()
    tok = token_for(db.query(User).filter_by(email="admin@local").first())
    db.close()

    def override_db():
        s = factory()
        try:
            yield s
        finally:
            s.close()

    test_app = FastAPI()
    test_app.include_router(pessoas_router)
    test_app.include_router(links_router)
    test_app.include_router(mov_router)
    test_app.dependency_overrides[get_db] = override_db
    with TestClient(test_app) as client:
        yield client, {"Authorization": f"Bearer {tok}"}
    engine.dispose()


def test_resolver_traz_payload_e_pago(api_link):
    client, H = api_link
    rep = client.post("/representantes",
                      json={"tipo": "representante", "nome": "Vendedor V"},
                      headers=H).json()
    forn = client.post("/fornecedores",
                       json={"tipo": "fornecedor", "nome": "Fornecedor F",
                             "chave_pix": "f@forn.com"},
                       headers=H).json()
    link = client.post("/links", json={"representante_id": rep["id"],
                                       "fornecedor_id": forn["id"],
                                       "valor_fixo": 460},
                       headers=H).json()
    tok = link["token"]

    antes = client.get(f"/links/v/{tok}")
    assert antes.status_code == 200, antes.text
    assert antes.json()["pago"] is False
    payload = antes.json()["payload_pix"]
    assert "BR.GOV.BCB.PIX" in payload and "f@forn.com" in payload
    assert "5406460.00" in payload

    mov = client.post("/movimentacoes",
                      json={"data_pix": "2026-09-08", "valor": 460,
                            "representante_id": rep["id"],
                            "fornecedor_id": forn["id"], "link_token": tok},
                      headers=H)
    assert mov.status_code == 201, mov.text
    depois = client.get(f"/links/v/{tok}").json()
    assert depois["pago"] is True


def _vendedor(client, H, nome, completo=True):
    base = {"tipo": "representante", "nome": nome}
    if completo:
        base.update({"email": "v@loja.com", "telefone": "(11) 99999-9999",
                     "documento": "123.456.789-00"})
    return client.post("/representantes", json=base, headers=H).json()


def _fornecedor(client, H, nome="Forn Auto"):
    return client.post("/fornecedores", json={"tipo": "fornecedor", "nome": nome,
                                              "chave_pix": "auto@forn.com"},
                       headers=H).json()


def test_cobranca_automatica_ao_gerar_link(api_link, monkeypatch):
    import app.checkto as ck
    monkeypatch.setattr(ck, "criar_cobranca_pix", lambda **kw: {
        "transactionId": "tx-auto", "webhookToken": "tok-auto",
        "pix": {"code": "000201auto", "image": "http://img/auto"}})
    client, H = api_link
    rep = _vendedor(client, H, "Vendedor Auto")
    forn = _fornecedor(client, H)
    link = client.post("/links", json={"representante_id": rep["id"],
                                       "fornecedor_id": forn["id"],
                                       "valor_fixo": 460}, headers=H)
    assert link.status_code == 201, link.text
    assert link.json()["tem_cobranca"] is True
    # /v já mostra o QR sem ninguém clicar em nada
    pub = client.get(f"/links/v/{link.json()['token']}").json()
    assert pub["pix_code"] == "000201auto"


def test_auto_cai_para_manual_sem_dados_ou_sem_gateway(api_link):
    client, H = api_link
    forn = _fornecedor(client, H, "Forn Manual")
    # vendedor incompleto -> link nasce manual, sem erro
    rep_pobre = _vendedor(client, H, "Vendedor Sem Dados", completo=False)
    m1 = client.post("/links", json={"representante_id": rep_pobre["id"],
                                     "fornecedor_id": forn["id"],
                                     "valor_fixo": 460}, headers=H)
    assert m1.status_code == 201, m1.text
    assert m1.json()["tem_cobranca"] is False
    # vendedor completo mas sem gateway configurado -> manual também
    rep_ok = _vendedor(client, H, "Vendedor Ok")
    m2 = client.post("/links", json={"representante_id": rep_ok["id"],
                                     "fornecedor_id": forn["id"],
                                     "valor_fixo": 460}, headers=H)
    assert m2.status_code == 201, m2.text
    assert m2.json()["tem_cobranca"] is False
    # manual continua valendo: copia-e-cola local no /v
    pub = client.get(f"/links/v/{m2.json()['token']}").json()
    assert "BR.GOV.BCB.PIX" in pub["payload_pix"]
