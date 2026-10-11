"""Posições do domínio novo por conta; fluxos de caixa não somam orçamentos."""
from sqlalchemy import select, union, case, func, literal, true
from .models import Pessoa, NotaObrigacao, Pagamento, CreditoConta, Acerto
from .routers import notas, pagamentos, creditos, acertos

COBERTURA = {"legado_integrado": False, "consumo_integrado_habilitado": False}
GRUPOS = {
    "notas": {"valor_original": "n_original", "valor_abatido": "n_abatido", "saldo_aberto": "n_saldo", "saldo_vencido": "n_vencido", "quantidade_ativas": "n_ativas", "quantidade_canceladas": "n_canceladas"},
    "pagamentos": {"valor_elegivel": "p_elegivel", "valor_aplicado": "p_aplicado", "destinado_credito": "p_credito", "saldo_disponivel": "p_saldo", "quantidade_ativos": "p_ativos", "quantidade_cancelados": "p_cancelados"},
    "creditos": {"valor_reconhecido_ativo": "c_original", "valor_aplicado_ativo": "c_usado", "saldo_disponivel": "c_saldo", "quantidade_ativos": "c_ativos", "quantidade_revertidos": "c_revertidos"},
    "acertos": {estado: "a_" + estado for estado in sorted(acertos.ESTADOS)},
}
METRICAS = [col for grupo in GRUPOS.values() for col in grupo.values()]


def _soma(expr):
    return func.coalesce(func.sum(expr), 0)


def _ativos(alias, flag, campos):
    return [_soma(case((getattr(alias.c, flag) == False, expr), else_=0)).label(nome) for nome, expr in campos]


def _contas(db, relacao, pessoa_id=None):
    """Inclui contas históricas mesmo se o papel/estado atual do cadastro mudou."""
    pcol = Pagamento.cliente_id if relacao == "cliente" else Pagamento.fornecedor_id
    tipos = ("cliente_loja", "cliente_fornecedor") if relacao == "cliente" else ("cliente_fornecedor", "repasse_fornecedor")
    papel = "representante" if relacao == "cliente" else "fornecedor"
    queries = [select(Pessoa.id.label("pid")).where(Pessoa.tipo.in_((papel, "ambos"))),
        select(NotaObrigacao.pessoa_id.label("pid")).where(NotaObrigacao.relacao == relacao),
        select(pcol.label("pid")).where(Pagamento.tipo.in_(tipos), pcol.isnot(None)),
        select(CreditoConta.pessoa_id.label("pid")).where(CreditoConta.relacao == relacao),
        select(Acerto.pessoa_id.label("pid")).where(Acerto.relacao == relacao)]
    if pessoa_id is not None:
        # An individual extrato exists for every cadastro/relação, even empty.
        queries.append(select(Pessoa.id.label("pid")).where(Pessoa.id == pessoa_id))
    return union(*queries).subquery()


