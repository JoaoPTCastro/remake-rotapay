"""Referência explícita entre identidade central e cadastro financeiro local."""
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, Money, _now


class CadastroFornecedorOrganizacao(Base):
    __tablename__ = 'cadastros_fornecedor_organizacao'
    __table_args__ = (UniqueConstraint('organizacao_id', 'identidade_id'),
                     UniqueConstraint('organizacao_id', 'pessoa_local_id'))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizacao_id: Mapped[int] = mapped_column(ForeignKey('organizacoes.id'))
    identidade_id: Mapped[int] = mapped_column(ForeignKey('fornecedor_identidades.id'))
    # ID no banco da organização, deliberadamente sem FK para a Pessoa central.
    pessoa_local_id: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class RecebimentoFornecedor(Base):
    __tablename__ = 'recebimentos_fornecedor'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pagamento_id: Mapped[int] = mapped_column(ForeignKey('pagamentos.id'), unique=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey('pessoas.id'))
    usuario_central_id: Mapped[int] = mapped_column(Integer)
    pagamento_version: Mapped[int] = mapped_column(Integer)
    valor_declarado: Mapped[float] = mapped_column(Money)
    referencia: Mapped[str] = mapped_column(String(220))
    observacao: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
