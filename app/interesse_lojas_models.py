"""Solicitações privadas de avaliação comercial, sem vínculo com contas financeiras."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, _now


class InteresseLoja(Base):
    __tablename__ = 'interesse_lojas'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome_contato: Mapped[str] = mapped_column(String(120))
    loja_nome: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(160))
    whatsapp: Mapped[str] = mapped_column(String(13))
    cidade: Mapped[str] = mapped_column(String(120))
    uf: Mapped[str] = mapped_column(String(2))
    segmento: Mapped[str] = mapped_column(String(30))
    equipe: Mapped[str] = mapped_column(String(20))
    vendas_pix_mes: Mapped[str] = mapped_column(String(20))
    fornecedores: Mapped[str] = mapped_column(String(20))
    modelo_venda: Mapped[str] = mapped_column(String(30))
    controle_atual: Mapped[str] = mapped_column(String(30))
    desafio: Mapped[str] = mapped_column(Text)
    consentimento: Mapped[bool] = mapped_column(Boolean)
    consentimento_versao: Mapped[str] = mapped_column(String(40), default='loja-interesse-v1')
    status: Mapped[str] = mapped_column(String(20), default='novo', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
