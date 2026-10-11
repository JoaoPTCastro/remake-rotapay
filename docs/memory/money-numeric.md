---
name: money-numeric
description: Dinheiro em Numeric(12,2) com round(x,2)
metadata:
  type: architecture
---
`Money = Numeric(12, 2, asdecimal=False)` em `models.py`; aritmética sempre com
`round(x, 2)` em `services.py`. `Float` causava erro de centavos.
