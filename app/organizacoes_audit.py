"""Auditoria de identidades e organizações separada do histórico financeiro."""
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, _now


class AuditOrganizacao(Base):
    __tablename__ = 'audit_organizacoes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    acao: Mapped[str] = mapped_column(String(60))
    entidade: Mapped[str] = mapped_column(String(60))
    entidade_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    antes: Mapped[str] = mapped_column(Text, default='')
    depois: Mapped[str] = mapped_column(Text, default='')
    ip: Mapped[str] = mapped_column(String(45), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


def identidade_compartilhada(db, user_id):
    from .models import User
    from .organizacoes_models import Organizacao, VinculoOrganizacao, FornecedorIdentidade
    if user_id is None or db.query(Organizacao.id).first() is None:
        return False
    user = db.get(User, user_id)
    if not user:
        return False
    if db.query(FornecedorIdentidade.id).filter_by(user_id=user_id).first():
        return True
    return not db.query(VinculoOrganizacao.id).filter(
        VinculoOrganizacao.user_id == user_id, VinculoOrganizacao.organizacao_id == 1,
        VinculoOrganizacao.perfil.in_(('admin', 'financeiro', 'operador', 'consulta'))).first()
