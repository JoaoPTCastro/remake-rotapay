"""Painel privado do novo domínio, sem inferir integração ou executar rodízio."""
import csv
import io
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..auth import need
from ..database import get_db
from ..models import User, Pessoa, NotaObrigacao
from ..visao_geral import contas_statement, resumo_statement, posicao, totais, COBERTURA, GRUPOS
from . import notas

r = APIRouter(prefix="/visao-geral", tags=["visao-geral"])
LEITURA = need("admin", "financeiro", "operador", "consulta")
Relacao = Literal["cliente", "fornecedor"]
MAX_EXPORT = 10000


def _privado(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"


def _filtros(q, coluna_id, coluna_nome, pessoa_id, busca):
    if pessoa_id is not None:
        q = q.where(coluna_id == pessoa_id)
    if busca:
        # Literal substring: user %/_ must not expand the search scope.
        q = q.where(func.lower(coluna_nome).contains(busca.strip().lower(), autoescape=True))
    return q


def _pagina(itens, total, limit, offset, relacao, pessoa_id, q):
    return {"itens": itens, "total_filtrado": total, "limit": limit, "offset": offset,
        "tem_mais": offset + len(itens) < total,
        "filtros": {"relacao": relacao, "pessoa_id": pessoa_id, "q": q},
        "escopo": "dominio_novo", "cobertura": COBERTURA}


@r.get("/resumo")
def resumo(response: Response, db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    _privado(response)
    rows = db.execute(resumo_statement(db)).mappings().all()
    cash = rows[0]
    money = lambda campo: round(float(cash[campo]), 2)
    return {"escopo": "dominio_novo", "cobertura": COBERTURA,
        "contas": {row["relacao"]: totais(row) for row in rows},
        "fluxo_caixa": {"entradas_cliente_loja": money("entrada"),
            "saidas_repasse_fornecedor": money("saida"), "saldo_liquido": round(money("entrada") - money("saida"), 2),
            "pagamentos_diretos_cliente_fornecedor": money("direto"),
            "quantidade_entradas": int(cash["q_entrada"]), "quantidade_saidas": int(cash["q_saida"]), "quantidade_diretos": int(cash["q_direto"])}}


def _posicoes_query(db, relacao, pessoa_id, q):
    contas = contas_statement(db, relacao).subquery()
    query = select(contas)
    return _filtros(query, contas.c.pessoa_id, contas.c.pessoa_nome, pessoa_id, q), contas


@r.get("/posicoes")
def posicoes(relacao: Relacao, response: Response, pessoa_id: int | None = Query(None, gt=0),
        q: str | None = Query(None, max_length=120), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
        db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    _privado(response)
    stmt, contas = _posicoes_query(db, relacao, pessoa_id, q)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(stmt.order_by(contas.c.pessoa_nome.asc(), contas.c.pessoa_id.asc()).offset(offset).limit(limit)).mappings().all()
    return _pagina([posicao(row) for row in rows], total, limit, offset, relacao, pessoa_id, q)


@r.get("/fila")
def fila(relacao: Relacao, response: Response, pessoa_id: int | None = Query(None, gt=0),
        q: str | None = Query(None, max_length=120), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
        db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    _privado(response)
    nq, _, atraso = notas._consulta_notas(db)
    abatido = nq.column_descriptions[1]["expr"]
    saldo = func.round(NotaObrigacao.valor_original - abatido, 2)
    stmt = nq.with_entities(NotaObrigacao.id.label("id"), NotaObrigacao.pessoa_id.label("pessoa_id"), Pessoa.nome.label("pessoa_nome"),
        NotaObrigacao.relacao.label("relacao"), NotaObrigacao.numero_documento.label("numero_documento"), NotaObrigacao.data_emissao.label("data_emissao"),
        NotaObrigacao.vencimento.label("vencimento"), NotaObrigacao.valor_original.label("valor_original"), abatido.label("valor_abatido"), saldo.label("saldo_aberto"), atraso.label("em_atraso"))\
        .filter(NotaObrigacao.relacao == relacao, NotaObrigacao.cancelada == False, saldo > 0).statement
    stmt = _filtros(stmt, NotaObrigacao.pessoa_id, Pessoa.nome, pessoa_id, q)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(NotaObrigacao.vencimento.asc().nulls_last(), NotaObrigacao.data_emissao.asc(), NotaObrigacao.id.asc()).offset(offset).limit(limit)
    rows = db.execute(stmt).mappings().all()
    itens = []
    for row in rows:
        item = dict(row)
        for campo in ("valor_original", "valor_abatido", "saldo_aberto"):
            item[campo] = round(float(item[campo]), 2)
        item["url"] = f"/notas/{item['id']}"
        itens.append(item)
    return {**_pagina(itens, total, limit, offset, relacao, pessoa_id, q), "ordem": "vencimento_emissao_id", "programacao_automatica": False}


def _celula(valor):
    texto = str(valor)
    # Excel also interprets formulas after whitespace/control characters.
    if texto.lstrip().startswith(("=", "+", "-", "@")) or texto.startswith(("\t", "\r", "\n")):
        return "'" + texto
    return texto


@r.get("/export.csv")
def exportar(relacao: Relacao, pessoa_id: int | None = Query(None, gt=0), q: str | None = Query(None, max_length=120),
        db: Session = Depends(get_db), u: User = Depends(LEITURA)):
    stmt, contas = _posicoes_query(db, relacao, pessoa_id, q)
    rows = db.execute(stmt.order_by(contas.c.pessoa_nome.asc(), contas.c.pessoa_id.asc()).limit(MAX_EXPORT + 1)).mappings().all()
    if len(rows) > MAX_EXPORT:
        raise HTTPException(413, "Exportação excede 10.000 contas; refine os filtros")
    campos = [(grupo, nome) for grupo, metricas in GRUPOS.items() for nome in metricas]
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(["pessoa_id", "pessoa_nome", "relacao", "cadastro_ativo", *[f"{grupo}_{nome}" for grupo, nome in campos], "disponibilidade_total_para_abater", "cobertura"])
    for row in rows:
        values = totais(row)
        cells = [_celula(row["pessoa_id"]), _celula(row["pessoa_nome"]), relacao, "sim" if row["pessoa_ativo"] else "não"]
        for grupo, nome in campos:
            n = values[grupo][nome]
            cells.append(str(n) if nome.startswith("quantidade_") or grupo == "acertos" else f"{n:.2f}".replace(".", ","))
        cells.extend([f"{values['disponibilidade_total_para_abater']:.2f}".replace(".", ","), "domínio novo; legado não integrado"])
        writer.writerow(cells)
    response = Response(content="\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="rotapay-posicoes-{relacao}.csv"'
    _privado(response)
    return response
