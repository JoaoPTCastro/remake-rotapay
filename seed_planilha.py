"""Seed fiel à planilha original (aba CONTROLE SAÍDAS), com 5 fornecedores.

Colunas da planilha -> modelo:
  DATA/CONTROLE + CLIENTE        -> data (lançamento) + representante Daniel Luís Teixeira
  DADOS DO COMPROVANTE (data)    -> movimentacao.data_pix (01-02/09/2026)
  VALOR                          -> valor (760 / 687 / 410 nas 3 primeiras + faixa 200-1800)
  AUTOR                          -> observacao "Lançado por X"
  REMETENTE                      -> remetente (JOAO PEDRO)
  FORNECEDOR                     -> 5 fornecedores, cada um com sua chave PIX
  FORMA PAG. = PIX, NATUREZA     -> despesa (lancamento tipo=despesa)
  OBSERVAÇÃO                     -> "O FUNCIONARIO/ LANCADO NO SISTEMA"
  CONCILIAÇÃO (checkboxes vazios)-> maioria pendente; ~30% conciliado p/ demo

Total alvo: R$ 898.761,88 (soma do rodapé da planilha).
Limpa dados de demonstração anteriores (mantém usuários).
Só roda com ALLOW_SEED=true.
"""
import os
import random
import sys
from datetime import date

if os.getenv("ALLOW_SEED", "false").lower() != "true":
    sys.exit("Recusado: defina ALLOW_SEED=true (nunca em produção)")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_db
from app.models import (User, Pessoa, Movimentacao, Projecao, Lancamento,
                        Conciliacao, Estorno, AuditLog)
from app.services import conciliar

random.seed(20260902)
ALVO = 898_761.88

# (nome, documento, chave_pix, banco, conta, prazo_dias, peso)
FORNS = [
    ("JOAO PEDRO THEOTONIO DE", "123.456.789-00", "joao.pedro@pag.com",
     "Itaú", "0041-88231-5", 14, 0.45),
    ("ATACADAO DAS RIFAS LTDA", "12.345.678/0001-90", "12345678000190",
     "Bradesco", "1122-00981-3", 21, 0.20),
    ("MARIA DAS GRACAS SILVA", "987.654.321-00", "98765432100",
     "Nubank", "0001-77412-9", 7, 0.15),
    ("DISTRIBUIDORA NORDESTE SA", "98.765.432/0001-10", "a1b2c3d4-5678-90ab-cdef-1234567890ab",
     "Inter", "0001-55123-0", 30, 0.12),
    ("CARLOS HENRIQUE SOUZA", "456.789.123-00", "+5585991234567",
     "Banco do Brasil", "3100-44501-8", 10, 0.08),
]

init_db()
db = SessionLocal()
admin = db.query(User).filter_by(email="admin@local").first()
assert admin, "rode seed-admin antes"

# limpa demo anterior (ordem respeita FKs)
for t in (Estorno, Conciliacao, Movimentacao, Projecao, Lancamento, Pessoa, AuditLog):
    db.query(t).delete()
db.flush()

daniel = Pessoa(tipo="representante", nome="DANIEL LUÍS TEIXEIRA",
                documento="042.XXX.XXX-00")
db.add(daniel)
forns = []
for nome, doc, chave, banco, conta, prazo, _ in FORNS:
    f = Pessoa(tipo="fornecedor", nome=nome, documento=doc, chave_pix=chave,
               banco=banco, conta=conta, titular_chave=nome.title(),
               prazo_dias=prazo)
    db.add(f)
    forns.append(f)
db.flush()
autoras = []
for nome in ("ANNA CLARA", "RAINNY", "THALITA"):
    a = Pessoa(tipo="representante", nome=f"{nome} (AUTORA)",
               observacoes="Autora de lançamentos na planilha original")
    db.add(a)
    autoras.append(a)
db.flush()

