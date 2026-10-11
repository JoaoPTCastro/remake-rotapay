"""Sugestoes deterministicas para revisao humana de conciliacoes."""
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import Lancamento, Movimentacao, Pessoa, Projecao

TIPOS_PAGAVEIS = ("debito", "despesa", "imposto", "salario")
CRITERIO_DUPLICIDADE = "Mesmo fornecedor, valor e data PIX."


def _dinheiro(valor: float) -> float:
    return round(float(valor), 2)


def detectar_duplicidades(
    db: Session, movimentacoes: list[Movimentacao]
) -> dict[int, dict]:
    """Sinaliza apenas coincidencias exatas, sem alterar as movimentacoes."""
    alertas = {
        m.id: {
            "possivel_duplicidade": False,
            "duplicidade_movimentacao_ids": [],
            "duplicidade_criterio": None,
        }
        for m in movimentacoes
    }
    elegiveis = [
        m for m in movimentacoes
        if m.id is not None and m.fornecedor_id is not None and m.status != "cancelada"
    ]
    if not elegiveis:
        return alertas

    fornecedores = {m.fornecedor_id for m in elegiveis}
    datas = {m.data_pix for m in elegiveis}
    candidatas = db.query(Movimentacao).filter(
        Movimentacao.fornecedor_id.in_(fornecedores),
        Movimentacao.data_pix.in_(datas),
        Movimentacao.status != "cancelada",
    ).all()
    por_criterio: dict[tuple[int, float, object], list[int]] = {}
    for candidata in candidatas:
        chave = (
            candidata.fornecedor_id,
            _dinheiro(candidata.valor),
            candidata.data_pix,
        )
        por_criterio.setdefault(chave, []).append(candidata.id)

    for movimentacao in elegiveis:
        chave = (
            movimentacao.fornecedor_id,
            _dinheiro(movimentacao.valor),
            movimentacao.data_pix,
        )
        semelhantes = sorted(
            mid for mid in por_criterio.get(chave, []) if mid != movimentacao.id
        )
        if semelhantes:
            alertas[movimentacao.id] = {
                "possivel_duplicidade": True,
                "duplicidade_movimentacao_ids": semelhantes,
                "duplicidade_criterio": CRITERIO_DUPLICIDADE,
            }
    return alertas


def _montar_sugestao(
    alvo_tipo: str,
    alvo_id: int,
    fornecedor_id: int,
    saldo_alvo: float,
    saldo_pix: float,
    data_pix,
    data_alvo,
) -> tuple[tuple, dict]:
    saldo_alvo = _dinheiro(saldo_alvo)
    saldo_exato = abs(saldo_alvo - saldo_pix) < 0.005
    distancia = abs((data_alvo - data_pix).days) if data_alvo else None
    criterio_data = (
        f"datas com diferenca de {distancia} dia(s)"
        if distancia is not None else "data do alvo nao informada"
    )
    motivo = (
        "Mesmo fornecedor; "
        f"{'saldo exato' if saldo_exato else 'conciliacao parcial segura'}; "
        f"{criterio_data}."
    )
    sugestao = {
        "alvo_tipo": alvo_tipo,
        "alvo_id": alvo_id,
        "fornecedor_id": fornecedor_id,
        "saldo_alvo": saldo_alvo,
        "valor_sugerido": _dinheiro(min(saldo_pix, saldo_alvo)),
        "data_alvo": str(data_alvo) if data_alvo else None,
        "confianca": "alta" if saldo_exato else "media",
        "motivo": motivo,
    }
    ordem = (
        not saldo_exato,
        distancia is None,
        distancia if distancia is not None else 0,
        0 if alvo_tipo == "lancamento" else 1,
        alvo_id,
    )
    return ordem, sugestao


