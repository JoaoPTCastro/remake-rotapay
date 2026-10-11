"""Crédito reconhecido explicitamente da sobra; não representa dinheiro novo."""
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import Field
from .notas_schemas import Estrito


class ReconhecimentoIn(Estrito):
    acerto_id: int = Field(gt=0)
    pagamento_id: int = Field(gt=0)
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    data: date
    referencia: str = Field(min_length=3, max_length=220)
    observacao: str = Field(min_length=3, max_length=4000)
    chave_idempotencia: str = Field(min_length=1, max_length=80)
    confirmacao: Literal[True]
    fornecedor_confirmou: bool = False
    referencia_confirmacao: str | None = Field(default=None, min_length=3, max_length=220)


class CreditoAplicacaoIn(Estrito):
    nota_id: int = Field(gt=0)
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    data: date
    referencia: str = Field(min_length=3, max_length=220)
    observacao: str = Field(min_length=3, max_length=4000)
    chave_idempotencia: str = Field(min_length=1, max_length=80)
    fornecedor_confirmou: bool = False
    referencia_confirmacao: str | None = Field(default=None, min_length=3, max_length=220)
