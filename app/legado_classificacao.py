"""Inventário e prévia por projeção permitida; classificação não habilita consumo.

O grafo congela dependências financeiras relacionadas. Não lê arquivos, tokens,
chaves, hashes de comprovantes, observações ou contatos. Sem efeitos financeiros.
"""
import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from fastapi import HTTPException
from .models import (Movimentacao, Lancamento, Projecao, Conciliacao, Estorno,
    NotaAbatimento, NotaAbatimentoEstorno, NotaObrigacao, Pessoa, LegadoClassificacao,
    PagamentoAplicacao, CreditoAplicacao, Pagamento, CreditoConta,
    PagamentoAplicacaoEstorno, CreditoAplicacaoEstorno)

MODELOS = {"movimentacao": Movimentacao, "lancamento": Lancamento,
    "projecao": Projecao, "conciliacao": Conciliacao, "estorno": Estorno,
    "abatimento_documental": NotaAbatimento}
CAMPOS = {
    "movimentacao": ("id", "codigo", "data_pix", "valor", "saldo_disponivel", "representante_id", "fornecedor_id", "forma_pagamento", "natureza", "status", "updated_at"),
    "lancamento": ("id", "tipo", "natureza", "valor", "saldo_aberto", "data", "representante_id", "fornecedor_id", "origem", "status", "updated_at"),
    "projecao": ("id", "representante_id", "fornecedor_id", "valor_projetado", "valor_conciliado", "data_prevista", "status", "updated_at"),
    "conciliacao": ("id", "movimentacao_id", "alvo_tipo", "alvo_id", "valor", "data", "estornada"),
    "estorno": ("id", "conciliacao_id", "created_at"),
    "abatimento_documental": ("id", "nota_id", "valor", "data", "origem", "estornado", "pagamento_aplicacao_id", "credito_aplicacao_id"),
    "nota": ("id", "pessoa_id", "relacao", "valor_original", "data_emissao", "vencimento", "cancelada", "version"),
    "abatimento": ("id", "nota_id", "valor", "origem", "estornado", "pagamento_aplicacao_id", "credito_aplicacao_id"),
    "abatimento_estorno": ("id", "abatimento_id", "created_at"),
    "pessoa": ("id", "tipo", "ativo"),
    "pagamento_aplicacao": ("id", "pagamento_id", "nota_id", "relacao", "valor", "estornada", "fornecedor_confirmou", "acerto_id"),
    "credito_aplicacao": ("id", "credito_id", "nota_id", "valor", "estornada", "fornecedor_confirmou", "acerto_id"),
    "pagamento": ("id", "tipo", "forma", "valor", "data", "cliente_id", "fornecedor_id", "pagamento_origem_id", "cancelado", "version"),
    "credito": ("id", "pessoa_id", "relacao", "acerto_id", "pagamento_id", "valor_original", "revertido", "version"),
    "pagamento_estorno": ("id", "aplicacao_id", "created_at"),
    "credito_estorno": ("id", "aplicacao_id", "created_at"),
}
DINHEIRO = {"valor", "saldo_disponivel", "saldo_aberto", "valor_projetado", "valor_conciliado", "valor_original"}
SEM_IMPACTO = {"conversao_habilitada": False, "impacto_financeiro": "nenhum"}


def canonico(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonico(value).encode()).hexdigest()


