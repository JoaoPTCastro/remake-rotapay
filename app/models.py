"""Modelos SQLAlchemy — espelham §18 do PRD + ajustes de integridade."""
from __future__ import annotations
from datetime import datetime, date, timezone
from sqlalchemy import (String, Integer, Numeric, Date, DateTime, Boolean, Text,
                        ForeignKey, Index, UniqueConstraint, CheckConstraint, text, select)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, column_property

Money = Numeric(12, 2, asdecimal=False)  # precisão fixa no banco, interface float


class Base(DeclarativeBase):
    pass


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[str] = mapped_column(String(30), default="operador")  # admin|financeiro|operador|consulta
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Pessoa(Base):
    """tipo: representante | fornecedor (§18 Pessoa)"""
    __tablename__ = "pessoas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20), index=True)
    nome: Mapped[str] = mapped_column(String(160), index=True)
    documento: Mapped[str] = mapped_column(String(30), default="", index=True)
    telefone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    observacoes: Mapped[str] = mapped_column(Text, default="")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Extensão cadeia (diagrama Whimsical): cliente→vendedor→loja→fornecedor→fabricante
    apelido: Mapped[str] = mapped_column(String(60), default="")
    endereco: Mapped[str] = mapped_column(String(220), default="")
    chave_pix: Mapped[str] = mapped_column(String(120), default="", index=True)
    banco: Mapped[str] = mapped_column(String(60), default="")
    conta: Mapped[str] = mapped_column(String(60), default="")
    titular_chave: Mapped[str] = mapped_column(String(160), default="")
    prazo_dias: Mapped[int] = mapped_column(Integer, default=0)
    # Prioridade de pagamento: 1=alta, 2=normal, 3=baixa (base do rodízio).
    prioridade: Mapped[int] = mapped_column(Integer, default=2)
    # Sprint 4 (atas): tolerância máxima de crédito gerável com o fornecedor.
    # 0 = comportamento atual (nenhum crédito automático).
    tolerancia_credito: Mapped[float] = mapped_column(Money, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class PessoaContato(Base):
    __tablename__ = "pessoa_contatos"
    __table_args__ = (Index("uq_contato_principal", "pessoa_id", unique=True,
                           sqlite_where=text("principal = 1"), postgresql_where=text("principal = true")),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), index=True)
    nome: Mapped[str] = mapped_column(String(160), default="")
    telefone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    cargo: Mapped[str] = mapped_column(String(120), default="")
    principal: Mapped[bool] = mapped_column(Boolean, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class PessoaChavePix(Base):
    __tablename__ = "pessoa_chaves_pix"
    __table_args__ = (Index("uq_chave_principal", "pessoa_id", unique=True,
                           sqlite_where=text("principal = 1"), postgresql_where=text("principal = true")),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), index=True)
    chave: Mapped[str] = mapped_column(String(120), index=True)
    tipo: Mapped[str] = mapped_column(String(20), default="aleatoria")
    titular: Mapped[str] = mapped_column(String(160), default="")
    banco: Mapped[str] = mapped_column(String(60), default="")
    agencia: Mapped[str] = mapped_column(String(30), default="")
    conta: Mapped[str] = mapped_column(String(60), default="")
    tipo_conta: Mapped[str] = mapped_column(String(30), default="")
    categoria: Mapped[str] = mapped_column(String(20), default="fixa")
    validade: Mapped[date | None] = mapped_column(Date, nullable=True)
    principal: Mapped[bool] = mapped_column(Boolean, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Movimentacao(Base):
    """PIX atravessado. saldo_disponivel = quanto ainda pode ser conciliado."""
    __tablename__ = "movimentacoes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # PIX-000123 RN-001
    link_token: Mapped[str] = mapped_column(String(32), default="", index=True)
    data_pix: Mapped[date] = mapped_column(Date, index=True)
    valor: Mapped[float] = mapped_column(Money)
    saldo_disponivel: Mapped[float] = mapped_column(Money)
    remetente: Mapped[str] = mapped_column(String(160), default="")
    representante_id: Mapped[int | None] = mapped_column(ForeignKey("pessoas.id"), nullable=True, index=True)
    destinatario: Mapped[str] = mapped_column(String(160), default="")
    fornecedor_id: Mapped[int | None] = mapped_column(ForeignKey("pessoas.id"), nullable=True, index=True)
    # Colunas da planilha (aba CONTROLE SAÍDAS)
    autor: Mapped[str] = mapped_column(String(120), default="")
    forma_pagamento: Mapped[str] = mapped_column(String(20), default="PIX")
    natureza: Mapped[str] = mapped_column(String(30), default="DESPESA")
    comprovante_path: Mapped[str] = mapped_column(String(400), default="")
    status: Mapped[str] = mapped_column(String(20), default="disponivel", index=True)
    # pendente|disponivel|parcial|conciliada|cancelada
    observacao: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Projecao(Base):
    """Projeção de Pagamento — 1 aberta/parcial por (representante, fornecedor). RN-006"""
    __tablename__ = "projecoes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    representante_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), index=True)
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), index=True)
    valor_projetado: Mapped[float] = mapped_column(Money)
    valor_conciliado: Mapped[float] = mapped_column(Money, default=0.0)
    data_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="aberta", index=True)
    # aberta|parcial|conciliada|cancelada
    observacao: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    @property
    def saldo(self) -> float:
        return round(self.valor_projetado - self.valor_conciliado, 2)


