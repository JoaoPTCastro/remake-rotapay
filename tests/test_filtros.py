"""Filtros do Controle: por chave (remetente/destinatário/chave do fornecedor) e por link."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.models import Base, User
from app.auth import hash_pw, token_for
from app.routers.movimentacoes import r as mov_router
from app.routers.pessoas import r as pessoas_router


@pytest.fixture
def api_mov():
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
    admin = db.query(User).filter_by(email="admin@local").first()
    tok = token_for(admin)
    db.close()

    def override_db():
        s = factory()
        try:
            yield s
        finally:
            s.close()

    test_app = FastAPI()
    test_app.include_router(mov_router)
    test_app.include_router(pessoas_router)
    test_app.dependency_overrides[get_db] = override_db
    with TestClient(test_app) as client:
        yield client, {"Authorization": f"Bearer {tok}"}
    engine.dispose()


def _criar(client, H, **kw):
    base = {"data_pix": "2026-09-02", "valor": 10}
    base.update(kw)
    r = client.post("/movimentacoes", json=base, headers=H)
    assert r.status_code == 201, r.text
    return r.json()


def test_filtro_chave_casa_remetente_destinatario_e_chave_fornecedor(api_mov):
    client, H = api_mov
    f = client.post("/fornecedores", json={"tipo": "fornecedor", "nome": "Forn Chave",
                                           "chave_pix": "chave-unica-123"},
                    headers=H)
    assert f.status_code == 201, f.text
    fid = f.json()["id"]
    a = _criar(client, H, remetente="JOAO TESTE", destinatario="LOJA")
    b = _criar(client, H, remetente="OUTRO", destinatario="chave-unica-123")
    c = _criar(client, H, remetente="TERCEIRO")
    d = _criar(client, H, remetente="ZZZ", destinatario="YYY", fornecedor_id=fid)

    r = client.get("/movimentacoes?chave=joao", headers=H).json()
    assert {m["id"] for m in r} == {a["id"]}

    r = client.get("/movimentacoes?chave=chave-unica", headers=H).json()
    assert {m["id"] for m in r} == {b["id"], d["id"]}

    r = client.get("/movimentacoes", headers=H).json()
    assert {m["id"] for m in r} >= {a["id"], b["id"], c["id"], d["id"]}


def test_filtro_com_link(api_mov):
    client, H = api_mov
    a = _criar(client, H, link_token="tok-1")
    b = _criar(client, H)

    r = client.get("/movimentacoes?com_link=true", headers=H).json()
    assert a["id"] in {m["id"] for m in r}
    assert b["id"] not in {m["id"] for m in r}

    r = client.get("/movimentacoes?com_link=false", headers=H).json()
    assert b["id"] in {m["id"] for m in r}
    assert a["id"] not in {m["id"] for m in r}