def sugerir_conciliacoes(db: Session, movimentacao: Movimentacao) -> list[dict]:
    """Retorna alvos elegiveis e valores seguros, sem criar conciliacoes."""
    saldo_pix = _dinheiro(movimentacao.saldo_disponivel)
    if (
        movimentacao.fornecedor_id is None
        or movimentacao.status not in ("disponivel", "parcial")
        or saldo_pix <= 0
    ):
        return []

    sugestoes = []
    lancamentos = db.query(Lancamento).filter(
        Lancamento.fornecedor_id == movimentacao.fornecedor_id,
        Lancamento.tipo.in_(TIPOS_PAGAVEIS),
        Lancamento.status.in_(("aberto", "parcial")),
        Lancamento.saldo_aberto > 0,
    ).all()
    for lancamento in lancamentos:
        sugestoes.append(_montar_sugestao(
            "lancamento", lancamento.id, lancamento.fornecedor_id,
            lancamento.saldo_aberto, saldo_pix, movimentacao.data_pix, lancamento.data,
        ))

    if movimentacao.representante_id is not None:
        projecoes = db.query(Projecao).filter(
            Projecao.fornecedor_id == movimentacao.fornecedor_id,
            Projecao.representante_id == movimentacao.representante_id,
            Projecao.status.in_(("aberta", "parcial")),
        ).all()
        for projecao in projecoes:
            if projecao.saldo <= 0:
                continue
            sugestoes.append(_montar_sugestao(
                "projecao", projecao.id, projecao.fornecedor_id,
                projecao.saldo, saldo_pix, movimentacao.data_pix, projecao.data_prevista,
            ))

    sugestoes.sort(key=lambda item: item[0])
    return [sugestao for _, sugestao in sugestoes]


def fila_pagamentos(db: Session, hoje: date | None = None) -> list[dict]:
    """Rodízio de pagamentos (leitura da lógica da planilha).

    Por fornecedor com débito em aberto: identifica a nota mais antiga
    (menor data com saldo, desempate por id) e quanto falta para quitá-la.
    Ordem: prioridade do fornecedor, data da nota antiga, menor faltante
    (quitar notas pequenas libera posições no rodízio).
    Nunca altera nada — só propõe a ordem para decisão humana.
    """
    hoje = hoje or date.today()
    abertos = db.query(Lancamento).filter(
        Lancamento.tipo.in_(TIPOS_PAGAVEIS),
        Lancamento.status.in_(("aberto", "parcial")),
        Lancamento.saldo_aberto > 0,
        Lancamento.fornecedor_id.isnot(None),
    ).order_by(Lancamento.data.asc(), Lancamento.id.asc()).all()
    por_forn: dict[int, list[Lancamento]] = {}
    for lanc in abertos:
        por_forn.setdefault(lanc.fornecedor_id, []).append(lanc)
    nomes = {p.id: p.nome for p in db.query(Pessoa).filter(
        Pessoa.id.in_(list(por_forn))).all()}
    prios = {p.id: p.prioridade for p in db.query(Pessoa).filter(
        Pessoa.id.in_(list(por_forn))).all()}
    pix = dict(db.query(
        Movimentacao.fornecedor_id,
        func.coalesce(func.sum(Movimentacao.saldo_disponivel), 0),
    ).filter(
        Movimentacao.fornecedor_id.in_(por_forn),
        Movimentacao.status.in_(("disponivel", "parcial")),
    ).group_by(Movimentacao.fornecedor_id).all())

    fila = []
    for fid, lancs in por_forn.items():
        antiga = lancs[0]
        total = _dinheiro(sum(l.saldo_aberto for l in lancs))
        faltante = _dinheiro(antiga.saldo_aberto)
        em_maos = _dinheiro(pix.get(fid, 0))
        fila.append({
            "fornecedor_id": fid,
            "fornecedor_nome": nomes.get(fid, f"#{fid}"),
            "prioridade": prios.get(fid, 2),
            "nota_antiga": {
                "id": antiga.id,
                "data": str(antiga.data),
                "valor": _dinheiro(antiga.valor),
                "saldo_aberto": faltante,
                "dias_em_aberto": (hoje - antiga.data).days,
            },
            "total_devido": total,
            "faltante_nota_antiga": faltante,
            "pix_em_maos": em_maos,
            "quitavel_agora": em_maos >= faltante,
            "ordem": (prios.get(fid, 2), str(antiga.data), antiga.id,
                      faltante),
        })
    fila.sort(key=lambda item: (item["ordem"][0], item["ordem"][1],
                                item["ordem"][3], item["ordem"][2]))
    for item in fila:
        del item["ordem"]
    return fila