def contas_statement(db, relacao, pessoa_id=None):
    """One row per person/relation, with grouped SQL shared by extrato and global."""
    nq, _, atraso = notas._consulta_notas(db)
    abatido = nq.column_descriptions[1]["expr"]
    nq = nq.with_entities(NotaObrigacao.pessoa_id.label("pid"), NotaObrigacao.valor_original.label("original"), abatido.label("abatido"),
        func.round(NotaObrigacao.valor_original - abatido, 2).label("saldo"), NotaObrigacao.cancelada.label("cancelada"), atraso.label("atraso"))\
        .filter(NotaObrigacao.relacao == relacao)
    if pessoa_id is not None:
        nq = nq.filter(NotaObrigacao.pessoa_id == pessoa_id)
    ns = nq.subquery()
    nt = select(ns.c.pid, *_ativos(ns, "cancelada", [("n_original", ns.c.original), ("n_abatido", ns.c.abatido), ("n_saldo", ns.c.saldo), ("n_ativas", literal(1))]),
        _soma(case((ns.c.atraso, ns.c.saldo), else_=0)).label("n_vencido"), _soma(case((ns.c.cancelada == True, 1), else_=0)).label("n_canceladas")).group_by(ns.c.pid).subquery()
    pq = pagamentos._query(db)
    pcol = Pagamento.cliente_id if relacao == "cliente" else Pagamento.fornecedor_id
    tipos = ("cliente_loja", "cliente_fornecedor") if relacao == "cliente" else ("cliente_fornecedor", "repasse_fornecedor")
    aplicado = pq.column_descriptions[1 if relacao == "cliente" else 2]["expr"]
    destinado = pq.column_descriptions[6 if relacao == "cliente" else 7]["expr"]
    pq = pq.with_entities(pcol.label("pid"), Pagamento.valor.label("original"), aplicado.label("aplicado"), destinado.label("credito"),
        func.round(Pagamento.valor - aplicado - destinado, 2).label("saldo"), Pagamento.cancelado.label("cancelado")).filter(Pagamento.tipo.in_(tipos))
    if pessoa_id is not None:
        pq = pq.filter(pcol == pessoa_id)
    ps = pq.subquery()
    pg = select(ps.c.pid, *_ativos(ps, "cancelado", [("p_elegivel", ps.c.original), ("p_aplicado", ps.c.aplicado), ("p_credito", ps.c.credito), ("p_saldo", ps.c.saldo), ("p_ativos", literal(1))]),
        _soma(case((ps.c.cancelado == True, 1), else_=0)).label("p_cancelados")).group_by(ps.c.pid).subquery()
    cq, _ = creditos._query(db)
    usado = cq.column_descriptions[1]["expr"]
    cq = cq.with_entities(CreditoConta.pessoa_id.label("pid"), CreditoConta.valor_original.label("original"), usado.label("usado"),
        func.round(CreditoConta.valor_original - usado, 2).label("saldo"), CreditoConta.revertido.label("revertido")).filter(CreditoConta.relacao == relacao)
    if pessoa_id is not None:
        cq = cq.filter(CreditoConta.pessoa_id == pessoa_id)
    cs = cq.subquery()
    cr = select(cs.c.pid, *_ativos(cs, "revertido", [("c_original", cs.c.original), ("c_usado", cs.c.usado), ("c_saldo", cs.c.saldo), ("c_ativos", literal(1))]),
        _soma(case((cs.c.revertido == True, 1), else_=0)).label("c_revertidos")).group_by(cs.c.pid).subquery()
    aq = select(Acerto.pessoa_id.label("pid"), *[_soma(case((Acerto.status == estado, 1), else_=0)).label("a_" + estado) for estado in sorted(acertos.ESTADOS)]).where(Acerto.relacao == relacao)
    if pessoa_id is not None:
        aq = aq.where(Acerto.pessoa_id == pessoa_id)
    acts = aq.group_by(Acerto.pessoa_id).subquery()
    contas = _contas(db, relacao, pessoa_id)
    joined = contas.join(Pessoa, Pessoa.id == contas.c.pid)
    for grupo in (nt, pg, cr, acts):
        joined = joined.outerjoin(grupo, grupo.c.pid == contas.c.pid)
    colunas = [func.coalesce(grupo.c[nome], 0).label(nome) for grupo in (nt, pg, cr, acts) for nome in grupo.c.keys() if nome != "pid"]
    stmt = select(Pessoa.id.label("pessoa_id"), Pessoa.nome.label("pessoa_nome"), Pessoa.tipo.label("pessoa_tipo"), Pessoa.ativo.label("pessoa_ativo"), literal(relacao).label("relacao"), *colunas).select_from(joined)
    if pessoa_id is not None:
        stmt = stmt.where(Pessoa.id == pessoa_id)
    return stmt


def totais(row):
    result = {}
    for grupo, campos in GRUPOS.items():
        result[grupo] = {nome: int(row[coluna]) if nome.startswith("quantidade_") or grupo == "acertos" else round(float(row[coluna]), 2) for nome, coluna in campos.items()}
    result["disponibilidade_total_para_abater"] = round(result["pagamentos"]["saldo_disponivel"] + result["creditos"]["saldo_disponivel"], 2)
    return result


def posicao(row):
    return {"pessoa": {"id": row["pessoa_id"], "nome": row["pessoa_nome"], "tipo": row["pessoa_tipo"], "ativo": row["pessoa_ativo"]}, "relacao": row["relacao"], "totais_globais": totais(row)}


def resumo_statement(db):
    # Two fixed relations, never a query loop per cadastro. All money and
    # cash-flow totals below share one SQL statement/snapshot.
    globais = []
    for relacao in ("cliente", "fornecedor"):
        contas = contas_statement(db, relacao).subquery()
        globais.append(select(literal(relacao).label("relacao"), *[_soma(contas.c[nome]).label(nome) for nome in METRICAS]))
    from sqlalchemy import union_all
    pos = union_all(*globais).subquery()
    cash = select(*[_soma(case(((Pagamento.cancelado == False) & (Pagamento.tipo == tipo), Pagamento.valor), else_=0)).label(nome)
        for tipo, nome in (("cliente_loja", "entrada"), ("repasse_fornecedor", "saida"), ("cliente_fornecedor", "direto"))],
        *[_soma(case(((Pagamento.cancelado == False) & (Pagamento.tipo == tipo), 1), else_=0)).label(nome)
        for tipo, nome in (("cliente_loja", "q_entrada"), ("repasse_fornecedor", "q_saida"), ("cliente_fornecedor", "q_direto"))]).subquery()
    return select(*pos.c, *cash.c).select_from(pos.join(cash, true()))
