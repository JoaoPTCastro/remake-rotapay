import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.models import AuditLog, Base, User
from app.routers.auth import r as auth_router


@pytest.fixture
def users_api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    test_app = FastAPI()
    test_app.include_router(auth_router)
    test_app.dependency_overrides[get_db] = override_db
    with TestClient(test_app) as client:
        yield client, session_factory
    engine.dispose()


def admin_headers(client):
    assert client.post("/auth/seed-admin").status_code == 200
    response = client.post(
        "/auth/login",
        json={"email": "admin@local", "senha": "admin123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_user(client, headers, **overrides):
    payload = {
        "nome": "Pessoa Operadora",
        "email": "operadora@example.com",
        "senha": "Senha123!",
        "perfil": "operador",
    }
    payload.update(overrides)
    return client.post("/auth/users", json=payload, headers=headers)


def test_admin_lists_and_creates_users_without_exposing_password(users_api):
    client, session_factory = users_api
    headers = admin_headers(client)

    created = create_user(client, headers)

    assert created.status_code == 201, created.text
    assert created.json() == {
        "id": 2,
        "nome": "Pessoa Operadora",
        "email": "operadora@example.com",
        "perfil": "operador",
        "ativo": True,
    }
    listed = client.get("/auth/users", headers=headers)
    assert listed.status_code == 200
    assert [user["email"] for user in listed.json()] == [
        "admin@local",
        "operadora@example.com",
    ]
    assert all("senha" not in key and "hash" not in key for user in listed.json() for key in user)

    with session_factory() as db:
        user = db.query(User).filter(User.email == "operadora@example.com").one()
        assert user.senha_hash != "Senha123!"
        entry = db.query(AuditLog).filter(AuditLog.acao == "usuario_criado").one()
        audited = f"{entry.antes}{entry.depois}".lower()
        assert "senha123" not in audited
        assert "senha" not in audited
        assert "hash" not in audited


@pytest.mark.parametrize(
    "field,value",
    [
        ("nome", " "),
        ("email", "email-invalido"),
        ("senha", "curta"),
        ("perfil", "superadmin"),
    ],
)
def test_create_user_validates_input(users_api, field, value):
    client, _ = users_api
    headers = admin_headers(client)

    response = create_user(client, headers, **{field: value})

    assert response.status_code == 422


def test_create_user_rejects_duplicate_email_case_insensitively(users_api):
    client, _ = users_api
    headers = admin_headers(client)
    assert create_user(client, headers, email="Financeiro@Example.com").status_code == 201

    duplicate = create_user(client, headers, email="financeiro@example.com")

    assert duplicate.status_code == 409


def test_non_admin_cannot_manage_users(users_api):
    client, _ = users_api
    headers = admin_headers(client)
    created = create_user(client, headers)
    user_id = created.json()["id"]
    login = client.post(
        "/auth/login",
        json={"email": "operadora@example.com", "senha": "Senha123!"},
    )
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    responses = [
        client.get("/auth/users", headers=user_headers),
        create_user(client, user_headers, email="outra@example.com"),
        client.patch(
            f"/auth/users/{user_id}",
            json={"perfil": "financeiro"},
            headers=user_headers,
        ),
        client.post(
            f"/auth/users/{user_id}/password",
            json={"senha": "NovaSenha123!"},
            headers=user_headers,
        ),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403]


def test_admin_changes_profile_and_active_status_and_audits_changes(users_api):
    client, session_factory = users_api
    headers = admin_headers(client)
    user_id = create_user(client, headers).json()["id"]

    changed_profile = client.patch(
        f"/auth/users/{user_id}",
        json={"perfil": "financeiro"},
        headers=headers,
    )
    deactivated = client.patch(
        f"/auth/users/{user_id}",
        json={"ativo": False},
        headers=headers,
    )

    assert changed_profile.status_code == 200
    assert changed_profile.json()["perfil"] == "financeiro"
    assert deactivated.status_code == 200
    assert deactivated.json()["ativo"] is False
    with session_factory() as db:
        entries = db.query(AuditLog).filter(AuditLog.acao == "usuario_atualizado").all()
        assert len(entries) == 2
        assert json.loads(entries[0].antes)["perfil"] == "operador"
        assert json.loads(entries[0].depois)["perfil"] == "financeiro"
        assert all("senha" not in f"{entry.antes}{entry.depois}".lower() for entry in entries)


def test_admin_cannot_deactivate_self_or_remove_last_active_admin(users_api):
    client, _ = users_api
    headers = admin_headers(client)

    self_deactivation = client.patch(
        "/auth/users/1",
        json={"ativo": False},
        headers=headers,
    )
    last_admin_demotion = client.patch(
        "/auth/users/1",
        json={"perfil": "operador"},
        headers=headers,
    )

    assert self_deactivation.status_code == 422
    assert last_admin_demotion.status_code == 422


def test_admin_can_demote_self_when_another_active_admin_exists(users_api):
    client, _ = users_api
    headers = admin_headers(client)
    assert create_user(
        client,
        headers,
        nome="Segunda Admin",
        email="admin2@example.com",
        perfil="admin",
    ).status_code == 201

    response = client.patch(
        "/auth/users/1",
        json={"perfil": "consulta"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["perfil"] == "consulta"


def test_admin_resets_password_without_returning_or_auditing_it(users_api):
    client, session_factory = users_api
    headers = admin_headers(client)
    user_id = create_user(client, headers).json()["id"]

    reset = client.post(
        f"/auth/users/{user_id}/password",
        json={"senha": "NovaSenha123!"},
        headers=headers,
    )

    assert reset.status_code == 200
    assert reset.json() == {"ok": True}
    assert client.post(
        "/auth/login",
        json={"email": "operadora@example.com", "senha": "Senha123!"},
    ).status_code == 401
    assert client.post(
        "/auth/login",
        json={"email": "operadora@example.com", "senha": "NovaSenha123!"},
    ).status_code == 200
    with session_factory() as db:
        entry = db.query(AuditLog).filter(
            AuditLog.acao == "usuario_senha_redefinida"
        ).one()
        audited = f"{entry.antes}{entry.depois}".lower()
        assert "novasenha" not in audited
        assert "senha" not in audited
        assert "hash" not in audited


def test_login_aceita_email_com_maiusculas(users_api):
    client, _ = users_api
    admin = admin_headers(client)
    r = create_user(client, admin, email="Financeiro@Example.com", perfil="financeiro")
    assert r.status_code == 201, r.text
    ok = client.post("/auth/login",
                     json={"email": "financeiro@example.com", "senha": "Senha123!"})
    assert ok.status_code == 200, ok.text
    maius = client.post("/auth/login",
                        json={"email": "FINANCEIRO@EXAMPLE.COM", "senha": "Senha123!"})
    assert maius.status_code == 200, maius.text


def test_troca_propria_senha_e_sessao_antiga_expira(users_api):
    client, _ = users_api
    admin = admin_headers(client)
    create_user(client, admin, email="operador@example.com", perfil="operador")
    tok = client.post("/auth/login",
                      json={"email": "operador@example.com", "senha": "Senha123!"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    assert client.get("/auth/me", headers=H).status_code == 200

    errada = client.post("/auth/me/password",
                         json={"senha_atual": "errada", "nova": "NovaSenha1"}, headers=H)
    assert errada.status_code == 403

    curta = client.post("/auth/me/password",
                        json={"senha_atual": "Senha123!", "nova": "curta"}, headers=H)
    assert curta.status_code == 422

    ok = client.post("/auth/me/password",
                     json={"senha_atual": "Senha123!", "nova": "NovaSenha1"}, headers=H)
    assert ok.status_code == 200, ok.text
    # sessão antiga morre
    assert client.get("/auth/me", headers=H).status_code == 401
    # login com a nova funciona
    novo = client.post("/auth/login",
                       json={"email": "operador@example.com", "senha": "NovaSenha1"})
    assert novo.status_code == 200
    # login com a antiga falha
    assert client.post("/auth/login",
                       json={"email": "operador@example.com", "senha": "Senha123!"}).status_code == 401


def test_reset_admin_expira_sessao_do_usuario(users_api):
    client, _ = users_api
    admin = admin_headers(client)
    r = create_user(client, admin, email="redefinida@example.com", perfil="operador")
    uid = r.json()["id"]
    tok = client.post("/auth/login",
                      json={"email": "redefinida@example.com", "senha": "Senha123!"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    assert client.get("/auth/me", headers=H).status_code == 200
    assert client.post(f"/auth/users/{uid}/password",
                       json={"senha": "OutraSenha2"}, headers=admin).status_code == 200
    assert client.get("/auth/me", headers=H).status_code == 401


def test_seed_login_and_me_remain_available(users_api):
    client, _ = users_api
    headers = admin_headers(client)

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "nome": "Admin",
        "email": "admin@local",
        "perfil": "admin",
    }
