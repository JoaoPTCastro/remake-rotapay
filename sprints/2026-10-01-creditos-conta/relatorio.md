# Sprint 5 — crédito de conta explícito

Entrega local validada em 01/10/2026. Usuário autorizou este sprint; próximo sprint aguarda confirmação. Nenhum deploy, commit, push ou migração do banco operacional.

## Entregas

- Reconhecimento manual da sobra de acerto efetivado, vinculado ao titular, relação e pagamento presente no acerto. Limite considera sobra fotografada, reconhecimentos anteriores não revertidos e disponibilidade corrente da fonte.
- O valor original reconhecido deixa integralmente de estar disponível no pagamento desta relação. Uso do crédito não cria dinheiro, não duplica orçamento e não devolve saldo à fonte.
- Listagem, filtros, detalhe, origem, referência, observação, responsável e histórico. Clientes e fornecedores permanecem separados.
- Aplicação manual em notas elegíveis do mesmo titular/relação; abatimento atômico na nota original e seleção paginada antes de limitar resultados.
- Fornecedor exige concordância externa declarada com referência tanto no reconhecimento quanto no uso. Sem envio de mensagem automático.
- Estorno de uso restaura somente o crédito e reabre a nota. Reversão do reconhecimento exige todos os usos estornados e libera novamente o valor original na fonte.
- Acerto de origem e cancelamento do pagamento bloqueados enquanto houver crédito não revertido, inclusive totalmente utilizado. Abatimento vinculado não pode ser estornado isoladamente pela nota.
- Idempotência, controle de concorrência, validação monetária, permissões e proteção recíproca de referências documentais.
- Integração com pagamentos, acertos e histórico das notas. Repasse e orçamento do outro lado continuam independentes.

## Validação

204 testes backend aprovados em 37,38 s. Incluem 20 casos de créditos e uma integração adicional no MVP: ciclo de aceite, limites, titular/relação, confirmação de fornecedor, repetição idempotente, bloqueios, referências Unicode, concorrência e migração idempotente. Revisão das fontes backend/frontend aprovada sem pendências.

Lint principal: zero erros/avisos. Lint com tipos: zero erros, 200 avisos preexistentes. TypeScript e build de produção aprovados. Execução Python 3.11 em ambiente isolado; projeto declara Python 3.14. Concorrência validada em SQLite; PostgreSQL não foi validado nesta entrega.

Navegação no ambiente sintético isolado confirmou reconhecimento de R$ 100, aplicação de R$ 60, estorno do uso e reversão do reconhecimento. Após uso: nota R$ 440 e crédito R$ 40. Após estorno: nota R$ 500 e crédito R$ 100; após reversão: pagamento cliente R$ 100, crédito indisponível, fornecedor R$ 1.100 preservado. Evidências em `evidencias/credito-parcial.png`, `credito-revertido.png` e `ciclo-browser.json`.

Inicialização repetida em cópia descartável do banco preservou os registros financeiros existentes: 908 movimentações, 18 lançamentos, 274 conciliações e zero estornos. Nenhum crédito automático foi criado. O banco operacional não foi alterado. Evidência: `evidencias/migracao-clone.json`. Uma execução intermediária foi interrompida por falta de espaço; a execução final completa passou.

Demo local: http://localhost:3015/creditos/1. Todos os dados desta demonstração são sintéticos.

## Limites e próximo sprint proposto

Créditos são aplicados manualmente em notas. Não foram incluídos como fontes de acertos em lote neste sprint. Não há transferência entre titulares, expiração presumida nem geração/uso automático. Alterações permanecem locais.

Sprint 6 proposto: permitir créditos e pagamentos como fontes do mesmo acerto em lote, com prévia explícita, confirmação externa do fornecedor, limites agrupados, efetivação atômica, estorno integral e histórico preservado. Criar testes de concorrência e navegar pelos fluxos mistos antes da entrega.

Regra combinada com o usuário: entregar relatório, explicar próximo sprint e aguardar confirmação antes de iniciar. Sprint 6 não iniciado.
