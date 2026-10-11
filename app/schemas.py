"""Schemas Pydantic — validação de entrada (RN-002: valores > 0)."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LoginIn(BaseModel):
    email: str
    senha: str

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return v.strip().lower()


class SenhaIn(BaseModel):
    senha_atual: str
    nova: str = Field(min_length=8, max_length=128)


class LojaIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nome: str | None = Field(default=None, min_length=2, max_length=160)
    documento: str | None = Field(default=None, max_length=30)
    telefone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=160)
    endereco: str | None = Field(default=None, max_length=220)

    @model_validator(mode="after")
    def _validar(self):
        values = self.model_dump(exclude_unset=True)
        if not values or any(v is None for v in values.values()):
            raise ValueError("informe campos não nulos para alterar")
        if self.email and ("@" not in self.email or any(c.isspace() for c in self.email)):
            raise ValueError("email inválido")
        return self


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    perfil: str
    ativo: bool


Perfil = Literal["admin", "financeiro", "operador", "consulta"]


class UserCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=160, pattern=r"^[^@\s]+@[^@\s]+$")
    senha: str = Field(min_length=8, max_length=128)
    perfil: Perfil = "operador"
    ativo: bool = True

    @field_validator("nome", mode="before")
    @classmethod
    def _nome(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class PerfilUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=160, pattern=r"^[^@\s]+@[^@\s]+$")
    senha_atual: str | None = Field(default=None, max_length=128)

    @field_validator("nome", "email", mode="before")
    @classmethod
    def _normalizar(cls, value, info):
        if isinstance(value, str):
            value = value.strip()
            return value.lower() if info.field_name == "email" else value
        return value

    @model_validator(mode="after")
    def _validar(self):
        fields = self.model_dump(exclude_unset=True)
        if not ({"nome", "email"} & fields.keys()) or any(v is None for k, v in fields.items() if k != "senha_atual"):
            raise ValueError("informe nome ou email não nulos")
        return self


class UserUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=160, pattern=r"^[^@\s]+@[^@\s]+$")
    perfil: Perfil | None = None
    ativo: bool | None = None
    motivo: str | None = Field(default=None, max_length=500)

    @field_validator("nome", "email", "motivo", mode="before")
    @classmethod
    def _normalizar(cls, value, info):
        if isinstance(value, str):
            value = value.strip()
            return value.lower() if info.field_name == "email" else value
        return value

    @model_validator(mode="after")
    def _tem_alteracao(self):
        fields = self.model_dump(exclude_unset=True)
        if not ({"nome", "email", "perfil", "ativo"} & fields.keys()) or any(v is None for k, v in fields.items() if k != "motivo"):
            raise ValueError("informe nome, email, perfil ou ativo não nulos")
        return self


class UserPasswordResetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    senha: str = Field(min_length=8, max_length=128)


class PessoaIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    tipo: str = Field(pattern="^(representante|cliente|fornecedor|ambos)$")
    nome: str = Field(min_length=2, max_length=160)
    documento: str = Field(default="", max_length=30)
    telefone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=160)
    observacoes: str = ""
    ativo: bool = True
    apelido: str = Field(default="", max_length=60)
    endereco: str = Field(default="", max_length=220)
    chave_pix: str = Field(default="", max_length=120)
    banco: str = Field(default="", max_length=60)
    conta: str = Field(default="", max_length=60)
    titular_chave: str = Field(default="", max_length=160)
    prazo_dias: int = Field(default=0, ge=0)
    tolerancia_credito: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    prioridade: int = Field(default=2, ge=1, le=3)


class PessoaPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    tipo: Literal["representante", "cliente", "fornecedor", "ambos"] | None = None
    nome: str | None = Field(default=None, min_length=2, max_length=160)
    documento: str | None = Field(default=None, max_length=30)
    telefone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=160)
    observacoes: str | None = None
    ativo: bool | None = None
    apelido: str | None = Field(default=None, max_length=60)
    endereco: str | None = Field(default=None, max_length=220)
    chave_pix: str | None = Field(default=None, max_length=120)
    banco: str | None = Field(default=None, max_length=60)
    conta: str | None = Field(default=None, max_length=60)
    titular_chave: str | None = Field(default=None, max_length=160)
    prazo_dias: int | None = Field(default=None, ge=0)
    tolerancia_credito: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    prioridade: int | None = Field(default=None, ge=1, le=3)

    @model_validator(mode="after")
    def reject_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Campos do cadastro não aceitam null")
        return self


class ContatoIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nome: str = Field(min_length=2, max_length=160)
    telefone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=160)
    cargo: str = Field(default="", max_length=120)
    principal: bool = False
    ativo: bool = True


class ChavePixIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    chave: str = Field(min_length=1, max_length=120)
    tipo: Literal["cpf", "cnpj", "email", "telefone", "aleatoria"] = "aleatoria"
    titular: str = Field(default="", max_length=160)
    banco: str = Field(default="", max_length=60)
    agencia: str = Field(default="", max_length=30)
    conta: str = Field(default="", max_length=60)
    tipo_conta: str = Field(default="", max_length=30)
    categoria: Literal["fixa", "temporaria"] = "fixa"
    validade: date | None = None
    principal: bool = False
    ativo: bool = True

    @model_validator(mode="after")
    def temporary_expiry(self):
        if self.categoria == "temporaria" and self.validade is None:
            raise ValueError("Chave temporária exige validade")
        if self.principal and not self.ativo:
            raise ValueError("Chave principal precisa estar ativa")
        return self


class MovIn(BaseModel):
    data_pix: date
    valor: float = Field(gt=0)
    remetente: str = ""
    representante_id: int | None = None
    destinatario: str = ""
    fornecedor_id: int | None = None
    observacao: str = ""
    autor: str = ""
    forma_pagamento: str = "PIX"
    natureza: str = "DESPESA"
    link_token: str = ""


class ProjecaoIn(BaseModel):
    representante_id: int
    fornecedor_id: int
    valor_projetado: float = Field(gt=0)
    data_prevista: date | None = None
    observacao: str = ""


class LancIn(BaseModel):
    tipo: str
    natureza: str = ""
    valor: float = Field(gt=0)
    data: date
    representante_id: int | None = None
    fornecedor_id: int | None = None
    descricao: str = ""
    origem: str = "manual"
    prioridade: int | None = Field(default=None, ge=1, le=3)

    @field_validator("tipo")
    @classmethod
    def _tipo(cls, v):
        ok = {"debito", "credito", "pagamento", "estorno", "desconto",
              "despesa", "imposto", "salario", "perda"}
        if v not in ok:
            raise ValueError(f"tipo deve ser um de {sorted(ok)}")
        return v


class ConcilIn(BaseModel):
    movimentacao_id: int
    alvo_tipo: str = Field(pattern="^(lancamento|projecao)$")
    alvo_id: int
    valor: float = Field(gt=0)
