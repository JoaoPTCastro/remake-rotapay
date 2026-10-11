---
name: sprint-d
description: Endurecimento instalado: rate limit, métricas, k6, Playwright e armadilhas
metadata:
  type: reference
---
- `ratelimit.py`: login 10/min, upload 30/min por IP (memória; Redis se multi-instância).
- `GET /metricas`: comprovantes/dia, conciliações/dia, auto vs manual, créditos abertos.
- `tests/carga.js`: `API=.. TOKEN=.. k6 run`; p95 busca 55ms, dash 75ms, 0 falhas.
- Playwright em `frontend/e2e/`; spec usa valor único por run (tabela não exibe remetente).
- ARMADILHAS: rodar `pix.db` sempre com caminho absoluto (nunca relativo em outro workdir);
  k6/e2e poluem o banco — limpar `remetente IN ('k6','E2E Playwright')` depois.