pesos = [w for *_, w in FORNS]
autores = ["ANNA CLARA", "RAINNY", "THALITA"]
base_vals = [760.00, 687.00, 410.00]

por_forn: dict[int, list[Movimentacao]] = {f.id: [] for f in forns}
total = 0.0
i = 0
while total < ALVO:
    i += 1
    faltam = round(ALVO - total, 2)
    if faltam <= 1800:
        valor = faltam
    elif i <= 3:
        valor = base_vals[i - 1]  # 3 primeiras linhas = print
    else:
        valor = round(random.uniform(200, 1800), 2)
    forn = forns[0] if i <= 3 else random.choices(forns, weights=pesos)[0]
    autor = autores[(i - 1) % 3] if i <= 3 else random.choice(autores)
    m = Movimentacao(
        codigo="PIX-TMP",
        data_pix=date(2026, 9, 1) if i % 2 else date(2026, 9, 2),
        valor=valor, saldo_disponivel=valor,
        remetente="JOAO PEDRO", representante_id=daniel.id,
        destinatario="Empresa", fornecedor_id=forn.id,
        autor=autor, forma_pagamento="PIX", natureza="DESPESA",
        status="disponivel", created_by=admin.id,
        observacao="O FUNCIONARIO/ LANCADO NO SISTEMA")
    db.add(m)
    db.flush()
    m.codigo = f"PIX-{m.id:06d}"
    por_forn[forn.id].append(m)
    total = round(total + valor, 2)

# por fornecedor: débito cobrindo ~30% (conciliado) + NFs em aberto p/ o resto
conciliados = 0
nf = 200
for forn in forns:
    movs = sorted(por_forn[forn.id], key=lambda m: m.id)
    soma = round(sum(m.valor for m in movs), 2)
    if soma <= 0:
        continue
    alvo = round(soma * 0.30, 2)
    deb = Lancamento(tipo="despesa", natureza="DESPESA", valor=alvo,
                     saldo_aberto=alvo, data=date(2026, 9, 1),
                     fornecedor_id=forn.id, descricao="Despesas 01-02/09 (planilha)",
                     origem="planilha", status="aberto", created_by=admin.id)
    db.add(deb)
    db.flush()
    gasto = 0.0
    for m in movs:
        if gasto + m.valor > alvo:
            break
        conciliar(db, m.id, "lancamento", deb.id, m.valor, admin.id)
        gasto = round(gasto + m.valor, 2)
        conciliados += 1
    restante = round(soma - gasto, 2)
    while restante > 0.005:
        parte = round(min(restante, random.uniform(30000, 90000)), 2)
        db.add(Lancamento(tipo="despesa", natureza="DESPESA", valor=parte,
                          saldo_aberto=parte, data=date(2026, 9, 2),
                          fornecedor_id=forn.id, descricao=f"NF {nf} (planilha)",
                          origem="planilha", status="aberto", created_by=admin.id))
        restante = round(restante - parte, 2)
        nf += 1

# projeções abertas em combos distintos (RN-006)
db.add(Projecao(representante_id=daniel.id, fornecedor_id=forns[0].id,
                valor_projetado=50000.00, valor_conciliado=0.0, status="aberta",
                data_prevista=date(2026, 9, 30), observacao="Projeção set/2026"))
db.add(Projecao(representante_id=autoras[0].id, fornecedor_id=forns[1].id,
                valor_projetado=30000.00, valor_conciliado=0.0, status="aberta",
                data_prevista=date(2026, 9, 30), observacao="Projeção set/2026"))
db.commit()
print(f"PLANILHA OK: {i} PIX somando R$ {total:,.2f} em {len(forns)} fornecedores | "
      f"{conciliados} conciliados")
for forn in forns:
    soma = round(sum(m.valor for m in por_forn[forn.id]), 2)
    print(f"  - {forn.nome}: {len(por_forn[forn.id])} PIX R$ {soma:,.2f} | chave {forn.chave_pix}")
