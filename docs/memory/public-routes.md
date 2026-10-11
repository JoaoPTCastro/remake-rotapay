---
name: public-routes
description: Rotas públicas fora do proxy de auth
metadata:
  type: architecture
---
`proxy.ts` exige login em tudo exceto `/api/*`, `/pagar/*`, `/v/*`.
Rota pública nova precisa entrar nessa lista + layout próprio sem menu
(route group `(painel)` isola as telas internas).
