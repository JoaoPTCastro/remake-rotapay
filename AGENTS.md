# RotaPay — Cobranças e conciliação (MVP)

> Fonte única de verdade: o que entrou, de quem veio, para quem vai, qual obrigação quita, quanto falta.

## Continuidade dos sprints

Antes de retomar desenvolvimento, leia [sprints/ESTADO-PROJETO.md](sprints/ESTADO-PROJETO.md) e o relatório do último sprint. Ao finalizar cada sprint ou interromper trabalho incompleto, atualize esse documento com entregas, validações, pendências, estado de autorização e próximo passo. Apresente relatório e escopo do próximo sprint ao usuário; aguarde confirmação antes de iniciá-lo. Não tratar arquivos temporários nem histórico privado de chats como única fonte de continuidade.

## Behavioral guidelines

1. **Think before coding** — explicite suposições. Se houver múltiplas interpretações, apresente-as em vez de escolher calado. Em dúvida real, pare e pergunte.
2. **Simplicity first** — mínimo que resolve. Sem features especulativas, sem abstração de uso único, sem trapaça em gate de lint.
3. **Surgical changes** — toque só o pedido. Sem refatorar código adjacente.
4. **Goal-driven execution** — todo passo com verificação observável (comando, teste). Sem "deveria funcionar".
5. **Sem crédito automático** (regra de negócio central) — excedente de conciliação permanece no PIX; crédito só via lançamento explícito.

## Stack

Python 3.14 · FastAPI + SQLAlchemy (SQLite migrável p/ Postgres via `DATABASE_URL`) · Next.js 16 + React + TypeScript · npm

## Canonical commands

- **Install:** `pip install -r requirements.txt` (raiz) · `npm install` (`frontend/`)
- **Lint:** `npm run lint` (`frontend/`; 0 errors/0 warnings exigidos) · `npm run lint:types` (tier type-aware, fora de hook)
- **Typecheck:** `npx tsc --noEmit` (`frontend/`)
- **Test:** `PYTHONPATH=. python -m pytest tests/ -q` (raiz; banco isolado, nunca toca `pix.db`)
- **Build:** `npm run build` (`frontend/`)
- **Run/Dev:** `uvicorn app.main:app --port 8000` (raiz) · `npm run dev -- --port 3000` (`frontend/`, `API_URL` em `.env.local`)
- **Seed (nunca em prod):** `ALLOW_SEED=true python seed_planilha.py` (base fiel à planilha)

## Specialist agent routing table

| Agent | When to use |
|---|---|
| `backend-specialist` | Endpoints, `services.py` (regras RN), persistência |
| `frontend-specialist` | Telas App Router, server actions, `lib/` |
| `code-reviewer` | Após editar qualquer fonte; achado exige cenário concreto de falha |
| `security-reviewer` | Antes de expor endpoint público ou mexer em auth/upload |
| `test-engineer` | Nova lógica entra com teste em `tests/test_mvp.py` |

Ondas paralelas: ver `docs/rules-parallel-waves.md` — sem dependência e sem arquivo em comum na mesma onda.

## Conventions

- Dinheiro: `Numeric(12,2)` no banco; `round(x, 2)` nos serviços.
- Código PIX derivado do id pós-flush (`PIX-000123`), nunca `count()+1`.
- Exclusão sempre lógica (`/cancelar`, `/revogar`); estorno com registro próprio (RN-008).
- CSV PT-BR: separador `;`, BOM, 2 casas.
- Frontend: server components + actions em `lib/actions.ts`; rotas públicas (`/pagar/*`, `/v/*`) fora do `proxy.ts`.
- Memória do projeto: `docs/memory/` (regras em `INSTRUCTIONS.md`).

## Learn more

Playbook e prompts de referência: https://github.com/soumatheusgomes/vibe-coding-toolkit (Parte 4: brainstorm → plano → ondas → revisão → commit).
