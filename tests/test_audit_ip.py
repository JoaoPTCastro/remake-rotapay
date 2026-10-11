"""Auditoria com IP: middleware carimba, audit() registra, sem IP grava vazio."""
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.models import Base, AuditLog
from app.audit import audit, fixar_ip, soltar_ip
from app.main import IPMiddleware


@pytest.fixture
def api_ip():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_db():
        s = factory()
        try:
            yield s
        finally:
            s.close()

    test_app = FastAPI()
    test_app.add_middleware(IPMiddleware)

    @test_app.post("/probe")
    def probe(db: Session = Depends(get_db)):
        audit(db, 7, "teste_ip", "x", 1)
        db.commit()
        return {"ok": True}

    test_app.dependency_overrides[get_db] = override_db
    with TestClient(test_app) as client:
        yield client, factory
    engine.dispose()


def _ip(factory, acao="teste_ip"):
    db = factory()
    try:
        row = db.query(AuditLog).filter_by(acao=acao).order_by(AuditLog.id.desc()).first()
        return row.ip if row else None
    finally:
        db.close()


def test_middleware_registra_ip_do_cliente(api_ip):
    client, factory = api_ip
    assert client.post("/probe").status_code == 200
    assert _ip(factory) == "testclient"


def test_x_forwarded_for_tem_prioridade(api_ip):
    client, factory = api_ip
    assert client.post("/probe", headers={"x-forwarded-for": "1.2.3.4, 5.6.7.8"}).status_code == 200
    assert _ip(factory) == "1.2.3.4"


def test_sem_request_grava_vazio():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = factory()
    audit(db, None, "teste_ip", "x", 2)
    db.commit()
    assert _ip(factory) == ""
    db.close()
    engine.dispose()


def test_override_explicito_vence_contexto():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = factory()
    tok = fixar_ip("9.9.9.9")
    try:
        audit(db, None, "teste_ip", "x", 3, ip="1.1.1.1")
        db.commit()
    finally:
        soltar_ip(tok)
    assert _ip(factory) == "1.1.1.1"
    db.close()
    engine.dispose()
