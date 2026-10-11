"""Projeção automática: compõe PIX × dívida na ordem do rodízio, só com aprovação."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.models import AuditLog, Base, User
from app.auth import hash_pw, token_for
from app.routers.pessoas import r as pessoas_router
from app.routers.financeiro import rp, rl
from app.routers.movimentacoes import r as mov_router


@pytest.fixture
def api_auto():
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
    test_app.include_router(rp)
    test_app.include_router(rl)
    test_app.include_router(mov_router)
    test_app.dependency_overrides[get_db] = override_db
    with TestClient(test_app) as client:
        yield client, factory, {"Authorization": f"Bearer {tok}"}
    engine.dispose()


def test_propoe_aplica_e_respeita_rn006(api_auto):
    client, factory, H = api_auto
    rep = client.post("/representantes", json={"tipo": "representante", "nome": "Rep Auto"},
                      headers=H).json()
    fa = client.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn A",
                                            "prioridade": 1}, headers=H).json()
    fb = client.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn B"},
                     headers=H).json()
    client.post("/lancamentos", json={"tipo": "debito", "valor": 1000, "data": "2026-08-10",
                                      "fornecedor_id": fa["id"]}, headers=H)
    client.post("/lancamentos", json={"tipo": "debito", "valor": 200, "data": "2026-08-01",
                                      "fornecedor_id": fb["id"]}, headers=H)
    client.post("/movimentacoes", json={"data_pix": "2026-09-08", "valor": 400,
                                        "representante_id": rep["id"],
                                        "fornecedor_id": fa["id"]}, headers=H)
    client.post("/movimentacoes", json={"data_pix": "2026-09-08", "valor": 500,
                                        "representante_id": rep["id"],
                                        "fornecedor_id": fb["id"]}, headers=H)

    prev = client.post("/projecoes/automaticas", headers=H)
    assert prev.status_code == 200, prev.text
    prev = prev.json()
    assert prev["aplicado"] is False
    assert len(prev["propostas"]) == 2
    # ordem do rodízio: prioridade 1 antes
    assert prev["propostas"][0]["fornecedor_id"] == fa["id"]
    assert prev["propostas"][0]["valor_proposto"] == 400
    assert prev["propostas"][0]["ja_existe"] is False
    assert prev["propostas"][1]["valor_proposto"] == 200

    ap = client.post("/projecoes/automaticas?aplicar=true", headers=H)
    assert ap.status_code == 200, ap.text
    ap = ap.json()
    assert ap["aplicado"] is True and len(ap["criadas"]) == 2
    assert ap["ignoradas"] == []
    projs = client.get("/projecoes", headers=H).json()
    assert len(projs) == 2
    assert {p["valor_projetado"] for p in projs} == {400, 200}
    assert {c["valor_projetado"] for c in ap["criadas"]} == {400, 200}

    # segunda aplicação: RN-006 barra tudo como já existente
    ap2 = client.post("/projecoes/automaticas?aplicar=true", headers=H).json()
    assert ap2["criadas"] == [] and len(ap2["ignoradas"]) == 2
    db = factory()
    try:
        autos = db.query(AuditLog).filter_by(acao="projecao_criada").all()
        assert sum(1 for a in autos if "automatica" in (a.depois or "")) == 2
    finally:
        db.close()


def test_sem_pix_ou_sem_divida_nao_propoe(api_auto):
    client, _, H = api_auto
    rep = client.post("/representantes", json={"tipo": "representante", "nome": "Rep Z"},
                      headers=H).json()
    f = client.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn Z"},
                    headers=H).json()
    # só dívida, sem PIX
    client.post("/lancamentos", json={"tipo": "debito", "valor": 100, "data": "2026-09-01",
                                      "fornecedor_id": f["id"]}, headers=H)
    assert client.post("/projecoes/automaticas", headers=H).json()["propostas"] == []
    # só PIX, sem dívida
    f2 = client.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn Y"},
                     headers=H).json()
    client.post("/movimentacoes", json={"data_pix": "2026-09-08", "valor": 50,
                                        "representante_id": rep["id"],
                                        "fornecedor_id": f2["id"]}, headers=H)
    props = client.post("/projecoes/automaticas", headers=H).json()["propostas"]
    assert all(p["fornecedor_id"] != f2["id"] for p in props)
