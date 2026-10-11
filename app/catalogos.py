"""Vínculos opcionais: somente rótulos e prazo explícito, sem novos efeitos."""
from fastapi import HTTPException
from .models import CatalogoConfig
from .referencias_financeiras import bloquear_referencia


def resolver_catalogos(db, documento, operacao_id=None, forma_id=None, condicao_id=None, forma=None):
    result = {}
    if not any((operacao_id, forma_id, condicao_id)):
        return result
    bloquear_referencia(db, "mutex:catalogos")
    for kind, identifier, field in (("operacoes", operacao_id, "operacao"), ("formas", forma_id, "forma"), ("condicoes", condicao_id, "condicao")):
        if not identifier:
            continue
        item = db.get(CatalogoConfig, identifier)
        if item:
            db.refresh(item)
        if not item or item.tipo != kind or not item.ativo or item.aplicavel_em not in (documento, "ambos"):
            raise HTTPException(422, "Item de catálogo deve estar ativo e ser aplicável ao documento")
        if kind == "formas" and item.forma_base != forma:
            raise HTTPException(422, "Forma do catálogo deve coincidir com PIX/dinheiro informado")
        result[field + "_id"] = item.id
        result[field + "_nome_snapshot"] = item.nome
        if kind == "condicoes":
            result["prazo_dias_snapshot"] = item.prazo_dias
    return result
