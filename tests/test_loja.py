"""Perfil da loja: linha única, leitura para todos, edição só admin/financeiro."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.models import AuditLog, Base, User
from app.auth import hash_pw, token_for
from app.routers.loja import r as loja_router


@pytest.fixture
def loja_api():
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
    admin = db.query(User).filter_by(email="admin@local").first()
    oper = db.query(User).filter_by(email="op@local").first()
    tok_admin = token_for(admin)
    tok_op = token_for(oper)
    db.close()

    def override_db():
        s = factory()
        try:
            yield s
        finally:
            s.close()

    test_app = FastAPI()
    test_app.include_router(loja_router)
    test_app.dependency_overrides[get_db] = override_db
    with TestClient(test_app) as client:
        yield client, factory, {"Authorization": f"Bearer {tok_admin}"}, \
            {"Authorization": f"Bearer {tok_op}"}
    engine.dispose()


def test_loja_nasce_com_padrao(loja_api):
    client, _, admin, _ = loja_api
    r = client.get("/loja", headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["nome"] == "Minha Loja"


def test_admin_atualiza_e_persiste(loja_api):
    client, factory, admin, _ = loja_api
    r = client.patch("/loja", json={"nome": "Loja da Esquina",
                                    "telefone": "(11) 99999-0000"}, headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["nome"] == "Loja da Esquina"
    assert client.get("/loja", headers=admin).json()["telefone"] == "(11) 99999-0000"
    db = factory()
    try:
        acoes = {a.acao for a in db.query(AuditLog).filter_by(entidade="loja").all()}
    finally:
        db.close()
    assert "loja_atualizada" in acoes


def test_operador_nao_edita(loja_api):
    client, _, admin, oper = loja_api
    assert client.get("/loja", headers=oper).status_code == 200
    assert client.patch("/loja", json={"nome": "X"}, headers=oper).status_code == 403
    assert client.patch("/loja", json={"nome": "X"}).status_code in (401, 403)
    assert client.get("/loja", headers=admin).json()["nome"] == "Minha Loja"


def test_nome_curto_recusado(loja_api):
    client, _, admin, _ = loja_api
    assert client.patch("/loja", json={"nome": "A"}, headers=admin).status_code == 422
