# Issues — Sprints 0–8

45 issues geradas de `generate.py` a partir do `Roadmap por sprints.md`,
adaptadas à stack real (FastAPI + SQLite + Next.js) e marcadas contra o MVP atual:
**20 prontas · 9 parciais · 16 a fazer.**

Cada issue tem: título `[Sprint · pontos]`, status + evidência no código,
tarefas e critérios de aceitação.

## Importar no GitHub

```bash
# na raiz do repo GitHub (requer gh autenticado)
bash docs/issues/import.sh
```

Cria labels `sprint-0..8`, `status:*` e uma issue por arquivo via
`gh issue create --title --body-file --label`.

## Regenerar

Edite a lista `ISSUES` em `generate.py` e rode `python3 docs/issues/generate.py`.
