---
name: frontend-lint
description: Gates do toolkit no frontend, teto 500
metadata:
  type: reference
---
Gates do toolkit em `frontend/eslint.config.mjs`, teto 500 (`quality/max-lines`).
Regras `.cjs` copiadas byte a byte — nunca reescrever. Sem módulo de dados no
front: `no-direct-data-access` removida (documentado). `npm run lint` zerado.
