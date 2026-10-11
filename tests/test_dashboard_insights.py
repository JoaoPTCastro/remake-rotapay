from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import current_user
from app.database import get_db
from app.models import (Base, Comprovante, Conciliacao, Lancamento,
                        Movimentacao, Projecao, User)
from app.routers import dashboard as dashboard_router


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 9, 9)


@pytest.fixture
def dashboard_api(monkeypatch):
    monkeypatch.setattr(dashboard_router, "date", FixedDate, raising=False)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    identity = {"user": User(id=1, nome="Teste", email="teste@local",
                              senha_hash="x", perfil="admin")}

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    api = FastAPI()
    api.include_router(dashboard_router.r)
    api.dependency_overrides[get_db] = override_db
    api.dependency_overrides[current_user] = lambda: identity["user"]

    with TestClient(api) as client:
        yield client, session_factory, identity, engine

    engine.dispose()


def test_dashboard_mantem_resposta_legada_e_expoe_estado_vazio(dashboard_api):
    client, _, _, _ = dashboard_api

    response = client.get("/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert {"total_a_pagar", "pix_disponivel", "pix_pendentes",
            "pix_conciliados", "projecoes_abertas", "por_fornecedor"} <= body.keys()
    assert body["resumo_operacional"] == {
        "pix_pendentes": {"quantidade": 0, "saldo": 0.0},
        "pix_antigos": {"quantidade": 0, "saldo": 0.0, "limite_dias": 7},
        "comprovantes_aguardando": {"total": 0, "registro": 0, "revisao": 0},
        "obrigacoes_abertas": {"quantidade": 0, "saldo": 0.0},
        "obrigacoes_proximas": {"quantidade": 0, "saldo": 0.0,
                                 "janela_dias": 7},
        "conciliacoes_recentes": {"quantidade": 0, "valor": 0.0,
                                   "janela_dias": 7},
    }
    assert [item["codigo"] for item in body["insights"]] == [
        "pix_pendentes", "comprovantes_aguardando", "obrigacoes_abertas",
        "obrigacoes_proximas", "conciliacoes_recentes",
    ]
    assert all(item["nivel"] == "ok" for item in body["insights"])
    assert all(item["acao"] is None and item["destino"] is None
               for item in body["insights"])


