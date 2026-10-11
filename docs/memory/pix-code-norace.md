---
name: pix-code-norace
description: Código PIX derivado do id pós-flush
metadata:
  type: architecture
---
`count()+1` tinha race e duplicava código (Risco 3 do PRD). Hoje: insere com
`PIX-TMP`, `flush()`, define `f"PIX-{id:06d}"`. Ver `routers/movimentacoes.py`.
