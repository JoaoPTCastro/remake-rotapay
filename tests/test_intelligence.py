from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_pw, token_for
from app.database import get_db
from app.intelligence import detectar_duplicidades, sugerir_conciliacoes
from app.models import Base, Lancamento, Movimentacao, Projecao, User
from app.routers.movimentacoes import r as movimentacoes_router


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _movimentacao(**overrides):
    data = {
        "codigo": "PIX-000001",
        "data_pix": date(2026, 9, 10),
        "valor": 100.0,
        "saldo_disponivel": 100.0,
        "fornecedor_id": 10,
        "representante_id": 20,
        "status": "disponivel",
    }
    data.update(overrides)
    return Movimentacao(**data)


def test_sugestoes_sao_deterministicas_conservadoras_e_nao_persistem(db):
    mov = _movimentacao()
    lancamento_exato = Lancamento(
        tipo="debito", valor=100, saldo_aberto=100, data=date(2026, 9, 9),
        fornecedor_id=10, status="aberto",
    )
    projecao_exata = Projecao(
        representante_id=20, fornecedor_id=10, valor_projetado=100,
        valor_conciliado=0, data_prevista=date(2026, 9, 11), status="aberta",
    )
    lancamento_parcial = Lancamento(
        tipo="despesa", valor=250, saldo_aberto=250, data=date(2026, 9, 8),
        fornecedor_id=10, status="aberto",
    )
    ignorados = [
        Lancamento(tipo="credito", valor=100, saldo_aberto=100, data=date(2026, 9, 10),
                   fornecedor_id=10, status="aberto"),
        Lancamento(tipo="debito", valor=100, saldo_aberto=100, data=date(2026, 9, 10),
                   fornecedor_id=99, status="aberto"),
        Lancamento(tipo="debito", valor=100, saldo_aberto=100, data=date(2026, 9, 10),
                   fornecedor_id=10, status="quitado"),
        Projecao(representante_id=99, fornecedor_id=10, valor_projetado=100,
                 valor_conciliado=0, data_prevista=date(2026, 9, 10), status="aberta"),
    ]
    db.add_all([mov, lancamento_exato, projecao_exata, lancamento_parcial, *ignorados])
    db.commit()

    sugestoes = sugerir_conciliacoes(db, mov)

    assert [(s["alvo_tipo"], s["alvo_id"]) for s in sugestoes] == [
        ("lancamento", lancamento_exato.id),
        ("projecao", projecao_exata.id),
        ("lancamento", lancamento_parcial.id),
    ]
    assert sugestoes[0]["valor_sugerido"] == 100.0
    assert sugestoes[0]["saldo_alvo"] == 100.0
    assert sugestoes[0]["confianca"] == "alta"
    assert "mesmo fornecedor" in sugestoes[0]["motivo"].lower()
    assert "saldo exato" in sugestoes[0]["motivo"].lower()
    assert sugestoes[2]["valor_sugerido"] == 100.0
    assert sugestoes[2]["confianca"] == "media"
    assert mov.saldo_disponivel == 100.0
    assert lancamento_exato.saldo_aberto == 100.0
    assert projecao_exata.valor_conciliado == 0.0
    assert not db.dirty and not db.new and not db.deleted


def test_sugestoes_exigem_movimentacao_e_fornecedor_elegiveis(db):
    sem_fornecedor = _movimentacao(codigo="PIX-000002", fornecedor_id=None)
    cancelada = _movimentacao(codigo="PIX-000003", status="cancelada")
    sem_saldo = _movimentacao(codigo="PIX-000004", saldo_disponivel=0, status="conciliada")
    db.add_all([sem_fornecedor, cancelada, sem_saldo])
    db.commit()

    assert sugerir_conciliacoes(db, sem_fornecedor) == []
    assert sugerir_conciliacoes(db, cancelada) == []
    assert sugerir_conciliacoes(db, sem_saldo) == []


