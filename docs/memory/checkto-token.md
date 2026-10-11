---
name: checkto-token
description: Checkto não usa HMAC; webhook valida token por cobrança; cobrança via pix/receive
metadata:
  type: reference
---
`llms.txt`: validação = comparar `body.token` com `webhookToken` da criação
(ou painel). `identifier` = `link-{token}`; idempotência por `transaction.id`;
sempre 2XX. Cobrança: `POST /gateway/pix/receive` (reais, callbackUrl fixa,
`x-public-key/x-secret-key`). Sem `CHECKTO_*` no env, `/cobrar` dá 422 claro.
Migrações SQLite: `create_all` não ALTERa — usar `ALTER TABLE` no `pix.db` vivo.
