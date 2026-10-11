from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class CadastroFornecedorIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pessoa_id: int = Field(gt=0, strict=True)


class MembroOrganizacaoIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    perfil: Literal['admin', 'financeiro', 'operador', 'consulta', 'fornecedor']
    ativo: bool = Field(strict=True)


class AdicionarMembroIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    email: str = Field(max_length=160, pattern=r'^[^@\s]+@[^@\s]+$')
    perfil: Literal['admin', 'financeiro', 'operador', 'consulta']


class RecebimentoFornecedorIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    referencia: str = Field(min_length=3, max_length=220)
    observacao: str = Field(default='', max_length=1000)