def test_duplicidade_ignora_propria_linha_e_exige_tripla_exata(db):
    atual = _movimentacao()
    duplicada = _movimentacao(codigo="PIX-000002")
    db.add_all([
        atual,
        duplicada,
        _movimentacao(codigo="PIX-000003", valor=100.01),
        _movimentacao(codigo="PIX-000004", data_pix=date(2026, 9, 11)),
        _movimentacao(codigo="PIX-000005", fornecedor_id=11),
        _movimentacao(codigo="PIX-000006", status="cancelada"),
    ])
    db.commit()

    alertas = detectar_duplicidades(db, [atual])
    alerta = alertas[atual.id]

    assert alerta["possivel_duplicidade"] is True
    assert alerta["duplicidade_movimentacao_ids"] == [duplicada.id]
    assert atual.id not in alerta["duplicidade_movimentacao_ids"]
    assert alerta["duplicidade_criterio"] == "Mesmo fornecedor, valor e data PIX."


def test_duplicidade_sem_fornecedor_ou_par_unico_nao_gera_alerta(db):
    unica = _movimentacao()
    sem_fornecedor = _movimentacao(codigo="PIX-000002", fornecedor_id=None)
    db.add_all([unica, sem_fornecedor])
    db.commit()

    alertas = detectar_duplicidades(db, [unica, sem_fornecedor])

    assert alertas[unica.id]["possivel_duplicidade"] is False
    assert alertas[sem_fornecedor.id]["possivel_duplicidade"] is False
    assert alertas[unica.id]["duplicidade_criterio"] is None


@pytest.fixture
def api(db):
    user = User(
        nome="Consulta",
        email="consulta@local",
        senha_hash=hash_pw("segredo"),
        perfil="consulta",
        ativo=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    test_app = FastAPI()
    test_app.include_router(movimentacoes_router)

    def override_db():
        yield db

    test_app.dependency_overrides[get_db] = override_db
    with TestClient(test_app) as client:
        yield client, {"Authorization": f"Bearer {token_for(user)}"}


def test_endpoint_autenticado_expoe_sugestoes_sem_alterar_dados(api, db):
    client, auth = api
    mov = _movimentacao()
    alvo = Lancamento(
        tipo="debito", valor=100, saldo_aberto=100, data=date(2026, 9, 9),
        fornecedor_id=10, status="aberto",
    )
    db.add_all([mov, alvo])
    db.commit()

    assert client.get(f"/movimentacoes/{mov.id}/sugestoes").status_code in (401, 403)
    response = client.get(f"/movimentacoes/{mov.id}/sugestoes", headers=auth)

    assert response.status_code == 200, response.text
    assert response.json()["movimentacao_id"] == mov.id
    assert response.json()["sugestoes"][0]["alvo_id"] == alvo.id
    db.refresh(mov)
    db.refresh(alvo)
    assert mov.status == "disponivel" and mov.saldo_disponivel == 100.0
    assert alvo.status == "aberto" and alvo.saldo_aberto == 100.0


def test_listagem_e_detalhe_expoem_alerta_de_duplicidade(api, db):
    client, auth = api
    atual = _movimentacao()
    duplicada = _movimentacao(codigo="PIX-000002")
    db.add_all([atual, duplicada])
    db.commit()

    listagem = client.get("/movimentacoes", headers=auth)
    detalhe = client.get(f"/movimentacoes/{atual.id}", headers=auth)

    assert listagem.status_code == 200, listagem.text
    item = next(row for row in listagem.json() if row["id"] == atual.id)
    assert item["possivel_duplicidade"] is True
    assert item["duplicidade_movimentacao_ids"] == [duplicada.id]
    assert detalhe.status_code == 200, detalhe.text
    assert detalhe.json()["possivel_duplicidade"] is True
    assert detalhe.json()["duplicidade_movimentacao_ids"] == [duplicada.id]
