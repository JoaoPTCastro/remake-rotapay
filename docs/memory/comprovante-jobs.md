---
name: comprovante-jobs
description: Comprovante é entidade própria com etapa; upload enfileira Job que o OCR consome
metadata:
  type: architecture
---
`Comprovante(movimentacao_id, arquivo+hash, origem, enviado_por, data, etapa)`
caminha recebido→registrado. Upload cria `Job(tipo=comprovante)`; `POST /jobs/processar`
é o worker (stub até o OCR da Sprint C). Tela de detalhe avança a etapa.