def horario(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


def _decimal(value):
    try:
        n = Decimal(str(value))
        if not n.is_finite():
            raise ValueError
        return n.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise HTTPException(409, "Origem com valor monetário inválido; revisar legado")


def _projecao(tipo, row):
    dados = {}
    for campo in CAMPOS[tipo]:
        value = getattr(row, campo)
        if campo in DINHEIRO:
            value = format(_decimal(value), ".2f")
        elif isinstance(value, (date, datetime)):
            value = value.isoformat()
        dados[campo] = value
    return dados


def query_fonte(db, fonte):
    q = db.query(MODELOS[fonte])
    if fonte == "abatimento_documental":
        q = q.filter(NotaAbatimento.origem == "registro_documental")
    return q


def _vinculos(q):
    rows = q.limit(5001).all()
    if len(rows) > 5000:
        raise HTTPException(413, "Origem com muitos vínculos; dividir a análise do legado")
    return rows


def _grafo(db, fonte, row):
    """Fechamento dos vínculos; limite explícito evita prévias incompletas."""
    vistos, fila = {}, [(fonte, row)]
    while fila:
        tipo, item = fila.pop()
        key = f"{tipo}:{item.id}"
        if key in vistos:
            continue
        if len(vistos) >= 5000:
            raise HTTPException(413, "Origem com muitos vínculos; dividir a análise do legado")
        vistos[key] = _projecao(tipo, item)
        for pid in (getattr(item, "representante_id", None), getattr(item, "fornecedor_id", None), getattr(item, "pessoa_id", None), getattr(item, "cliente_id", None)):
            pessoa = db.get(Pessoa, pid) if pid else None
            if pessoa:
                fila.append(("pessoa", pessoa))
        if tipo == "movimentacao":
            fila.extend(("conciliacao", c) for c in _vinculos(db.query(Conciliacao).filter_by(movimentacao_id=item.id).order_by(Conciliacao.id)))
        elif tipo in ("lancamento", "projecao"):
            fila.extend(("conciliacao", c) for c in _vinculos(db.query(Conciliacao).filter_by(alvo_tipo=tipo, alvo_id=item.id).order_by(Conciliacao.id)))
        elif tipo == "conciliacao":
            m = db.get(Movimentacao, item.movimentacao_id)
            alvo = db.get(MODELOS[item.alvo_tipo], item.alvo_id) if item.alvo_tipo in ("lancamento", "projecao") else None
            if m:
                fila.append(("movimentacao", m))
            if alvo:
                fila.append((item.alvo_tipo, alvo))
            fila.extend(("estorno", e) for e in _vinculos(db.query(Estorno).filter_by(conciliacao_id=item.id).order_by(Estorno.id)))
            # O legado vincula tolerância por descrição exata. Só projetamos
            # dados financeiros do crédito; nunca a descrição livre.
            creditos = _vinculos(db.query(Lancamento).filter_by(origem="tolerancia", descricao=f"Crédito por tolerância (conciliação #{item.id})").order_by(Lancamento.id))
            vistos[key]["creditos_tolerancia_ids"] = [c.id for c in creditos]
            fila.extend(("lancamento", c) for c in creditos)
        elif tipo == "estorno":
            c = db.get(Conciliacao, item.conciliacao_id)
            if c:
                fila.append(("conciliacao", c))
        elif tipo in ("abatimento_documental", "abatimento"):
            n = db.get(NotaObrigacao, item.nota_id)
            if n:
                fila.append(("nota", n))
            fila.extend(("abatimento_estorno", e) for e in _vinculos(db.query(NotaAbatimentoEstorno).filter_by(abatimento_id=item.id).order_by(NotaAbatimentoEstorno.id)))
            for campo, modelo, relacionado in (("pagamento_aplicacao_id", PagamentoAplicacao, "pagamento_aplicacao"), ("credito_aplicacao_id", CreditoAplicacao, "credito_aplicacao")):
                pid = getattr(item, campo)
                vinculo = db.get(modelo, pid) if pid else None
                if vinculo:
                    fila.append((relacionado, vinculo))
        elif tipo == "nota":
            fila.extend(("abatimento", a) for a in _vinculos(db.query(NotaAbatimento).filter_by(nota_id=item.id).order_by(NotaAbatimento.id)))
        elif tipo in ("pagamento_aplicacao", "credito_aplicacao"):
            is_pg = tipo == "pagamento_aplicacao"
            origem_id = item.pagamento_id if is_pg else item.credito_id
            modelo = Pagamento if is_pg else CreditoConta
            pai = db.get(modelo, origem_id)
            if pai:
                fila.append(("pagamento" if is_pg else "credito", pai))
            modelo_estorno = PagamentoAplicacaoEstorno if is_pg else CreditoAplicacaoEstorno
            fila.extend(("pagamento_estorno" if is_pg else "credito_estorno", e) for e in _vinculos(db.query(modelo_estorno).filter_by(aplicacao_id=item.id).order_by(modelo_estorno.id)))
        elif tipo == "credito":
            pg = db.get(Pagamento, item.pagamento_id)
            if pg:
                fila.append(("pagamento", pg))
        elif tipo == "pagamento" and item.pagamento_origem_id:
            pg = db.get(Pagamento, item.pagamento_origem_id)
            if pg:
                fila.append(("pagamento", pg))
    return vistos


def _relacoes(db, fonte, row):
    if fonte == "estorno":
        c = db.get(Conciliacao, row.conciliacao_id)
        return _relacoes(db, "conciliacao", c) if c else []
    if fonte == "conciliacao":
        m = db.get(Movimentacao, row.movimentacao_id)
        alvo = db.get(MODELOS[row.alvo_tipo], row.alvo_id) if row.alvo_tipo in ("lancamento", "projecao") else None
        if not m or not alvo:
            return []
        # Ambos os lados devem concordar; conciliar no legado não valida titular.
        fonte_rel = _relacoes(db, "movimentacao", m)
        return [p for p in _relacoes(db, row.alvo_tipo, alvo) if p in fonte_rel]
    if fonte == "abatimento_documental":
        n = db.get(NotaObrigacao, row.nota_id)
        pares = [(n.pessoa_id, n.relacao)] if n else []
    else:
        pares = [(getattr(row, "representante_id", None), "cliente"), (getattr(row, "fornecedor_id", None), "fornecedor")]
    result = []
    for pid, relacao in pares:
        p = db.get(Pessoa, pid) if pid else None
        papel = "representante" if relacao == "cliente" else "fornecedor"
        if p and p.ativo and p.tipo in (papel, "ambos"):
            result.append({"pessoa_id": pid, "relacao": relacao})
    return result


def _pendencias(fonte, row, graph, relacoes):
    result = []
    if not relacoes:
        result.append("titular_relacao_nao_comprovados")
    if fonte == "movimentacao":
        result.append("trajeto_pagamento_nao_comprovado")
    if fonte == "lancamento":
        result.append("obrigacao_documental_nao_comprovada")
        if row.tipo == "credito":
            result.append("origem_credito_nao_comprovada")
    if fonte == "projecao":
        result.append("projecao_nao_e_obrigacao_documental")
    if fonte in ("conciliacao", "estorno"):
        result.append("destino_documental_e_confirmacao_nao_comprovados")
    if fonte == "abatimento_documental":
        result.append("evento_financeiro_origem_nao_comprovado")
    for key, dados in graph.items():
        tipo = key.split(":", 1)[0]
        for campo, relacao in (("representante_id", "cliente"), ("cliente_id", "cliente"), ("fornecedor_id", "fornecedor"), ("pessoa_id", dados.get("relacao"))):
            pid = dados.get(campo)
            if not pid:
                continue
            pessoa = graph.get(f"pessoa:{pid}")
            papel = "representante" if relacao == "cliente" else "fornecedor"
            if not pessoa:
                result.append("titular_orfao")
            elif not pessoa["ativo"] or (relacao and pessoa["tipo"] not in (papel, "ambos")):
                result.append("titular_incompativel")
        if any(_decimal(dados[k]) < 0 for k in DINHEIRO if k in dados):
            result.append("valor_negativo")
        if tipo == "conciliacao":
            if f"movimentacao:{dados['movimentacao_id']}" not in graph or f"{dados['alvo_tipo']}:{dados['alvo_id']}" not in graph:
                result.append("vinculo_orfao")
            tem_estorno = any(e.get("conciliacao_id") == dados["id"] for k, e in graph.items() if k.startswith("estorno:"))
            if tem_estorno != dados["estornada"]:
                result.append("estorno_divergente")
            tolerancias = [graph[f"lancamento:{pid}"] for pid in dados["creditos_tolerancia_ids"]]
            if len(tolerancias) > 1 or any(c["tipo"] != "credito" or c["natureza"] != "tolerancia" or _decimal(c["valor"]) > _decimal(dados["valor"]) for c in tolerancias):
                result.append("tolerancia_divergente")
            if tolerancias:
                result.append("tolerancia_requer_conferencia")
            m = graph.get(f"movimentacao:{dados['movimentacao_id']}")
            alvo = graph.get(f"{dados['alvo_tipo']}:{dados['alvo_id']}")
            if m and alvo and any(m.get(campo) and alvo.get(campo) and m[campo] != alvo[campo] for campo in ("representante_id", "fornecedor_id")):
                result.append("titulares_conciliacao_divergentes")
        if tipo == "estorno" and f"conciliacao:{dados['conciliacao_id']}" not in graph:
            result.append("vinculo_orfao")
        if tipo in ("abatimento", "abatimento_documental"):
            if f"nota:{dados['nota_id']}" not in graph:
                result.append("vinculo_orfao")
            tem_estorno = any(e.get("abatimento_id") == dados["id"] for k, e in graph.items() if k.startswith("abatimento_estorno:"))
            if tem_estorno != dados["estornado"]:
                result.append("estorno_divergente")
        if tipo == "movimentacao":
            consumido = sum((_decimal(c["valor"]) for k, c in graph.items() if k.startswith("conciliacao:") and c["movimentacao_id"] == dados["id"] and not c["estornada"]), Decimal("0"))
            if _decimal(dados["valor"]) - consumido != _decimal(dados["saldo_disponivel"]):
                result.append("saldo_pix_divergente")
        if tipo in ("lancamento", "projecao"):
            consumido = Decimal("0")
            for ckey, c in graph.items():
                if not ckey.startswith("conciliacao:") or c["estornada"] or c["alvo_tipo"] != tipo or c["alvo_id"] != dados["id"]:
                    continue
                excesso = sum((_decimal(graph[f"lancamento:{pid}"]["valor"]) for pid in c["creditos_tolerancia_ids"]), Decimal("0"))
                consumido += _decimal(c["valor"]) - excesso
            if tipo == "projecao" and consumido != _decimal(dados["valor_conciliado"]):
                result.append("saldo_alvo_divergente")
            if tipo == "projecao" and _decimal(dados["valor_conciliado"]) > _decimal(dados["valor_projetado"]):
                result.append("saldo_alvo_divergente")
            if tipo == "lancamento" and dados["status"] != "cancelado" and _decimal(dados["valor"]) - consumido != _decimal(dados["saldo_aberto"]):
                result.append("saldo_alvo_divergente")
        if tipo == "nota":
            abatimentos = sum((_decimal(a["valor"]) for k, a in graph.items() if k.startswith("abatimento:") and a["nota_id"] == dados["id"] and not a["estornado"]), Decimal("0"))
            if abatimentos > _decimal(dados["valor_original"]):
                result.append("saldo_nota_divergente")
    return sorted(set(result))


def origem(db, fonte, fonte_id):
    row = query_fonte(db, fonte).filter(MODELOS[fonte].id == fonte_id).first()
    if not row:
        raise HTTPException(404, "Origem do legado não encontrada")
    graph = _grafo(db, fonte, row)
    relacoes = _relacoes(db, fonte, row)
    dados = graph[f"{fonte}:{row.id}"]
    ledger = db.query(LegadoClassificacao).filter_by(fonte=fonte, fonte_id=fonte_id).first()
    snapshot_hash = digest({"regra": 1, "origem": [fonte, row.id], "grafo": graph})
    return {"fonte": fonte, "fonte_id": row.id, "snapshot_hash": snapshot_hash,
        "codigo": dados.get("codigo"), "status": dados.get("status", "estornado" if dados.get("estornada", dados.get("estornado", fonte == "estorno")) else "ativo"),
        "data": dados.get("data", dados.get("data_pix", dados.get("data_prevista", dados.get("created_at")))),
        "valores": {k: float(dados[k]) for k in DINHEIRO if k in dados},
        "vinculos": {k: dados[k] for k in ("representante_id", "fornecedor_id", "movimentacao_id", "alvo_tipo", "alvo_id", "conciliacao_id", "nota_id") if k in dados},
        "tipo": dados.get("tipo"), "relacoes_conhecidas": relacoes,
        "pendencias": _pendencias(fonte, row, graph, relacoes),
        "classificacao": {"id": ledger.id, "decisao": ledger.decisao, "lote_id": ledger.lote_id, "snapshot_atual": ledger.snapshot_hash == snapshot_hash} if ledger else None}


def payload_itens(itens):
    return sorted((i.model_dump() for i in itens), key=lambda x: (x["fonte"], x["fonte_id"]))


def previa(db, itens):
    result = []
    for item in sorted(itens, key=lambda i: (i.fonte, i.fonte_id)):
        o = origem(db, item.fonte, item.fonte_id)
        if item.snapshot_hash != o["snapshot_hash"]:
            raise HTTPException(409, "Origem alterada; atualize o inventário e refaça a prévia")
        if o["classificacao"]:
            raise HTTPException(409, "Origem já classificada; consulte o recibo existente")
        if item.pessoa_id and {"pessoa_id": item.pessoa_id, "relacao": item.relacao} not in o["relacoes_conhecidas"]:
            raise HTTPException(422, "Pessoa/relação não comprovadas pelos vínculos da origem")
        bloqueios = {"titular_relacao_nao_comprovados", "titular_orfao", "titular_incompativel", "titulares_conciliacao_divergentes", "vinculo_orfao", "estorno_divergente", "valor_negativo", "saldo_pix_divergente", "saldo_alvo_divergente", "saldo_nota_divergente", "tolerancia_divergente", "tolerancia_requer_conferencia"}
        if item.decisao != "pendente" and bloqueios.intersection(o["pendencias"]):
            raise HTTPException(422, "Origem inconsistente ou sem titular conhecido deve permanecer pendente")
        result.append({**item.model_dump(), "pendencias": o["pendencias"], "valores": o["valores"], "vinculos": o["vinculos"], "relacoes_conhecidas": o["relacoes_conhecidas"]})
    hash_previa = digest({"regra": 1, "itens": result, **SEM_IMPACTO})
    return {"hash_previa": hash_previa, "itens": result, "total": len(result), **SEM_IMPACTO}
