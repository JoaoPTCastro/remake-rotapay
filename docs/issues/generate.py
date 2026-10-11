"""Gera docs/issues/ — um .md por issue das Sprints 0-8 + import.sh (gh CLI).

Adaptação de stack vs roadmap original: Go→FastAPI, PostgreSQL→SQLite migrável,
React(Vite)→Next.js. Status reflete o MVP já construído em pix-conciliacao-mvp/.
Uso: python3 docs/issues/generate.py
"""
import os
import textwrap
import unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)))

# (sprint, titulo, pontos, status, evidencia, tarefas, aceite)
ISSUES = [
 # ---- Sprint 0 ----
 (0, "PRD do MVP aprovado", 3, "done", "PRD §§1–33 + Resumo das reuniões + Roadmaps em Downloads/Arquivar",
  ["Consolidar PRD com personas, jornadas, RFs e regras anti-crédito", "Anexar atas como base de domínio (cadeia rifas)"],
  ["PRD e atas aprovados pelo PO"]),
 (0, "Arquitetura alto nível + diagrama", 3, "done", "docs/arquitetura.md (cadeia + componentes + ADRs)",
  ["Diagramar componentes (web → API → SQLite → uploads)", "Registrar ADR da troca Go→FastAPI / PG→SQLite migrável"],
  ["Documento de arquitetura aprovado; diagrama reflete o código atual"]),
 (0, "Modelos de dados iniciais", 3, "done", "app/models.py",
  ["Pessoa (representante/fornecedor), Movimentação, Projeção, Lançamento, Conciliação, Estorno, AuditLog"],
  ["Modelos cobrem §18 do PRD; migração Postgres via DATABASE_URL sem SQL cru"]),
 (0, "Monorepo backend/frontend com padrões", 2, "done", "app/ + frontend/ + requirements + README runbook",
  ["Estrutura app/routers, lib/api+actions, middleware de auth", "README com runbook de dev"],
  ["Dev sobe API (:8000) e web (:3000) com .env locais"]),
 (0, "CI básico (lint, build, testes)", 2, "done", ".github/workflows/ci.yml validado",
  ["Workflow: pytest backend + tsc + next build + eslint", "Branch strategy main/dev"],
  ["CI verde a cada push; build quebrado bloqueia merge"]),
 (0, "Docker Compose dev/staging", 2, "done", "Dockerfile.api/web + compose validado (sem docker local)",
  ["Serviços api + web + volume sqlite/uploads", "Envs de exemplo"],
  ["`docker compose up` sobe o MVP localmente"]),
 # ---- Sprint 1 ----
 (1, "Estrutura do backend + convenções", 2, "done", "app/routers/*, app/services.py (regras RN)",
  ["Routers por domínio; services com RN-003/006/007/008"],
  ["Novos endpoints seguem o padrão existente"]),
 (1, "Auth JWT + perfis", 3, "done", "app/auth.py, app/routers/auth.py (admin|financeiro|operador|consulta)",
  ["Login, seed-admin travado em prod, guard need()", "Cookie httpOnly no frontend"],
  ["Login funciona; perfil consulta não escreve; 401/403 corretos"]),
 (1, "Modelos + banco migrável", 3, "done", "app/models.py (Numeric 12,2), app/database.py",
  ["Precisão fixa p/ dinheiro; código PIX sem race (id pós-flush)"],
  ["Sem erro de centavos; sem duplicidade de código"]),
 (1, "CRUDs pessoas e movimentações", 3, "done", "routers/pessoas.py, movimentacoes.py",
  ["Representantes/fornecedores, PIX, filtros, paginação, cancelamento lógico"],
  ["CRUD com testes; conciliada nunca some (RN-004)"]),
 (1, "Testes unitários backend", 2, "done", "tests/test_mvp.py (5 passed, banco isolado)",
  ["Parcial/integral, excedente, RN-002/003/006/008, permissões, auditoria"],
  ["pytest verde em CI"]),
 # ---- Sprint 2 ----
 (2, "Upload de comprovante + metadados", 3, "done", "POST /movimentacoes/{id}/comprovante",
  ["Validação extensão (pdf/png/jpg/webp) e tamanho 10MB"],
  ["Upload grava arquivo e vincula à movimentação"]),
 (2, "Armazenamento local + download", 2, "done", "uploads/{id}/ + GET comprovante",
  ["Path fora do git; download autenticado"],
  ["Comprovante recuperável depois (RF-080)"]),
 (2, "Entidade Comprovante própria", 3, "done", "models.Comprovante + GET/PATCH comprovantes",
  ["Tabela comprovantes (id, mov_id, arquivo, origem, enviado_por, data_comprovante vs lançamento)", "Migrar path atual"],
  ["Trilha quem enviou + data do comprovante vs lançamento (ata)"]),
 (2, "Fila async p/ processamento", 3, "done", "models.Job + GET/POST /jobs/processar (stub p/ OCR)",
  ["Fila simples p/ OCR futuro (stub primeiro)", "Worker consome e atualiza status"],
  ["Upload enfileira mensagem de processamento"]),
 (2, "Testes de upload", 2, "done", "test_upload_comprovante_e_fila",
  ["Upload válido/inválido, limite de tamanho, download 404"],
  ["Cobertura do fluxo de comprovante"]),
 # ---- Sprint 3 (OCR) ----
 (3, "Worker OCR stub", 2, "done", "jobs.processar extrai+sugere (ocr.py)",
  ["Worker consome fila e simula extração"],
  ["Worker processa e popula campos extraídos"]),
 (3, "Extração valor/data/remetente/destinatário/chave", 3, "done", "ocr.extrair + confiança por campo",
  ["Schema de campos extraídos + confiança por campo"],
  ["Campos extraídos salvos p/ revisão"]),
 (3, "Mapeamento p/ fornecedor + lançamento automático parcial", 3, "done", "ocr.sugerir_fornecedor (só sugere)",
  ["Match por chave PIX/nome; só sugere, não concilia sozinho"],
  ["Sugestão registrada sem gerar crédito automático"]),
 (3, "Revisão manual do OCR", 2, "done", "/revisao aceitar/rejeitar + fila",
  ["Tela de revisão na web com antes/depois"],
  ["Usuário corrige dados extraídos via UI"]),
 (3, "E2E upload→extração", 2, "done", "test_ocr_sugestao_revisao_e_dedup",
  ["Teste ponta a ponta com comprovante fixture"],
  ["Fluxo verde em CI"]),
 (3, "Upload manual com aprovação (drag-drop + revisão editável)", 3, "done", "DragDropUpload + /revisao com correção",
  ["Arrastar/soltar no detalhe", "Revisão mostra extração e permite corrigir antes de aprovar"],
  ["Upload vira sugestão; aprovação leva à conciliação"]),
 (3, "Webhook Checkto real + cobrança PIX com QR", 3, "done", "POST /webhooks/checkto + /links/cobrar + QR na /v",
  ["Token por cobrança; idempotência por transaction.id; QR na página do vendedor"],
  ["Pagamento via link registra mov + comprovante sem digitação"]),
 (3, "Deduplicação por hash + monitoramento de confiança", 2, "done", "arquivo_hash 422 + detalhe do job",
  ["sha256 no upload; confiança mín no detalhe do job"],
  ["Duplicado recusado; acerto acompanhado (meta 80%)"]),
 (3, "WhatsApp via QR (Baileys, sem Meta)", 5, "done", "wa-gateway + /whatsapp + /caixa-entrada",
  ["QR na tela, sem token Meta; anexos -> caixa; criar mov a partir dela"],
  ["Lojista pareia sozinho; foto vira movimentação conciliável"]),
 # ---- Sprint 4 ----
 (4, "Saldos por fornecedor", 2, "done", "GET /dashboard por_fornecedor + /export/posicao-fornecedores.csv",
  ["Agregação de débitos em aberto"],
  ["Dashboard mostra posição por fornecedor"]),
 (4, "Engine de regras + tolerância configurável", 3, "done", "services.py tolerancia_credito + credito origem=tolerancia",
  ["Parâmetro tolerância por fornecedor; prioridade por dívida", "Nunca gerar crédito acima da tolerância"],
  ["Projeção respeita tolerância; excedente sinalizado"]),
 (4, "Projeção por fornecedor e por rifeiro + simulação", 3, "done", "GET /simulacao + Simulador em projecoes/",
  ["Endpoint de simulação (não persiste): quanto o rifeiro pode pagar sem exceder"],
  ["API retorna projeção atual + simulação sem gerar crédito"]),
 (4, "Testes de regras e projeção", 2, "done", "tests/test_mvp.py",
  ["Parcial, excedente, unicidade, estorno"],
  ["Regras cobertas em CI"]),
 # ---- Sprint 5 ----
 (5, "Setup frontend Next.js", 1, "done", "frontend/ (Next 16, TS, App Router)",
  ["Layout, nav §24, middleware auth, lib/api+actions"],
  ["Build passa; rotas protegidas"]),
 (5, "Login JWT integrado", 2, "done", "app/login + /api/login (cookie httpOnly)",
  ["Redirect pós-login; logout limpa sessão"],
  ["Login navega ao dashboard"]),
 (5, "Dashboard com resumo e alertas", 3, "done", "app/page.tsx (5 cards + por fornecedor)",
  ["Indicadores §12; export posição"],
  ["Responde 'como está minha situação?'"]),
 (5, "Upload e listagem de comprovantes", 3, "done", "movimentacoes/ + [id]/upload",
  ["Filtros, anexo, download"],
  ["Upload na UI cria vínculo no backend"]),
 (5, "Fornecedores e projeção por fornecedor", 3, "done", "pessoas/ + projecoes/",
  ["CRUD pessoas; projeção única exibida"],
  ["Fluxo navegável sem ajuda"]),
 (5, "Estilos base + responsivo desktop-first", 2, "done", "globals.css minimalista",
  ["Poucas opções por tela (§1.1)"],
  ["Registro de PIX em <30s"]),
 # ---- Sprint 6 ----
 (6, "Marcar comprovantes (enviado/registrado)", 2, "done", "etapa recebido/registrado + botão no detalhe",
  ["Status de fluxo no comprovante/movimentação"],
  ["Operador marca e filtra por estágio"]),
 (6, "Trilha who/what/when", 2, "done", "audit_logs + GET /auditoria + tela",
  ["Eventos §26 cobertos"],
  ["Histórico visível por registro"]),
 (6, "UI de revisão e histórico", 3, "done", "detalhe exibe comprovantes + avanço de etapa",
  ["Fila de revisão + histórico de estornos"],
  ["Operador revisa e marca; histórico visível"]),
 (6, "Export CSV", 2, "done", "/export/*.csv + botões (respeitam filtros)",
  ["CSV compatível Excel PT-BR (BOM, ;)"],
  ["Download funciona autenticado"]),
 (6, "Testes integração + e2e UI", 2, "done", "pytest 14 + Playwright fluxo principal",
  ["Playwright: login→PIX→conciliação→export"],
  ["E2E verde em CI"]),
 # ---- Sprint 7 ----
 (7, "Validações e sanitização", 2, "partial", "Pydantic gt=0, enums, upload validado",
  ["Revisar inputs restantes; mensagens claras"],
  ["Erros explicam como corrigir (§25)"]),
 (7, "Rate limiting + segurança", 2, "done", "ratelimit.py login/upload + test",
  ["Throttle login e upload; headers seguros"],
  ["Abuso básico contido"]),
 (7, "Logs estruturados e métricas", 3, "done", "log JSON + GET /metricas (atas)",
  ["Log JSON; métricas: conciliações/dia, tempo médio, % auto vs manual, créditos por erro (atas)"],
  ["Métricas das atas coletadas"]),
 (7, "Teste de carga k6", 3, "done", "tests/carga.js: p95 busca 55ms, dash 75ms, 0 falhas",
  ["Cenário registro+busca+conciliação"],
  ["Metas §21: telas <2s, busca <1s"]),
 (7, "Lint + checklist Clean Code", 2, "partial", "tsc/eslint passam; sem workflow",
  ["Ruff/eslint no CI; complexidade sob controle"],
  ["CI barra código fora do padrão"]),
 # ---- Sprint 8 ----
 (8, "Deploy staging/produção", 2, "pending", "depende do Compose (S0)",
  ["Staging + prod com backup do sqlite"],
  ["MVP acessível p/ piloto"]),
 (8, "Onboarding + guia rápido", 2, "done", "/ajuda 6 passos + checklist PrimeirosPassos",
  ["Guia: registrar PIX, conciliar, exportar; vídeo curto opcional"],
  ["Rifeiro opera sem ajuda (§25)"]),
 (8, "Piloto 1–3 clientes", 3, "pending", "",
  ["Loja + fornecedores; coletar feedback e métricas das atas"],
  ["Fluxo upload→projeção usado; feedback documentado"]),
 (8, "Correção de bugs críticos", 3, "pending", "",
  ["Triagem pós-piloto"],
  ["Zero erros financeiros atribuíveis ao sistema"]),
]