def test_dashboard_resume_pendencias_com_janelas_e_insights_deterministas(dashboard_api):
    client, session_factory, _, engine = dashboard_api
    db = session_factory()
    db.add_all([
        Movimentacao(codigo="PIX-000001", data_pix=date(2026, 9, 2), valor=100,
                     saldo_disponivel=100, status="disponivel"),
        Movimentacao(codigo="PIX-000002", data_pix=date(2026, 9, 8), valor=80,
                     saldo_disponivel=30, status="parcial"),
        Movimentacao(codigo="PIX-000003", data_pix=date(2026, 9, 1), valor=50,
                     saldo_disponivel=0, status="conciliada"),
        Movimentacao(codigo="PIX-000004", data_pix=date(2026, 9, 1), valor=25,
                     saldo_disponivel=25, status="cancelada"),
        Comprovante(arquivo_path="recebido.pdf", etapa="recebido",
                    sugestao_status="nenhuma"),
        Comprovante(arquivo_path="revisao.pdf", etapa="registrado",
                    sugestao_status="pendente"),
        Comprovante(arquivo_path="ambos.pdf", etapa="recebido",
                    sugestao_status="pendente"),
        Comprovante(arquivo_path="concluido.pdf", etapa="registrado",
                    sugestao_status="aceita"),
        Lancamento(tipo="debito", valor=100, saldo_aberto=80,
                   data=date(2026, 9, 1), status="aberto"),
        Lancamento(tipo="despesa", valor=200, saldo_aberto=50,
                   data=date(2026, 9, 2), status="parcial"),
        Lancamento(tipo="credito", valor=999, saldo_aberto=999,
                   data=date(2026, 9, 3), status="aberto"),
        Lancamento(tipo="debito", valor=40, saldo_aberto=0,
                   data=date(2026, 9, 4), status="quitado"),
        Projecao(representante_id=1, fornecedor_id=1, valor_projetado=100,
                 valor_conciliado=20, data_prevista=date(2026, 9, 9), status="aberta"),
        Projecao(representante_id=2, fornecedor_id=2, valor_projetado=200,
                 valor_conciliado=50, data_prevista=date(2026, 9, 16), status="parcial"),
        Projecao(representante_id=3, fornecedor_id=3, valor_projetado=300,
                 valor_conciliado=0, data_prevista=date(2026, 9, 17), status="aberta"),
        Projecao(representante_id=4, fornecedor_id=4, valor_projetado=400,
                 valor_conciliado=0, data_prevista=date(2026, 9, 10), status="cancelada"),
        Conciliacao(movimentacao_id=1, alvo_tipo="lancamento", alvo_id=1,
                    valor=20, data=date(2026, 9, 9), estornada=False),
        Conciliacao(movimentacao_id=2, alvo_tipo="lancamento", alvo_id=2,
                    valor=30, data=date(2026, 9, 3), estornada=False),
        Conciliacao(movimentacao_id=3, alvo_tipo="lancamento", alvo_id=3,
                    valor=40, data=date(2026, 9, 2), estornada=False),
        Conciliacao(movimentacao_id=4, alvo_tipo="lancamento", alvo_id=4,
                    valor=50, data=date(2026, 9, 9), estornada=True),
    ])
    db.commit()
    db.close()

    selects = []

    def count_selects(_conn, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    event.listen(engine, "before_cursor_execute", count_selects)
    first = client.get("/dashboard")
    event.remove(engine, "before_cursor_execute", count_selects)
    second = client.get("/dashboard")

    assert first.status_code == 200
    body = first.json()
    # Autorização multiempresa acrescenta uma consulta fixa, sem N+1 financeiro.
    autorizacao = [stmt for stmt in selects if "vinculos_organizacao" in stmt]
    assert len(autorizacao) == 1
    assert len(selects) - len(autorizacao) <= 8
    assert body["total_a_pagar"] == 130.0
    assert body["pix_disponivel"] == 130.0
    assert body["pix_pendentes"] == 2
    assert body["pix_conciliados"] == 1
    assert body["projecoes_abertas"] == 3
    assert body["resumo_operacional"] == {
        "pix_pendentes": {"quantidade": 2, "saldo": 130.0},
        "pix_antigos": {"quantidade": 1, "saldo": 100.0, "limite_dias": 7},
        "comprovantes_aguardando": {"total": 3, "registro": 2, "revisao": 2},
        "obrigacoes_abertas": {"quantidade": 2, "saldo": 130.0},
        "obrigacoes_proximas": {"quantidade": 2, "saldo": 230.0,
                                 "janela_dias": 7},
        "conciliacoes_recentes": {"quantidade": 2, "valor": 50.0,
                                   "janela_dias": 7},
    }
    assert body["insights"] == second.json()["insights"]
    assert [(item["codigo"], item["nivel"], item["destino"])
            for item in body["insights"]] == [
        ("pix_pendentes", "atencao", "/movimentacoes"),
        ("comprovantes_aguardando", "atencao", "/movimentacoes"),
        ("obrigacoes_abertas", "atencao", "/lancamentos"),
        ("obrigacoes_proximas", "atencao", "/projecoes"),
        ("conciliacoes_recentes", "info", "/conciliacoes"),
    ]
    assert body["insights"][0]["mensagem"] == (
        "1 PIX está pendente há 7 dias ou mais. Revise as movimentações mais antigas.")


@pytest.mark.parametrize("perfil", ["admin", "financeiro", "operador", "consulta"])
def test_dashboard_preserva_perfis_autorizados(dashboard_api, perfil):
    client, _, identity, _ = dashboard_api
    identity["user"].perfil = perfil

    assert client.get("/dashboard").status_code == 200


def test_dashboard_rejeita_perfil_nao_autorizado(dashboard_api):
    client, _, identity, _ = dashboard_api
    identity["user"].perfil = "auditor"

    assert client.get("/dashboard").status_code == 403
