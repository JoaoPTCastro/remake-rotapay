"""Ordenação SQL por campos permitidos, aplicada antes da paginação."""
from fastapi import HTTPException


def ordenar(query, campo, direcao, permitidos, identificador, padrao):
    if direcao not in ("asc", "desc"):
        raise HTTPException(422, "Direção de ordenação inválida")
    if campo is None:
        return query.order_by(padrao, identificador.asc())
    if campo not in permitidos:
        raise HTTPException(422, "Campo de ordenação inválido")
    expr = permitidos[campo]
    return query.order_by(expr.asc() if direcao == "asc" else expr.desc(), identificador.asc())