LABELS = {"done": "status:pronto", "partial": "status:parcial", "pending": "status:a-fazer"}


def fname(sprint, title):
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = "".join(c if c.isalnum() else "-" for c in ascii_title.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return f"s{sprint}-{slug[:50]}.md"


def main():
    os.makedirs(ROOT, exist_ok=True)
    index = []
    for sprint, title, pts, status, evid, tasks, aceite in ISSUES:
        name = fname(sprint, title)
        index.append((sprint, title, pts, status, name))
        body = [
            f"# [S{sprint} · {pts}pts] {title}", "",
            f"**Status no MVP atual:** {status}" + (f" — evidência: `{evid}`" if evid else ""), "",
            "## Tarefas",
            *[f"- [ ] {t}" for t in tasks], "",
            "## Critérios de aceitação",
            *[f"- [ ] {a}" for a in aceite], "",
            f"Labels sugeridas: `sprint-{sprint}`, `{LABELS[status]}`, `{pts}pts`",
        ]
        with open(os.path.join(ROOT, name), "w") as f:
            f.write("\n".join(body) + "\n")
    with open(os.path.join(ROOT, "import.sh"), "w") as f:
        f.write(textwrap.dedent("""\
            #!/bin/bash
            # Cria labels e issues no repo atual via gh CLI. Rode na raiz do repo GitHub.
            # Uso: bash docs/issues/import.sh
            set -e
            for s in 0 1 2 3 4 5 6 7 8; do gh label create "sprint-$s" --color 1D76DB 2>/dev/null || true; done
            for st in "status:pronto" "status:parcial" "status:a-fazer"; do gh label create "$st" --color 0E8A16 2>/dev/null || true; done
            for md in docs/issues/s*.md; do
              title=$(head -1 "$md" | sed 's/^# //')
              sprint=$(echo "$md" | grep -o 's[0-9]' | head -1)
              status=$(grep -m1 'Status no MVP' "$md" | grep -o 'done\\|partial\\|pending')
              case "$status" in
                done) lbl="status:pronto";; partial) lbl="status:parcial";; *) lbl="status:a-fazer";;
              esac
              gh issue create --title "$title" --body-file "$md" --label "$sprint,$lbl"
            done
            """))
    os.chmod(os.path.join(ROOT, "import.sh"), 0o755)
    done = sum(1 for i in index if i[3] == "done")
    part = sum(1 for i in index if i[3] == "partial")
    print(f"ISSUES: {len(index)} arquivos ({done} prontos, {part} parciais, "
          f"{len(index)-done-part} a fazer) + import.sh")


if __name__ == "__main__":
    main()
