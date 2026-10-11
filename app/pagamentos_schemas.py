"""Eventos novos e aplicações manuais por relação, sem importação legado."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from typing import Literal
from pydantic import Field, model_validator, field_validator, AwareDatetime
from .notas_schemas import Estrito


class PagamentoIn(Estrito):
    data_hora_transacao: AwareDatetime | None = None
    remetente: str | None = Field(default=None, max_length=160)
    favorecido: str | None = Field(default=None, max_length=160)
    intermediador: str | None = Field(default=None, max_length=160)

    @field_validator("remetente", "favorecido", "intermediador", mode="before")
    @classmethod
    def texto_opcional(cls, value):
        return (value.strip() or None) if isinstance(value, str) else value

    @field_validator("data_hora_transacao", mode="before")
    @classmethod
    def horario_expresso(cls, value):
        if value is not None and not isinstance(value, (str, datetime)):
            raise ValueError("Informe data e hora ISO com timezone explícito")
        return value

    forma_id: int | None = Field(default=None, gt=0)
    operacao_id: int | None = Field(default=None, gt=0)
    tipo: Literal["cliente_loja", "cliente_fornecedor", "repasse_fornecedor"]
    forma: Literal["PIX", "dinheiro"]
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    data: date
    cliente_id: int | None = Field(default=None, gt=0)
    fornecedor_id: int | None = Field(default=None, gt=0)
    pagamento_origem_id: int | None = Field(default=None, gt=0)
    referencia_externa: str = Field(min_length=3, max_length=220)
    observacao: str = Field(min_length=3, max_length=4000)
    chave_idempotencia: str = Field(min_length=1, max_length=80)
    declaracao_novo_pagamento: Literal[True]

    @model_validator(mode="after")
    def titulares(self):
        if self.data_hora_transacao is not None:
            if self.data_hora_transacao.astimezone(ZoneInfo("America/Sao_Paulo")).date() != self.data:
                raise ValueError("Data da transação em São Paulo deve coincidir com a data do pagamento")
            if self.data_hora_transacao.astimezone(timezone.utc) > datetime.now(timezone.utc):
                raise ValueError("Transação não pode ter data e hora futura")
        if self.tipo == "cliente_loja" and (not self.cliente_id or self.fornecedor_id or self.pagamento_origem_id):
            raise ValueError("Recebimento na loja exige apenas cliente")
        if self.tipo == "cliente_fornecedor" and (not self.cliente_id or not self.fornecedor_id or self.pagamento_origem_id or self.forma != "PIX"):
            raise ValueError("Pagamento direto exige PIX, cliente e fornecedor")
        if self.tipo == "repasse_fornecedor" and (self.cliente_id or not self.fornecedor_id or not self.pagamento_origem_id):
            raise ValueError("Repasse exige fornecedor e recebimento de origem, sem cliente adicional")
        return self


class AplicacaoIn(Estrito):
    nota_id: int = Field(gt=0)
    relacao: Literal["cliente", "fornecedor"]
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    data: date
    referencia: str = Field(min_length=3, max_length=220)
    observacao: str = Field(min_length=3, max_length=4000)
    fornecedor_confirmou: bool = False
    referencia_confirmacao: str | None = Field(default=None, min_length=3, max_length=220)
    chave_idempotencia: str = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def confirmacao_fornecedor(self):
        if self.relacao == "fornecedor" and (not self.fornecedor_confirmou or not self.referencia_confirmacao):
            raise ValueError("Fornecedor deve ter conferido e concordado: informe a referência da confirmação externa")
        if self.relacao == "cliente" and (self.fornecedor_confirmou or self.referencia_confirmacao is not None):
            raise ValueError("Confirmação do fornecedor pertence somente à relação fornecedor")
        return self
