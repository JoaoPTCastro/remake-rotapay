"""Fluxo isolado do OCR experimental para comprovantes legados e anexados manualmente."""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import hash_pw, token_for
from app.database import get_db
from app.main import app
from app.models import Base, Comprovante, Job, User, Movimentacao


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'ocr-pipeline.db'}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = session_factory()
    admin = User(
        nome="Admin OCR",
        email="admin-ocr@local",
        senha_hash=hash_pw("admin123"),
        perfil="admin",
    )
    consulta = User(
        nome="Consulta OCR",
        email="consulta-ocr@local",
        senha_hash=hash_pw("consulta123"),
        perfil="consulta",
    )
    db.add_all([admin, consulta])
    db.flush()
    admin_headers = {"Authorization": f"Bearer {token_for(admin)}"}
    consulta_headers = {"Authorization": f"Bearer {token_for(consulta)}"}
    comprovante = Comprovante(
        movimentacao_id=None,
        arquivo_path="/tmp/comprovante-legado.jpg",
        arquivo_hash="hash-ocr-pipeline",
        origem="upload",
        enviado_por="Cliente legado",
        etapa="recebido",
    )
    db.add(comprovante)
    db.flush()
    db.add(Job(tipo="comprovante", ref_id=comprovante.id, status="pendente"))
    db.commit()
    comprovante_id = comprovante.id
    db.close()

    previous_override = app.dependency_overrides.get(get_db)

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, session_factory, comprovante_id, admin_headers, consulta_headers

    if previous_override is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous_override
    engine.dispose()


def test_comprovante_aguarda_vinculo_e_reutiliza_job_ate_processar(pipeline, monkeypatch):
    client, session_factory, comprovante_id, admin_headers, consulta_headers = pipeline

    assert client.post("/jobs/processar", headers=consulta_headers).status_code == 403

    import app.routers.jobs as jobs_router

    chamadas_ocr = []
    extrair_original = jobs_router.extrair

    def registrar_chamada(*args, **kwargs):
        chamadas_ocr.append((args, kwargs))
        return extrair_original(*args, **kwargs)

    monkeypatch.setattr(jobs_router, "extrair", registrar_chamada)

    primeira_execucao = client.post("/jobs/processar", headers=admin_headers)
    assert primeira_execucao.status_code == 200, primeira_execucao.text
    assert primeira_execucao.json() == {"processados": 0, "aguardando_vinculo": 1, "ignorados": 0, "erros": 0}
    assert chamadas_ocr == []

    db = session_factory()
    job = db.query(Job).filter_by(tipo="comprovante", ref_id=comprovante_id).one()
    assert job.status == "aguardando_vinculo"
    assert "aguardando vínculo" in job.detalhe
    assert db.get(Comprovante, comprovante_id).extraido_json == ""

    # Ensaia retomada de documento legado vinculado sem reabrir a caixa removida.
    from datetime import date
    mov = Movimentacao(codigo="PIX-LEGADO", data_pix=date(2026, 9, 9),
                        valor=125, saldo_disponivel=125, remetente="Cliente legado")
    db.add(mov)
    db.flush()
    comprovante = db.get(Comprovante, comprovante_id)
    comprovante.movimentacao_id = mov.id
    comprovante.etapa = "registrado"
    job.status = "pendente"
    db.commit()
    db.close()

    segunda_execucao = client.post("/jobs/processar", headers=admin_headers)
    assert segunda_execucao.status_code == 200, segunda_execucao.text
    assert segunda_execucao.json() == {"processados": 1, "aguardando_vinculo": 0, "ignorados": 0, "erros": 0}
    assert len(chamadas_ocr) == 1

    db = session_factory()
    job = db.query(Job).filter_by(tipo="comprovante", ref_id=comprovante_id).one()
    comprovante = db.get(Comprovante, comprovante_id)
    assert job.status == "processado"
    assert "OCR experimental (simulado)" in job.detalhe
    assert json.loads(comprovante.extraido_json)["valor"]["valor"] == 125
    db.close()
