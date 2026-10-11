---
name: no-auto-credit
description: Excedente de conciliação nunca gera crédito
metadata:
  type: business-rule
---
Premissa do produto (PRD RF-052): `conciliar()` em `services.py` recusa valor
acima do saldo do alvo; o restante fica em `saldo_disponivel`. Crédito com
fornecedor só via `POST /lancamentos {tipo: credito}` explícito e auditado.
