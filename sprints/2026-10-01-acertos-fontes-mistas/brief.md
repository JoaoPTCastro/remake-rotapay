# Sprint 6 — acertos com fontes mistas

Autorizado pelo usuário em 01/10/2026. Combinar créditos explícitos e pagamentos nos pares de um mesmo acerto, preservando titular/relação, limites, prévia sem reserva, confirmação externa de fornecedor, efetivação atômica, estorno integral e histórico. Nenhum crédito automático, dinheiro novo, transferência entre titulares ou mudança no legado. Sem deploy, commit, push ou migração operacional.

Itens indicam exatamente um pagamento ou crédito. Contrato anterior só pagamento permanece compatível. Aplicações de crédito ligadas ao acerto não admitem estorno isolado. Usar/estornar crédito modifica somente sua disponibilidade e notas; a fonte que originou o reconhecimento mantém valor destinado. Origem/acerto do crédito permanece protegida.

Locks globais: referência, todos acertos incluindo origens ordenados, todos pagamentos incluindo origens ordenados, créditos ordenados, notas ordenadas. Dados modificados após prévia rejeitam lote inteiro, sem redistribuição silenciosa. Recursos elegíveis filtrados no SQL antes de paginação.

Arquivos e dependências: backend app/** define contrato primeiro; frontend frontend/** e testes tests/** usam contrato; root documentação sprints/** e backups ignorados. Revisão posterior somente leitura, correções pelo dono. Nenhum agente faz commit.

Aceite: crédito100 + pagamento200 aplicam60+140 na mesma nota500: nota300, crédito40, pagamento60; fonte original continua indisponível no lado reconhecido. Estorno integral retorna nota500, crédito100, pagamento200; fonte original não muda. Fornecedor exige envio/concordância externos antes da efetivação. Cobrir concorrência, prévia vencida, autorização, idempotência, migração e histórico.

Ao finalizar: relatório das entregas/testes/limites, proposta de próximo sprint e esperar confirmação. Não iniciar próximo automaticamente.
