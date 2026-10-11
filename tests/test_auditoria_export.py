"""Auditoria: filtros por ação/usuário + IP na saída + export CSV (respeita filtros)."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import IPMiddleware
from app.models import Base, User
from app.auth import hash_pw, token_for
from app.routers.dashboard import r as dash_router
from app.routers.export import r as export_router
from app.routers.movimentacoes import r as mov_router


@pytest.fixture
def api_audit():
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
    test_app.add_middleware(IPMiddleware)
    test_app.include_router(dash_router)
    test_app.include_router(export_router)
    test_app.include_router(mov_router)
    test_app.dependency_overrides[get_db] = override_db
    with TestClient(test_app) as client:
        yield (client,
               {"Authorization": f"Bearer {tok_admin}"},
               {"Authorization": f"Bearer {tok_op}"})
    engine.dispose()


def test_auditoria_filtra_e_expoe_ip(api_audit):
    client, admin, oper = api_audit
    client.post("/movimentacoes", json={"data_pix": "2026-09-08", "valor": 10},
                headers=admin)
    todas = client.get("/auditoria", headers=admin).json()
    assert len(todas) >= 1
    assert "ip" in todas[0]
    assert todas[0]["ip"] == "testclient"

    so_criacao = client.get("/auditoria?acao=movimentacao_criada", headers=admin).json()
    assert len(so_criacao) >= 1
    assert all("movimentacao_criada" in a["acao"] for a in so_criacao)

    vazia = client.get("/auditoria?acao=acao_que_nao_existe", headers=admin).json()
    assert vazia == []

    por_usuario = client.get("/auditoria?usuario_id=1", headers=admin).json()
    assert len(por_usuario) >= 1
    assert all(a["usuario_id"] == 1 for a in por_usuario)

    # operador não tem acesso à auditoria
    assert client.get("/auditoria", headers=oper).status_code == 403
    assert client.get("/export/auditoria.csv", headers=oper).status_code == 403


def test_export_auditoria_csv_respeita_filtros(api_audit):
    client, admin, _ = api_audit
    client.post("/movimentacoes", json={"data_pix": "2026-09-08", "valor": 10},
                headers=admin)
    r = client.get("/export/auditoria.csv?acao=movimentacao_criada", headers=admin)
    assert r.status_code == 200, r.text
    texto = r.content.decode("utf-8-sig")
    linhas = texto.splitlines()
    assert linhas[0].startswith("id;acao;entidade")
    assert any("movimentacao_criada" in l for l in linhas[1:])
    assert 'attachment; filename=' in r.headers["content-disposition"]


def test_export_mov_respeita_chave_e_link(api_audit):
    client, admin, _ = api_audit
    a = client.post("/movimentacoes",
                    json={"data_pix": "2026-09-08", "valor": 11,
                          "remetente": "CHAVE EXPORT", "link_token": "tok-exp"},
                    headers=admin).json()
    b = client.post("/movimentacoes",
                    json={"data_pix": "2026-09-08", "valor": 12,
                          "remetente": "OUTRO"},
                    headers=admin).json()

    r = client.get("/export/movimentacoes.csv?chave=chave+export", headers=admin)
    texto = r.content.decode("utf-8-sig")
    assert f"11.00" in texto and "12.00" not in texto

    r = client.get("/export/movimentacoes.csv?com_link=true", headers=admin)
    texto = r.content.decode("utf-8-sig")
    assert "11.00" in texto and "12.00" not in texto
    assert a["id"] and b["id"]