def propostas_projecao(db: Session) -> list[dict]:
    """Compõe projeções PIX disponível × dívida, por (representante, fornecedor).

    Segue a ordem do rodízio (prioridade do fornecedor, dívida mais antiga).
    Nunca persiste — só propõe para aprovação humana (RN-006 respeitada na
    aplicação: par com projeção aberta/parcial é listado como já existente).
    """
    pares = db.query(
        Movimentacao.representante_id,
        Movimentacao.fornecedor_id,
        func.coalesce(func.sum(Movimentacao.saldo_disponivel), 0),
    ).filter(
        Movimentacao.representante_id.isnot(None),
        Movimentacao.fornecedor_id.isnot(None),
        Movimentacao.status.in_(("disponivel", "parcial")),
        Movimentacao.saldo_disponivel > 0,
    ).group_by(Movimentacao.representante_id, Movimentacao.fornecedor_id).all()
    if not pares:
        return []
    forn_ids = {f for _, f, _ in pares}
    dividas = dict(db.query(
        Lancamento.fornecedor_id,
        func.coalesce(func.sum(Lancamento.saldo_aberto), 0),
    ).filter(
        Lancamento.fornecedor_id.in_(forn_ids),
        Lancamento.tipo.in_(TIPOS_PAGAVEIS),
        Lancamento.status.in_(("aberto", "parcial")),
    ).group_by(Lancamento.fornecedor_id).all())
    mais_antiga = dict(db.query(
        Lancamento.fornecedor_id,
        func.min(Lancamento.data),
    ).filter(
        Lancamento.fornecedor_id.in_(forn_ids),
        Lancamento.tipo.in_(TIPOS_PAGAVEIS),
        Lancamento.status.in_(("aberto", "parcial")),
        Lancamento.saldo_aberto > 0,
    ).group_by(Lancamento.fornecedor_id).all())
    existentes = {(p.representante_id, p.fornecedor_id) for p in db.query(Projecao).filter(
        Projecao.status.in_(("aberta", "parcial"))).all()}
    pessoas = {p.id: p for p in db.query(Pessoa).filter(
        Pessoa.id.in_(forn_ids | {r for r, _, _ in pares})).all()}

    propostas = []
    for rep_id, forn_id, pix in pares:
        pix_v = _dinheiro(pix)
        divida = _dinheiro(dividas.get(forn_id, 0))
        if divida <= 0:
            continue
        forn = pessoas.get(forn_id)
        rep = pessoas.get(rep_id)
        propostas.append({
            "representante_id": rep_id,
            "representante_nome": rep.nome if rep else f"#{rep_id}",
            "fornecedor_id": forn_id,
            "fornecedor_nome": forn.nome if forn else f"#{forn_id}",
            "prioridade": forn.prioridade if forn else 2,
            "pix_disponivel": pix_v,
            "divida_aberta": divida,
            "valor_proposto": _dinheiro(min(pix_v, divida)),
            "nota_mais_antiga": str(mais_antiga[forn_id]) if forn_id in mais_antiga else None,
            "ja_existe": (rep_id, forn_id) in existentes,
            "motivo": (f"PIX de {rep.nome if rep else '?'} cobre "
                       f"{'toda a dívida' if pix_v >= divida else 'parte da dívida'} "
                       f"de {forn.nome if forn else '?'}; nota mais antiga "
                       f"{mais_antiga[forn_id] if forn_id in mais_antiga else '—'}."),
        })
    propostas.sort(key=lambda p: (p["prioridade"], p["nota_mais_antiga"] or "",
                                   -p["valor_proposto"]))
    return propostas
