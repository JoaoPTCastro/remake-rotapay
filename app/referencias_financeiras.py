"""Serializa cadastros novos que usam a mesma referência documental.

O lock permanece no banco até commit/rollback. Não altera nem bloqueia o
motor legado; referências diferentes não provam eventos reais diferentes.
"""
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import OperationalError, IntegrityError
from .models import ReferenciaRegistro


def chave_referencia(valor: str) -> str:
    return valor.strip().casefold()


def bloquear_referencia(db, referencia: str):
    chave = chave_referencia(referencia)
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    elif dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        raise HTTPException(503, "Banco não suportado para registro financeiro concorrente")
    try:
        db.execute(insert(ReferenciaRegistro).values(chave=chave, version=0)
            .on_conflict_do_nothing(index_elements=["chave"]))
        db.execute(update(ReferenciaRegistro).where(ReferenciaRegistro.chave == chave)
            .values(version=ReferenciaRegistro.version + 1))
    except (OperationalError, IntegrityError):
        db.rollback()
        raise HTTPException(409, "Referência em atualização. Recarregue e tente novamente")
    return chave
