"""Migração preservadora das fontes de AcertoItem, somente durante init_db."""
import re
from sqlalchemy import inspect, text


def _permitir_creditos_em_acertos(conn):
    cols = {c["name"]: c for c in inspect(conn).get_columns("acerto_itens")}
    nomes = ("pagamento_id", "pagamento_version", "saldo_pagamento_snapshot")
    if conn.dialect.name == "sqlite" and any(not cols[n]["nullable"] for n in nomes):
        original = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='acerto_itens'")).scalar_one()
        indices = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='acerto_itens' AND sql IS NOT NULL")).scalars().all()
        triggers = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='trigger' AND tbl_name='acerto_itens'")).scalars().all()
        sql = re.sub(r'CREATE TABLE\s+(?:"acerto_itens"|acerto_itens)', "CREATE TABLE acerto_itens_sprint6", original, count=1, flags=re.I)
        for nome in nomes:
            sql = re.sub(r'("?' + nome + r'"?\s+(?:INTEGER|NUMERIC\s*\(12,\s*2\)))\s+NOT NULL', r'\1', sql, flags=re.I)
        pos = sql.rfind(")")
        sql = sql[:pos] + ', CHECK ((pagamento_id IS NOT NULL AND credito_id IS NULL) OR (pagamento_id IS NULL AND credito_id IS NOT NULL))' + sql[pos:]
        conn.execute(text(sql))
        nomes_col = ", ".join('"' + n.replace('"', '""') + '"' for n in cols)
        conn.execute(text(f"INSERT INTO acerto_itens_sprint6 ({nomes_col}) SELECT {nomes_col} FROM acerto_itens"))
        conn.execute(text("DROP TABLE acerto_itens"))
        conn.execute(text("ALTER TABLE acerto_itens_sprint6 RENAME TO acerto_itens"))
        for ddl in indices + triggers:
            conn.execute(text(ddl))
    elif conn.dialect.name == "postgresql":
        for nome in nomes:
            if not cols[nome]["nullable"]:
                conn.execute(text(f"ALTER TABLE acerto_itens ALTER COLUMN {nome} DROP NOT NULL"))
    if conn.dialect.name == "postgresql" and not any(c["name"] == "ck_acerto_fonte" for c in inspect(conn).get_check_constraints("acerto_itens")):
        conn.execute(text("ALTER TABLE acerto_itens ADD CONSTRAINT ck_acerto_fonte CHECK ((pagamento_id IS NOT NULL AND credito_id IS NULL) OR (pagamento_id IS NULL AND credito_id IS NOT NULL))"))
    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_acerto_par_credito ON acerto_itens (acerto_id, credito_id, nota_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_acerto_itens_credito_id ON acerto_itens (credito_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_credito_aplicacoes_acerto_id ON credito_aplicacoes (acerto_id)"))


def permitir_creditos_em_acertos(conn):
    # SAVEPOINT garante rollback do rebuild mesmo em sqlite3 legacy transaction.
    with conn.begin_nested():
        _permitir_creditos_em_acertos(conn)
