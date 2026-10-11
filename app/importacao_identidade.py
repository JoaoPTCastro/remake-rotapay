"""Mutex transacional dos cadastros e lotes CSV, sem alterar dados históricos."""
import re
from fastapi import HTTPException
from .models import Pessoa
from .referencias_financeiras import bloquear_referencia


def documento_normalizado(valor):
    return re.sub(r"[^0-9]", "", valor or "")


def bloquear_cadastros(db):
    bloquear_referencia(db, "mutex:cadastros-csv")


def validar_documento_novo(db, documento, pessoa_id=None):
    """Não muda duplicados antigos; impede introduzir uma nova duplicidade."""
    doc = documento_normalizado(documento)
    if len(doc) not in (11, 14):
        return
    for pid, existente in db.query(Pessoa.id, Pessoa.documento).all():
        if pid != pessoa_id and documento_normalizado(existente) == doc:
            raise HTTPException(409, "Documento já utilizado em outro cadastro")
