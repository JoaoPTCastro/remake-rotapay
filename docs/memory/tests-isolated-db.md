---
name: tests-isolated-db
description: Testes usam banco temporário via dependency override
metadata:
  type: reference
---
`tests/test_mvp.py` cria sqlite temporário e `app.dependency_overrides[get_db]`.
`smoke.py` antigo fazia `drop_all` no banco real — nunca repetir.
