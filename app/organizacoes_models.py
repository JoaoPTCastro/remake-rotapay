"""Identidades e vínculos de acesso; separados dos fatos financeiros existentes."""
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, _now


class Organizacao(Base):
    __tablename__ = 'organizacoes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(160))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class VinculoOrganizacao(Base):
    __tablename__ = 'vinculos_organizacao'
    __table_args__ = (UniqueConstraint('user_id', 'organizacao_id'), CheckConstraint("perfil IN ('admin','financeiro','operador','consulta','fornecedor')"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    organizacao_id: Mapped[int] = mapped_column(ForeignKey('organizacoes.id'), index=True)
    perfil: Mapped[str] = mapped_column(String(30))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class FornecedorIdentidade(Base):
    __tablename__ = 'fornecedor_identidades'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True)


class FornecedorVinculo(Base):
    __tablename__ = 'fornecedor_vinculos'
    __table_args__ = (UniqueConstraint('identidade_id', 'organizacao_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identidade_id: Mapped[int] = mapped_column(ForeignKey('fornecedor_identidades.id'), index=True)
    organizacao_id: Mapped[int] = mapped_column(ForeignKey('organizacoes.id'), index=True)
    pessoa_id: Mapped[int | None] = mapped_column(ForeignKey('pessoas.id'), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class ConviteFornecedor(Base):
    __tablename__ = 'convites_fornecedor'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str] = mapped_column(String(160))
    nome: Mapped[str] = mapped_column(String(160))
    organizacao_id: Mapped[int] = mapped_column(ForeignKey('organizacoes.id'), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