class Lancamento(Base):
    """Débitos/créditos/pagamentos/estornos/descontos/... (§11 RF-060)"""
    __tablename__ = "lancamentos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20), index=True)
    natureza: Mapped[str] = mapped_column(String(40), default="")
    valor: Mapped[float] = mapped_column(Money)
    saldo_aberto: Mapped[float] = mapped_column(Money)  # quanto falta conciliar
    data: Mapped[date] = mapped_column(Date, index=True)
    representante_id: Mapped[int | None] = mapped_column(ForeignKey("pessoas.id"), nullable=True, index=True)
    fornecedor_id: Mapped[int | None] = mapped_column(ForeignKey("pessoas.id"), nullable=True, index=True)
    descricao: Mapped[str] = mapped_column(Text, default="")
    origem: Mapped[str] = mapped_column(String(60), default="manual")
    status: Mapped[str] = mapped_column(String(20), default="aberto", index=True)
    # aberto|parcial|quitado|cancelado
    # Override de prioridade por compra (null = herda do fornecedor).
    prioridade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Conciliacao(Base):
    __tablename__ = "conciliacoes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movimentacao_id: Mapped[int] = mapped_column(ForeignKey("movimentacoes.id"), index=True)
    alvo_tipo: Mapped[str] = mapped_column(String(20))  # lancamento | projecao
    alvo_id: Mapped[int] = mapped_column(Integer, index=True)
    valor: Mapped[float] = mapped_column(Money)
    data: Mapped[date] = mapped_column(Date, default=date.today)
    usuario_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estornada: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Estorno(Base):
    """RN-008: operação desfeita tem registro próprio, original preservado."""
    __tablename__ = "estornos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conciliacao_id: Mapped[int] = mapped_column(ForeignKey("conciliacoes.id"), unique=True)
    motivo: Mapped[str] = mapped_column(Text, default="")
    usuario_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    acao: Mapped[str] = mapped_column(String(60), index=True)
    entidade: Mapped[str] = mapped_column(String(60), index=True)
    entidade_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    antes: Mapped[str] = mapped_column(Text, default="")
    depois: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(45), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


