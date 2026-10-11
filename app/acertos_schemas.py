"""Acerto imutável de pares explícitos, ligado à prévia emitida pelo servidor."""
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import Field, model_validator
from .notas_schemas import Estrito


class AcertoItemIn(Estrito):
    pagamento_id: int | None = Field(default=None, gt=0)
    credito_id: int | None = Field(default=None, gt=0)
    nota_id: int = Field(gt=0)
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)

    @model_validator(mode="after")
    def fonte_unica(self):
        if (self.pagamento_id is None) == (self.credito_id is None):
            raise ValueError("Informe exatamente um pagamento ou crédito")
        return self


class AcertoPreviaIn(Estrito):
    pessoa_id: int = Field(gt=0)
    relacao: Literal["cliente", "fornecedor"]
    data: date
    referencia: str = Field(min_length=3, max_length=220)
    observacao: str = Field(min_length=3, max_length=4000)
    itens: list[AcertoItemIn] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def pares_unicos(self):
        if sum((i.valor for i in self.itens), Decimal("0")) > Decimal("9999999999.99"):
            raise ValueError("Total do acerto excede o limite monetário")
        pares = {(i.pagamento_id, i.credito_id, i.nota_id) for i in self.itens}
        if len(pares) != len(self.itens):
            raise ValueError("Um par pagamento/nota só pode aparecer uma vez")
        return self


class AcertoIn(AcertoPreviaIn):
    token_previa: str = Field(min_length=64, max_length=64)
    chave_idempotencia: str = Field(min_length=1, max_length=80)


class EnvioIn(Estrito):
    referencia_envio: str = Field(min_length=3, max_length=220)
    observacao_envio: str = Field(min_length=3, max_length=4000)


class ConfirmacaoIn(Estrito):
    referencia_confirmacao: str = Field(min_length=3, max_length=220)
    observacao_confirmacao: str = Field(min_length=3, max_length=4000)


class EfetivarIn(Estrito):
    confirmacao: Literal[True]
