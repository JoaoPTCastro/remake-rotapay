---
name: seed-guard
description: Seeds exigem ALLOW_SEED=true
metadata:
  type: reference
---
`seed_*.py` abortam sem `ALLOW_SEED=true`. `seed-admin` trava com `ENV=prod`.
Seeds limpam demo anterior mas nunca usuários.
