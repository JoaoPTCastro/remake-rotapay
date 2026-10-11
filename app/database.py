from fastapi import Depends, Request, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_URL
from .models import Base
from . import interesse_lojas_models  # registra a coleta privada no banco central
from . import organizacoes_models, organizacoes_audit, ambientes_models, fornecedores_models  # registra Base para sessões isoladas

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    from . import models, organizacoes_models, organizacoes_audit  # noqa
    from sqlalchemy import inspect, text
    Base.metadata.create_all(bind=engine)
    # Migração leve: bancos criados antes ganham as colunas novas sem perder dados.
    novas = [
        ("loja", "logo_arquivo", "VARCHAR(80)"),
        ("pagamentos", "origem_registro", "VARCHAR(30)"),
        ("pagamentos", "data_hora_transacao", "TIMESTAMP"),
        ("pagamentos", "remetente", "VARCHAR(160)"),
        ("pagamentos", "favorecido", "VARCHAR(160)"),
        ("pagamentos", "intermediador", "VARCHAR(160)"),
        ("notas_obrigacoes", "condicao_id", "INTEGER REFERENCES catalogos_config(id)"),
        ("notas_obrigacoes", "condicao_nome_snapshot", "VARCHAR(80)"),
        ("notas_obrigacoes", "operacao_id", "INTEGER REFERENCES catalogos_config(id)"),
        ("notas_obrigacoes", "operacao_nome_snapshot", "VARCHAR(80)"),
        ("pagamentos", "forma_id", "INTEGER REFERENCES catalogos_config(id)"),
        ("pagamentos", "forma_nome_snapshot", "VARCHAR(80)"),
        ("pagamentos", "operacao_id", "INTEGER REFERENCES catalogos_config(id)"),
        ("pagamentos", "operacao_nome_snapshot", "VARCHAR(80)"),
        ("acerto_itens", "credito_id", "INTEGER REFERENCES creditos_conta(id)"),
        ("acerto_itens", "credito_version", "INTEGER"),
        ("acerto_itens", "saldo_credito_snapshot", "NUMERIC(12,2)"),
        ("acerto_itens", "credito_dados_snapshot", "TEXT DEFAULT ''"),
        ("credito_aplicacoes", "acerto_id", "INTEGER REFERENCES acertos(id)"),
        ("nota_abatimentos", "credito_aplicacao_id", "INTEGER REFERENCES credito_aplicacoes(id)"),
        ("pagamento_aplicacoes", "acerto_id", "INTEGER REFERENCES acertos(id)"),
        ("nota_abatimentos", "referencia_chave", "VARCHAR(660) DEFAULT ''"),
        ("pagamento_aplicacoes", "fornecedor_confirmou", "BOOLEAN DEFAULT FALSE"),
        ("pagamento_aplicacoes", "referencia_confirmacao", "VARCHAR(220) DEFAULT ''"),
        ("nota_abatimentos", "pagamento_aplicacao_id", "INTEGER REFERENCES pagamento_aplicacoes(id)"),
        ("audit_logs", "ip", "VARCHAR(45) DEFAULT ''"),
        ("pessoas", "prioridade", "INTEGER DEFAULT 2"),
        ("lancamentos", "prioridade", "INTEGER"),
        ("links_pagamento", "chave_pix_id", "INTEGER REFERENCES pessoa_chaves_pix(id)"),
        ("links_pagamento", "chave_snapshot", "VARCHAR(120) DEFAULT ''"),
        ("links_pagamento", "titular_snapshot", "VARCHAR(160) DEFAULT ''"),
        ("links_pagamento", "banco_snapshot", "VARCHAR(60) DEFAULT ''"),
        ("links_pagamento", "agencia_snapshot", "VARCHAR(30) DEFAULT ''"),
        ("links_pagamento", "conta_snapshot", "VARCHAR(60) DEFAULT ''"),
        ("links_pagamento", "tipo_conta_snapshot", "VARCHAR(30) DEFAULT ''"),
        ("links_pagamento", "destino_fixado", "BOOLEAN DEFAULT FALSE"),
    ]
    with engine.begin() as conn:
        if conn.dialect.name == "sqlite":
            conn.exec_driver_sql("BEGIN IMMEDIATE")
        for tabela, coluna, ddl in novas:
            if not coluna:
                continue
            cols = {c["name"] for c in inspect(conn).get_columns(tabela)}
            if coluna not in cols:
                conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {ddl}"))
        from .migrations_acertos import permitir_creditos_em_acertos
        permitir_creditos_em_acertos(conn)
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_nota_credito_app ON nota_abatimentos (credito_aplicacao_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pagamento_aplicacoes_acerto_id ON pagamento_aplicacoes (acerto_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_nota_abatimentos_referencia_chave ON nota_abatimentos (referencia_chave)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_nota_pagamento_app ON nota_abatimentos (pagamento_aplicacao_id)"))
    db = SessionLocal()
    try:
        from .referencias_financeiras import chave_referencia
        for abatimento in db.query(models.NotaAbatimento).all():
            chave = chave_referencia(abatimento.referencia)
            if abatimento.referencia_chave != chave:
                abatimento.referencia_chave = chave
        from .cadastros import backfill_pessoas, backfill_links
        backfill_pessoas(db)
        backfill_links(db)
        db.commit()
        if not db.query(models.Loja).first():
            db.add(models.Loja(nome="Minha Loja"))
            db.commit()
        from .organizacoes_bootstrap import inicializar_organizacao_original
        inicializar_organizacao_original(db)
    finally:
        db.close()


def get_db(request: Request):
    central = SessionLocal()
    local = None
    try:
        from .auth import autenticar_token
        from .ambientes import abrir_financeiro, PAPEIS_INTERNOS
        from .organizacoes import exigir_vinculo
        public_org = getattr(request.state, "public_organizacao_id", None)
        org_id = public_org or 1
        authorization = request.headers.get("authorization", "")
        control_path = request.url.path.startswith(("/auth/", "/organizacoes"))
        # Segredos públicos de extrato não são JWTs e nunca selecionam ambiente privado.
        is_public = public_org is not None or request.url.path.startswith(("/links/v/", "/publico/", "/chave-pix/", "/webhooks/", "/integracao/"))
        if not is_public and authorization.startswith("Bearer "):
            user, org_id = autenticar_token(authorization[7:], central)
            if org_id != 1 and not control_path:
                _, membro = exigir_vinculo(central, user, org_id)
                if membro.perfil not in PAPEIS_INTERNOS:
                    raise HTTPException(403, "Sem acesso financeiro neste ambiente")
        if is_public and not control_path:
            from .organizacoes_models import Organizacao
            if central.query(Organizacao.id).first() is not None:
                org = central.get(Organizacao, org_id)
                if not org or not org.ativo:
                    raise HTTPException(404, "Acesso indisponível")
        contexto = request.headers.get("X-Organizacao-Id")
        if contexto is not None and contexto != str(org_id):
            raise HTTPException(403, "Contexto de organização incompatível")
        request.state.organizacao_id = org_id
        central.info.update(organizacao_id=org_id, controle_session=central, runtime_ambiente=True)
        if org_id != 1 and not control_path:
            local = abrir_financeiro(central, org_id)
            yield local
        else:
            yield central
    finally:
        if local is not None:
            local.close()
        central.close()


def get_control_db(db=Depends(get_db)):
    # A dependência preserva overrides get_db nos testes anteriores; runtime usa controle central.
    yield db.info.get("controle_session", db)
