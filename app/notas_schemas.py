"""Contratos de notas e registros documentais externos."""
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class NotaIn(Estrito):
    condicao_id: int | None = Field(default=None, gt=0)
    operacao_id: int | None = Field(default=None, gt=0)
    pessoa_id: int = Field(gt=0)
    relacao: Literal["cliente", "fornecedor"]
    numero_documento: str = Field(min_length=1, max_length=80)
    valor_original: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    data_emissao: date
    descricao: str = Field(default="", max_length=4000)
    modo_vencimento: Literal["prazo_cadastro", "prazo_informado", "data", "sem_vencimento"] = "prazo_cadastro"
    prazo_dias: int | None = Field(default=None, ge=0, le=36500)
    vencimento: date | None = None

    @model_validator(mode="after")
    def prazo_coerente(self):
        if self.condicao_id and self.modo_vencimento != "prazo_cadastro":
            raise ValueError("Condição de catálogo exige modo prazo_cadastro, sem prazo ou data explícitos")
        if self.modo_vencimento == "prazo_informado" and self.prazo_dias is None:
            raise ValueError("Informe o prazo em dias")
        if self.modo_vencimento != "prazo_informado" and self.prazo_dias is not None:
            raise ValueError("Prazo em dias exige modo prazo_informado")
        if self.modo_vencimento == "data" and self.vencimento is None:
            raise ValueError("Informe o vencimento")
        if self.modo_vencimento != "data" and self.vencimento is not None:
            raise ValueError("Data de vencimento exige modo data")
        if self.vencimento and self.vencimento < self.data_emissao:
            raise ValueError("Vencimento não pode anteceder a emissão")
        return self


class AbatimentoIn(Estrito):
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    data: date
    referencia: str = Field(min_length=3, max_length=220)
    observacao: str = Field(min_length=3, max_length=4000)
    chave_idempotencia: str = Field(min_length=1, max_length=80)


class DesfazerIn(Estrito):
    # A senha é uma credencial exata: espaços também fazem parte dela.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    motivo: str = Field(min_length=3, max_length=4000)
    senha: str = Field(min_length=1, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def limpar_motivo(cls, dados):
        if isinstance(dados, dict) and isinstance(dados.get("motivo"), str):
            return {**dados, "motivo": dados["motivo"].strip()}
        return dados
