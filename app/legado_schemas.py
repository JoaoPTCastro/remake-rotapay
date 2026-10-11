"""Classificação documental do legado; nenhum comando de conversão financeira."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

FonteLegado = Literal["movimentacao", "lancamento", "projecao", "conciliacao", "estorno", "abatimento_documental"]


class ItemClassificacao(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    fonte: FonteLegado
    fonte_id: int = Field(gt=0, strict=True)
    snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    decisao: Literal["pendente", "manter_legado", "avaliar_transicao"]
    evidencia: str = Field(min_length=3, max_length=500)
    pessoa_id: int | None = Field(default=None, gt=0, strict=True)
    relacao: Literal["cliente", "fornecedor"] | None = None

    @model_validator(mode="after")
    def par_relacao(self):
        if (self.pessoa_id is None) != (self.relacao is None):
            raise ValueError("Pessoa e relação devem ser informadas juntas")
        return self


class PreviaLegado(BaseModel):
    model_config = ConfigDict(extra="forbid")
    itens: list[ItemClassificacao] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def fontes_unicas(self):
        if len({(i.fonte, i.fonte_id) for i in self.itens}) != len(self.itens):
            raise ValueError("Uma fonte não pode aparecer duas vezes no mesmo lote")
        return self


class ConfirmacaoLegado(PreviaLegado):
    hash_previa: str = Field(pattern=r"^[a-f0-9]{64}$")
    chave_idempotencia: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9:_-]+$")
