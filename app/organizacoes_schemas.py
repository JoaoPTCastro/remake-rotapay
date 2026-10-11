"""Entradas limitadas para administração da base de organizações."""
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrganizacaoIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nome: str = Field(min_length=1, max_length=160)

    @field_validator('nome')
    @classmethod
    def nome_limpo(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Informe o nome')
        return value


class ConviteIn(OrganizacaoIn):
    email: str = Field(min_length=3, max_length=160)

    @field_validator('email')
    @classmethod
    def email_valido(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", value):
            raise ValueError('Informe um email válido')
        return value


class AceitarConviteIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: str = Field(min_length=32, max_length=128)


class RegistrarFornecedorIn(AceitarConviteIn):
    nome: str = Field(min_length=1, max_length=120)
    senha: str = Field(min_length=8, max_length=128)

    @field_validator('nome')
    @classmethod
    def nome_limpo(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Informe o nome')
        return value
