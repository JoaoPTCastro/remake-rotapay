# Sprint 4 — acertos e confirmação acompanhada

Implementação autorizada pelo usuário em 01/10/2026. Entrega local; demonstração usa exclusivamente dados fictícios.

## Entregas

- Acerto por titular e relação com até 100 pares explícitos pagamento/nota/valor. Total máximo do lote R$ 9.999.999.999,99.
- Prévia dos valores agrupados por pagamento e nota: valor a aplicar, saldo da nota após aplicação e sobra em cada fonte. Nenhuma reserva em rascunho.
- Proposta imutável vinculada à prévia por token HMAC, valores e versões. Mudança em qualquer recurso exige nova revisão e novo acerto; não há redistribuição silenciosa.
- Cliente: rascunho → efetivado com confirmação explícita.
- Fornecedor: rascunho → enviado externamente → confirmado externamente → efetivado. Referências e observações das evidências ficam no histórico do operador.
- Efetivação atômica de todas as aplicações e abatimentos. Nota original, identidade e valor original preservados.
- Histórico vinculado entre acerto, aplicações, pagamentos e notas; não permitir estorno isolado de aplicação integrante do lote.
- Estorno integral com senha e motivo, registros próprios e devolução dos saldos apenas naquela relação. Cancelamento lógico das propostas ainda não efetivadas.
- Idempotência no cadastro, transições e estorno; travas transacionais e ordenação dos recursos contra concorrência.
- Lista com filtros/paginação, seleção de recursos com saldo filtrada antes da paginação, formulários com prévia e preservação da tentativa após falha.
- Relação local autenticada para conferência/impressão, com fotografia da proposta, status atual, evidências, notas e links privados dos comprovantes já anexados aos pagamentos.

## Validação backend

**183 testes aprovados** em SQLite temporário, incluindo 17 testes de acertos e uma integração nova no MVP. Casos abrangem múltiplos pagamentos/notas, agrupamento de limites, datas e titulares, HMAC adulterado, prévia desatualizada, conferência externa, idempotência, concorrência, centavos, permissões, estorno integral e migração incremental.

Duas propostas concorrentes sobre o mesmo pagamento não excederam o saldo: uma efetivou, outra foi recusada integralmente. A relação cliente e fornecedor permaneceu independente.

Clone do banco atual inicializado duas vezes: preservadas todas as linhas de 908 movimentações, 18 lançamentos, 274 conciliações e zero estornos. Nenhum pagamento/acerto foi importado. O banco operacional não foi migrado.

## Validação frontend e navegação

- ESLint canônico: zero erros e avisos. TypeScript e build de produção aprovados.
- Lint com tipos: zero erros, 200 avisos preexistentes; arquivos da sprint sem avisos.
- Revisão de código e segurança concluída sem pendências bloqueantes. Corrigida ação de envio indevida no fluxo cliente; cliente tem apenas rascunho/efetivado, fornecedor conserva a sequência de conferência.
- Interface de criação validada: duas notas de R$ 700 e R$ 500, dois pagamentos de R$ 800 e R$ 500, três pares e R$ 1.200 aplicados. R$ 100 permaneceram disponíveis no segundo pagamento.
- Fluxo fornecedor validado pela interface com referências fictícias de envio e confirmação; efetivação e estorno integral concluídos. Após o estorno, notas cliente com saldo zero, notas fornecedor novamente com R$ 700 e R$ 500; saldos cliente dos pagamentos R$ 0/R$ 100 e fornecedor R$ 800/R$ 500.
- Relação local mostra fotografia da proposta e status atual; download autenticado do comprovante fictício com 2.170.606 bytes aprovado. Nenhum documento enviado a terceiros.
- Layout do detalhe verificado em 390 × 1024: área útil e conteúdo com 375 px, sem excesso horizontal externo. Viewport restaurado ao tamanho original.
- Capturas de prévia, acertos, relação e estorno em `evidencias/`. O botão e os estilos de impressão foram implementados/revisados; nenhuma impressão física ou exportação de PDF foi realizada nesta validação.

## Limites preservados

Nenhum envio de mensagem, transferência bancária, portal público, assinatura digital, integração de gateway, crédito automático, migração operacional, commit, push ou deploy nesta entrega.

Envio e confirmação são registros do que o operador declara ter realizado/obtido fora do RotaPay; não verificam automaticamente identidade ou mensagens do fornecedor. O documento local não comprova envio nem cria acesso externo.

Sobra continua disponível no pagamento por relação. Não foi criada uma segunda fonte de crédito. O reconhecimento explícito em crédito de conta e sua reutilização são a próxima etapa, exigindo transferência do saldo de origem para evitar uso duplicado.

Legado permanece no seu motor e nas visões atuais; classificação/migração consumível e integração de dashboard continuam pendentes. O mutex de referências dos registros novos não cobre inclusões simultâneas pelos endpoints legados, e referências diferentes não provam eventos diferentes.

Qualquer mudança na versão de um pagamento pode tornar obsoleta uma proposta, inclusive uso pelo outro lado, upload ou alteração de registro. A resposta exige nova prévia; fornecedor precisa de nova conferência para a nova proposta. Esta proteção é conservadora e não altera o saldo da outra relação.

Python disponível para os testes: 3.11 em ambiente isolado, frente à versão 3.14 declarada no projeto. PostgreSQL revisado no código, sem servidor PostgreSQL usado nesta entrega.

## Próxima etapa

Crédito de conta explícito: reconhecimento da sobra por titular/relação, retirada da disponibilidade da fonte original, reutilização auditada e estorno condicionado às aplicações posteriores. Depois, classificação do legado e piloto comparado ao controle atual.

## Demonstração e arquivos

Demonstração local atual: http://localhost:3014/acertos/1/conferencia. Login exclusivo de teste: demo@rotapay.local / [credencial demonstrativa omitida do Git]. Banco /tmp/rotapay-acertos-demo-20261001.db e uploads /tmp/rotapay-acertos-demo-uploads, apenas dados fictícios. Depende dos processos locais; não é publicação.

Backend: modelos de acerto/item/evento, schemas e router novos, migração incremental de pagamento_aplicacoes.acerto_id, integração de vínculos nas notas/pagamentos e registro de rotas. Frontend: páginas/acções/tipos de acertos, navegação e vínculos de histórico. Testes: test_acertos.py e integração em test_mvp.py. Backup anterior em backups-locais/2026-10-01-acertos-confirmacao, ignorado pelo Git.
