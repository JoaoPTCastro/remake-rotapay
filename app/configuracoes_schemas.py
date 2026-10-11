"""Configurações descritivas, sem criar novas regras financeiras."""
from typing import Literal
from pydantic import Field
from .notas_schemas import Estrito

COLUNAS = {
    "cadastros": ["nome", "tipo", "documento", "telefone", "email", "prazo_dias", "ativo"],
    "notas": ["numero_documento", "pessoa_nome", "relacao", "valor_original", "valor_abatido", "saldo_aberto", "data_emissao", "vencimento", "status"],
    "pagamentos": ["codigo", "tipo", "forma", "cliente_nome", "fornecedor_nome", "valor", "data", "cancelado"],
}
ORDENAVEIS = {**COLUNAS, "cadastros": ["nome", "tipo", "documento", "prazo_dias", "ativo"]}
FILTROS = {"cadastros": {"tipo", "ativo", "q"}, "notas": {"pessoa_id", "relacao", "status", "em_atraso"},
    "pagamentos": {"cliente_id", "fornecedor_id", "tipo", "forma", "valor_min", "valor_max", "origem_registro"}}


class CatalogoIn(Estrito):
    nome: str = Field(min_length=2, max_length=80)
    forma_base: Literal["PIX", "dinheiro"] | None = None
    aplicavel_em: Literal["notas", "pagamentos", "ambos"] | None = None
    prazo_dias: int | None = Field(None, ge=0, le=36500)


class CatalogoPatch(Estrito):
    nome: str | None = Field(None, min_length=2, max_length=80)
    ativo: bool | None = None


class ColunaIn(Estrito):
    campo: str
    visivel: bool = Field(strict=True)


class OrdenacaoIn(Estrito):
    campo: str
    direcao: Literal["asc", "desc"]


class PreferenciaIn(Estrito):
    colunas: list[ColunaIn] = Field(min_length=1, max_length=30)
    ordenacao: OrdenacaoIn | None = None
    filtros: dict = Field(default_factory=dict)
