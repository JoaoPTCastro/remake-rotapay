"""Prioridade de pagamento: padrão por fornecedor (1 alta/2 normal/3 baixa),
override por lançamento (null = herda do fornecedor)."""
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
from app.routers.financeiro import rp, rl


@pytest.fixture
def api_prio():
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
    db.add(User(nome="Op", email="op@local",
                senha_hash=hash_pw("op123456"), perfil="operador"))
    db.commit()
    tok_admin = token_for(db.query(User).filter_by(email="admin@local").first())
    tok_op = token_for(db.query(User).filter_by(email="op@local").first())
    db.close()

    def override_db():
        s = factory()
        try:
            yield s
        finally:
            s.close()

    test_app = FastAPI()
    test_app.include_router(pessoas_router)
    test_app.include_router(rp)
    test_app.include_router(rl)
    test_app.dependency_overrides[get_db] = override_db
    with TestClient(test_app) as client:
        yield (client,
               {"Authorization": f"Bearer {tok_admin}"},
               {"Authorization": f"Bearer {tok_op}"})
    engine.dispose()


def test_prioridade_padrao_e_edicao_fornecedor(api_prio):
    client, admin, _ = api_prio
    f = client.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn Prio"},
                    headers=admin)
    assert f.status_code == 201, f.text
    fid = f.json()["id"]
    assert client.get("/fornecedores", headers=admin).json()[0]["prioridade"] == 2

    assert client.patch(f"/pessoas/{fid}", json={"prioridade": 1},
                        headers=admin).status_code == 200
    assert client.get("/fornecedores", headers=admin).json()[0]["prioridade"] == 1
    assert client.patch(f"/pessoas/{fid}", json={"prioridade": 9},
                        headers=admin).status_code == 422


def test_override_por_lancamento(api_prio):
    client, admin, oper = api_prio
    fid = client.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn P2"},
                      headers=admin).json()["id"]
    base = {"tipo": "debito", "valor": 100, "data": "2026-09-01", "fornecedor_id": fid}
    sem = client.post("/lancamentos", json=base, headers=admin)
    assert sem.status_code == 201, sem.text
    com = client.post("/lancamentos", json={**base, "prioridade": 1}, headers=admin)
    assert com.status_code == 201, com.text
    ruim = client.post("/lancamentos", json={**base, "prioridade": 0}, headers=admin)
    assert ruim.status_code == 422

    lancs = {l["id"]: l for l in client.get("/lancamentos", headers=admin).json()}
    sem_id = sem.json()["id"]
    assert lancs[sem_id]["prioridade"] is None
    assert lancs[com.json()["id"]]["prioridade"] == 1
    # operador não edita pessoa
    assert client.patch(f"/pessoas/{fid}", json={"prioridade": 3},
                        headers=oper).status_code == 403
