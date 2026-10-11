---
name: fusoes
description: Telas fundidas aprovadas pelo time; deploy Render sem domínio
metadata:
  type: architecture
---
Extrato (`components/Extrato.tsx`) serve `/movimentacoes` (com registro) e
`/controle` (só leitura). CadastroTabs (`?aba=`) serve `/cadastro`, `/pessoas`,
`/chaves`. `/triagem` une caixa + revisão; antigas redirecionam. Conciliar usa
selects reais + criação inline (revalida `/conciliacoes`). Deploy: `render.yaml`
+ `docs/deploy-render.md`; `API_URL` manual pós-deploy; wa-gateway fora do
Render free (sessão efêmera) — fica na loja/VPS.