class LinkPagamento(Base):
    """Link individual gerado pelo admin p/ o vendedor (diagrama: Loja → link → Cliente).

    O vendedor abre o link, informa o valor e recebe a chave PIX do
    fornecedor administrada pela loja. Revogável sem apagar histórico.
    """
    __tablename__ = "links_pagamento"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    representante_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), index=True)
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), index=True)
    valor_fixo: Mapped[float | None] = mapped_column(Money, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    chave_pix_id: Mapped[int | None] = mapped_column(ForeignKey("pessoa_chaves_pix.id"), nullable=True)
    chave_snapshot: Mapped[str] = mapped_column(String(120), default="")
    titular_snapshot: Mapped[str] = mapped_column(String(160), default="")
    banco_snapshot: Mapped[str] = mapped_column(String(60), default="")
    agencia_snapshot: Mapped[str] = mapped_column(String(30), default="")
    conta_snapshot: Mapped[str] = mapped_column(String(60), default="")
    tipo_conta_snapshot: Mapped[str] = mapped_column(String(30), default="")
    destino_fixado: Mapped[bool] = mapped_column(Boolean, default=False)
    # Sprint gateway (Checkto): cobrança PIX vinculada ao link
    checkto_transaction_id: Mapped[str] = mapped_column(String(80), default="")
    checkto_webhook_token: Mapped[str] = mapped_column(String(80), default="")
    pix_code: Mapped[str] = mapped_column(Text, default="")
    pix_image: Mapped[str] = mapped_column(String(400), default="")
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Comprovante(Base):
    """Sprint B: comprovante com identidade — quem enviou, quando, em que etapa.

    Etapas: recebido (entrou pelo upload/WhatsApp) → registrado (vinculado
    e conferido na movimentação). Origens: upload | whatsapp.
    """
    __tablename__ = "comprovantes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movimentacao_id: Mapped[int | None] = mapped_column(ForeignKey("movimentacoes.id"),
                                                       nullable=True, index=True)
    arquivo_path: Mapped[str] = mapped_column(String(400))
    arquivo_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    origem: Mapped[str] = mapped_column(String(20), default="upload", index=True)
    enviado_por: Mapped[str] = mapped_column(String(160), default="")
    data_comprovante: Mapped[date | None] = mapped_column(Date, nullable=True)
    etapa: Mapped[str] = mapped_column(String(20), default="recebido", index=True)
    # Sprint C: extração OCR (JSON) + sugestão de fornecedor
    extraido_json: Mapped[str] = mapped_column(Text, default="")
    sugestao_fornecedor_id: Mapped[int | None] = mapped_column(ForeignKey("pessoas.id"), nullable=True)
    sugestao_motivo: Mapped[str] = mapped_column(String(220), default="")
    sugestao_status: Mapped[str] = mapped_column(String(20), default="nenhuma", index=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Job(Base):
    """Sprint B: fila async stub. Worker futuro (OCR) consome pendentes."""
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30), index=True)  # comprovante
    ref_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pendente", index=True)
    detalhe: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Loja(Base):
    """Perfil da loja: linha única com os dados da conta (nome, contato)."""
    __tablename__ = "loja"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(160), default="Minha Loja")
    documento: Mapped[str] = mapped_column(String(30), default="")
    telefone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    endereco: Mapped[str] = mapped_column(String(220), default="")
    logo_arquivo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class NotaObrigacao(Base):
    """Obrigação documental por relação; não participa do motor PIX legado."""
    __tablename__ = "notas_obrigacoes"
    __table_args__ = (UniqueConstraint("pessoa_id", "relacao", "numero_documento", name="uq_nota_documento"),)
    condicao_id: Mapped[int | None] = mapped_column(ForeignKey("catalogos_config.id"), nullable=True)
    condicao_nome_snapshot: Mapped[str | None] = mapped_column(String(80), nullable=True)
    operacao_id: Mapped[int | None] = mapped_column(ForeignKey("catalogos_config.id"), nullable=True)
    operacao_nome_snapshot: Mapped[str | None] = mapped_column(String(80), nullable=True)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), index=True)
    relacao: Mapped[str] = mapped_column(String(20), index=True)
    numero_documento: Mapped[str] = mapped_column(String(120))
    valor_original: Mapped[float] = mapped_column(Money)
    data_emissao: Mapped[date] = mapped_column(Date, index=True)
    vencimento: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    prazo_dias_snapshot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    modo_vencimento: Mapped[str] = mapped_column(String(30))
    descricao: Mapped[str] = mapped_column(Text, default="")
    cancelada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_cancelamento: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class NotaAbatimento(Base):
    __tablename__ = "nota_abatimentos"
    __table_args__ = (Index("uq_nota_abatimento_request", "nota_id", "chave_idempotencia", unique=True),
                       Index("uq_nota_pagamento_app", "pagamento_aplicacao_id", unique=True),
                       Index("uq_nota_credito_app", "credito_aplicacao_id", unique=True),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nota_id: Mapped[int] = mapped_column(ForeignKey("notas_obrigacoes.id"), index=True)
    pagamento_aplicacao_id: Mapped[int | None] = mapped_column(ForeignKey("pagamento_aplicacoes.id"), nullable=True)
    credito_aplicacao_id: Mapped[int | None] = mapped_column(ForeignKey("credito_aplicacoes.id"), nullable=True)
    valor: Mapped[float] = mapped_column(Money)
    data: Mapped[date] = mapped_column(Date)
    referencia: Mapped[str] = mapped_column(String(220))
    referencia_chave: Mapped[str] = mapped_column(String(660), default="", index=True)
    observacao: Mapped[str] = mapped_column(Text)
    origem: Mapped[str] = mapped_column(String(30), default="registro_documental")
    chave_idempotencia: Mapped[str] = mapped_column(String(80))
    estornado: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class NotaAbatimentoEstorno(Base):
    __tablename__ = "nota_abatimento_estornos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    abatimento_id: Mapped[int] = mapped_column(ForeignKey("nota_abatimentos.id"), unique=True)
    motivo: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class NotaAnexo(Base):
    __tablename__ = "nota_anexos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nota_id: Mapped[int] = mapped_column(ForeignKey("notas_obrigacoes.id"), index=True)
    nome_original: Mapped[str] = mapped_column(String(180))
    arquivo_path: Mapped[str] = mapped_column(String(400))
    tamanho: Mapped[int] = mapped_column(Integer)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Pagamento(Base):
    """Evento real novo, independente das movimentações do motor legado."""
    __tablename__ = "pagamentos"
    forma_id: Mapped[int | None] = mapped_column(ForeignKey("catalogos_config.id"), nullable=True)
    forma_nome_snapshot: Mapped[str | None] = mapped_column(String(80), nullable=True)
    operacao_id: Mapped[int | None] = mapped_column(ForeignKey("catalogos_config.id"), nullable=True)
    operacao_nome_snapshot: Mapped[str | None] = mapped_column(String(80), nullable=True)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origem_registro: Mapped[str | None] = mapped_column(String(30), nullable=True)
    data_hora_transacao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remetente: Mapped[str | None] = mapped_column(String(160), nullable=True)
    favorecido: Mapped[str | None] = mapped_column(String(160), nullable=True)
    intermediador: Mapped[str | None] = mapped_column(String(160), nullable=True)
    codigo: Mapped[str] = mapped_column(String(24), unique=True)
    tipo: Mapped[str] = mapped_column(String(30), index=True)
    forma: Mapped[str] = mapped_column(String(20), index=True)
    valor: Mapped[float] = mapped_column(Money)
    data: Mapped[date] = mapped_column(Date, index=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("pessoas.id"), nullable=True, index=True)
    fornecedor_id: Mapped[int | None] = mapped_column(ForeignKey("pessoas.id"), nullable=True, index=True)
    pagamento_origem_id: Mapped[int | None] = mapped_column(ForeignKey("pagamentos.id"), nullable=True, index=True)
    referencia_externa: Mapped[str] = mapped_column(String(220))
    referencia_chave: Mapped[str] = mapped_column(String(660), unique=True)
    observacao: Mapped[str] = mapped_column(Text)
    chave_idempotencia: Mapped[str] = mapped_column(String(80), unique=True)
    cancelado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_cancelamento: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    autor_nome = column_property(select(User.nome).where(User.id == created_by).scalar_subquery())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class PagamentoAplicacao(Base):
    __tablename__ = "pagamento_aplicacoes"
    __table_args__ = (UniqueConstraint("pagamento_id", "chave_idempotencia", name="uq_pagamento_app_request"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pagamento_id: Mapped[int] = mapped_column(ForeignKey("pagamentos.id"), index=True)
    acerto_id: Mapped[int | None] = mapped_column(ForeignKey("acertos.id"), nullable=True, index=True)
    nota_id: Mapped[int] = mapped_column(ForeignKey("notas_obrigacoes.id"), index=True)
    relacao: Mapped[str] = mapped_column(String(20), index=True)
    valor: Mapped[float] = mapped_column(Money)
    data: Mapped[date] = mapped_column(Date)
    referencia: Mapped[str] = mapped_column(String(220))
    observacao: Mapped[str] = mapped_column(Text)
    fornecedor_confirmou: Mapped[bool] = mapped_column(Boolean, default=False)
    referencia_confirmacao: Mapped[str] = mapped_column(String(220), default="")
    chave_idempotencia: Mapped[str] = mapped_column(String(80))
    estornada: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class PagamentoAplicacaoEstorno(Base):
    __tablename__ = "pagamento_aplicacao_estornos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aplicacao_id: Mapped[int] = mapped_column(ForeignKey("pagamento_aplicacoes.id"), unique=True)
    motivo: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class PagamentoAnexo(Base):
    __tablename__ = "pagamento_anexos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pagamento_id: Mapped[int] = mapped_column(ForeignKey("pagamentos.id"), index=True)
    nome_original: Mapped[str] = mapped_column(String(180))
    arquivo_path: Mapped[str] = mapped_column(String(400))
    tamanho: Mapped[int] = mapped_column(Integer)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ReferenciaRegistro(Base):
    """Mutex por referência, sem valor financeiro ou titular inferido."""
    __tablename__ = "referencia_registros"
    chave: Mapped[str] = mapped_column(String(660), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=0)


class Acerto(Base):
    __tablename__ = "acertos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(24), unique=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), index=True)
    relacao: Mapped[str] = mapped_column(String(20), index=True)
    data: Mapped[date] = mapped_column(Date)
    referencia: Mapped[str] = mapped_column(String(220))
    observacao: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="rascunho", index=True)
    token_previa: Mapped[str] = mapped_column(String(64))
    chave_idempotencia: Mapped[str] = mapped_column(String(80), unique=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    referencia_envio: Mapped[str] = mapped_column(String(220), default="")
    observacao_envio: Mapped[str] = mapped_column(Text, default="")
    referencia_confirmacao: Mapped[str] = mapped_column(String(220), default="")
    observacao_confirmacao: Mapped[str] = mapped_column(Text, default="")
    motivo_cancelamento: Mapped[str] = mapped_column(Text, default="")
    motivo_estorno: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class AcertoItem(Base):
    __tablename__ = "acerto_itens"
    __table_args__ = (UniqueConstraint("acerto_id", "pagamento_id", "nota_id", name="uq_acerto_par"),
        UniqueConstraint("acerto_id", "credito_id", "nota_id", name="uq_acerto_par_credito"),
        CheckConstraint("(pagamento_id IS NOT NULL AND credito_id IS NULL) OR (pagamento_id IS NULL AND credito_id IS NOT NULL)", name="ck_acerto_fonte"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    acerto_id: Mapped[int] = mapped_column(ForeignKey("acertos.id"), index=True)
    pagamento_id: Mapped[int | None] = mapped_column(ForeignKey("pagamentos.id"), nullable=True, index=True)
    credito_id: Mapped[int | None] = mapped_column(ForeignKey("creditos_conta.id"), nullable=True, index=True)
    nota_id: Mapped[int] = mapped_column(ForeignKey("notas_obrigacoes.id"), index=True)
    valor: Mapped[float] = mapped_column(Money)
    pagamento_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credito_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nota_version: Mapped[int] = mapped_column(Integer)
    saldo_pagamento_snapshot: Mapped[float | None] = mapped_column(Money, nullable=True)
    saldo_credito_snapshot: Mapped[float | None] = mapped_column(Money, nullable=True)
    credito_dados_snapshot: Mapped[str] = mapped_column(Text, default="")
    saldo_nota_snapshot: Mapped[float] = mapped_column(Money)


class AcertoEvento(Base):
    __tablename__ = "acerto_eventos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    acerto_id: Mapped[int] = mapped_column(ForeignKey("acertos.id"), index=True)
    acao: Mapped[str] = mapped_column(String(30))
    referencia: Mapped[str] = mapped_column(String(220), default="")
    observacao: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class CreditoConta(Base):
    __tablename__ = "creditos_conta"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(24), unique=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), index=True)
    relacao: Mapped[str] = mapped_column(String(20), index=True)
    acerto_id: Mapped[int] = mapped_column(ForeignKey("acertos.id"), index=True)
    pagamento_id: Mapped[int] = mapped_column(ForeignKey("pagamentos.id"), index=True)
    valor_original: Mapped[float] = mapped_column(Money)
    data: Mapped[date] = mapped_column(Date)
    referencia: Mapped[str] = mapped_column(String(220))
    referencia_chave: Mapped[str] = mapped_column(String(660), unique=True)
    observacao: Mapped[str] = mapped_column(Text)
    chave_idempotencia: Mapped[str] = mapped_column(String(80), unique=True)
    fornecedor_confirmou: Mapped[bool] = mapped_column(Boolean, default=False)
    referencia_confirmacao: Mapped[str] = mapped_column(String(220), default="")
    revertido: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class CreditoAplicacao(Base):
    __tablename__ = "credito_aplicacoes"
    __table_args__ = (UniqueConstraint("credito_id", "chave_idempotencia", name="uq_credito_app_request"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    credito_id: Mapped[int] = mapped_column(ForeignKey("creditos_conta.id"), index=True)
    acerto_id: Mapped[int | None] = mapped_column(ForeignKey("acertos.id"), nullable=True, index=True)
    nota_id: Mapped[int] = mapped_column(ForeignKey("notas_obrigacoes.id"), index=True)
    valor: Mapped[float] = mapped_column(Money)
    data: Mapped[date] = mapped_column(Date)
    referencia: Mapped[str] = mapped_column(String(220))
    observacao: Mapped[str] = mapped_column(Text)
    chave_idempotencia: Mapped[str] = mapped_column(String(80))
    fornecedor_confirmou: Mapped[bool] = mapped_column(Boolean, default=False)
    referencia_confirmacao: Mapped[str] = mapped_column(String(220), default="")
    estornada: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class CreditoAplicacaoEstorno(Base):
    __tablename__ = "credito_aplicacao_estornos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aplicacao_id: Mapped[int] = mapped_column(ForeignKey("credito_aplicacoes.id"), unique=True)
    motivo: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class CreditoReversao(Base):
    __tablename__ = "credito_reversoes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    credito_id: Mapped[int] = mapped_column(ForeignKey("creditos_conta.id"), unique=True)
    motivo: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ImportacaoCSV(Base):
    """Recibo persistente de lote; não armazena o arquivo de origem."""
    __tablename__ = "importacoes_csv"
    __table_args__ = (UniqueConstraint("tipo", "hash_conteudo"), UniqueConstraint("created_by", "chave_idempotencia"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20))
    hash_conteudo: Mapped[str] = mapped_column(String(64))
    chave_idempotencia: Mapped[str] = mapped_column(String(80))
    resultado_json: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ImportacaoCSVChave(Base):
    __tablename__ = "importacoes_csv_chaves"
    __table_args__ = (UniqueConstraint("created_by", "chave_idempotencia"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importacao_id: Mapped[int] = mapped_column(ForeignKey("importacoes_csv.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    chave_idempotencia: Mapped[str] = mapped_column(String(80))


class CatalogoConfig(Base):
    __tablename__ = "catalogos_config"
    __table_args__ = (UniqueConstraint("tipo", "nome_chave"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20))
    nome: Mapped[str] = mapped_column(String(80))
    nome_chave: Mapped[str] = mapped_column(String(240))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    forma_base: Mapped[str | None] = mapped_column(String(20), nullable=True)
    aplicavel_em: Mapped[str] = mapped_column(String(20))
    prazo_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class PreferenciaTabela(Base):
    __tablename__ = "preferencias_tabelas"
    __table_args__ = (UniqueConstraint("user_id", "tela"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    tela: Mapped[str] = mapped_column(String(20))
    configuracao_json: Mapped[str] = mapped_column(Text)


class CompartilhamentoExtrato(Base):
    """Acesso externo revogável a uma única relação, sem persistir o segredo."""
    __tablename__ = "compartilhamentos_extratos"
    __table_args__ = (CheckConstraint("relacao IN ('cliente', 'fornecedor')", name="ck_compartilhamento_relacao"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), index=True)
    relacao: Mapped[str] = mapped_column(String(20))
    destinatario: Mapped[str] = mapped_column(String(160))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    expira_em: Mapped[datetime] = mapped_column(DateTime)
    revogado: Mapped[bool] = mapped_column(Boolean, default=False)
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revogado_por: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    motivo_revogacao: Mapped[str] = mapped_column(String(500), default="")


class LegadoLote(Base):
    """Recibo imutável de classificação; não reserva nem consome dinheiro."""
    __tablename__ = "legado_lotes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chave_idempotencia: Mapped[str] = mapped_column(String(80), unique=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    hash_previa: Mapped[str] = mapped_column(String(64))
    recibo_json: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class LegadoClassificacao(Base):
    __tablename__ = "legado_classificacoes"
    __table_args__ = (UniqueConstraint("fonte", "fonte_id", name="uq_legado_origem"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("legado_lotes.id"), index=True)
    fonte: Mapped[str] = mapped_column(String(30))
    fonte_id: Mapped[int] = mapped_column(Integer)
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    decisao: Mapped[str] = mapped_column(String(30))
    evidencia: Mapped[str] = mapped_column(String(500))
    pessoa_id: Mapped[int | None] = mapped_column(ForeignKey("pessoas.id"), nullable=True)
    relacao: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
