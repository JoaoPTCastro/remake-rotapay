"""Fila do rodízio: nota mais antiga em aberto + faltante + ordem por fila."""
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
from app.routers.financeiro import rl, rc
from app.routers.dashboard import r as dash_router
from app.routers.movimentacoes import r as mov_router


@pytest.fixture
def api_fila():
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
    test_app.include_router(rl)
    test_app.include_router(rc)
    test_app.include_router(dash_router)
    test_app.include_router(mov_router)
    test_app.dependency_overrides[get_db] = override_db
    with TestClient(test_app) as client:
        yield client, {"Authorization": f"Bearer {tok}"}
    engine.dispose()


def test_fila_ordena_e_calcula_faltante(api_fila):
    client, H = api_fila
    fa = client.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn A",
                                            "prioridade": 1}, headers=H).json()
    fb = client.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn B",
                                            "prioridade": 3}, headers=H).json()
    # A: nota antiga parcial (faltam 300 de 1000) + nota nova de 500
    la1 = client.post("/lancamentos", json={"tipo": "debito", "valor": 1000,
                                            "data": "2026-08-22",
                                            "fornecedor_id": fa["id"]},
                      headers=H).json()
    la2 = client.post("/lancamentos", json={"tipo": "debito", "valor": 500,
                                            "data": "2026-09-05",
                                            "fornecedor_id": fa["id"]},
                      headers=H).json()
    # B: prioridade baixa mas nota bem antiga
    lb = client.post("/lancamentos", json={"tipo": "debito", "valor": 200,
                                           "data": "2026-08-01",
                                           "fornecedor_id": fb["id"]},
                     headers=H).json()
    # parcial de 700 na nota antiga de A
    pix = client.post("/movimentacoes", json={"data_pix": "2026-09-08", "valor": 900,
                                              "fornecedor_id": fa["id"]},
                      headers=H).json()
    cc = client.post("/conciliacoes", json={"movimentacao_id": pix["id"],
                                            "alvo_tipo": "lancamento",
                                            "alvo_id": la1["id"], "valor": 700},
                     headers=H)
    assert cc.status_code == 201, cc.text

    fila = client.get("/fila-pagamentos", headers=H)
    assert fila.status_code == 200, fila.text
    fila = fila.json()
    assert [f["fornecedor_id"] for f in fila] == [fa["id"], fb["id"]]
    a, b = fila
    assert a["nota_antiga"]["id"] == la1["id"]
    assert a["nota_antiga"]["data"] == "2026-08-22"
    assert a["faltante_nota_antiga"] == 300
    assert a["total_devido"] == 800
    assert a["pix_em_maos"] == 200
    assert a["quitavel_agora"] is False
    assert b["nota_antiga"]["id"] == lb["id"]
    assert b["quitavel_agora"] is False
    # sem débito em aberto, fornecedor some da fila
    assert {f["fornecedor_id"] for f in fila} == {fa["id"], fb["id"]}
    assert la2["id"] != a["nota_antiga"]["id"]


def test_fila_vazia_e_quitavel(api_fila):
    client, H = api_fila
    assert client.get("/fila-pagamentos", headers=H).json() == []
    f = client.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn Q"},
                    headers=H).json()
    lan = client.post("/lancamentos", json={"tipo": "debito", "valor": 100,
                                            "data": "2026-09-01",
                                            "fornecedor_id": f["id"]},
                      headers=H).json()
    pix = client.post("/movimentacoes", json={"data_pix": "2026-09-08", "valor": 150,
                                              "fornecedor_id": f["id"]},
                      headers=H).json()
    fila = client.get("/fila-pagamentos", headers=H).json()
    assert len(fila) == 1 and fila[0]["quitavel_agora"] is True
    assert fila[0]["nota_antiga"]["id"] == lan["id"]
    assert fila[0]["pix_em_maos"] == 150
