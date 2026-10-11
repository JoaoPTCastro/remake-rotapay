"""Registro central de ambientes provisionados; caminhos nunca vêm do cliente."""
from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, _now


class AmbienteOrganizacao(Base):
    __tablename__ = 'ambientes_organizacao'
    organizacao_id: Mapped[int] = mapped_column(ForeignKey('organizacoes.id'), primary_key=True)
    pronto: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
