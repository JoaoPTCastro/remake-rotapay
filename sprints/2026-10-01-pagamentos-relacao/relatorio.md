# Sprint 3 — pagamentos por relação

Entrega local em 01/10/2026. Implementação autorizada pelo usuário após as sprints de cadastros e notas. Dados da demonstração são fictícios.

## O que foi implementado

- Página de pagamentos com filtros, cadastro e consulta do evento real único.
- PIX direto do cliente ao fornecedor: o mesmo valor tem disponibilidade independente nos dois lados; não representa duas entradas de caixa.
- PIX ou dinheiro recebido pela loja: disponibilidade somente para o cliente.
- Repasse posterior ao fornecedor: registro próprio vinculado ao recebimento na loja; soma dos repasses ativos limitada ao valor recebido; não libera novo saldo cliente.
- Aplicação nas notas do mesmo titular e relação, limitada pelo saldo da nota e pela disponibilidade do pagamento. Original, número e prazo da nota são preservados.
- Aplicação no fornecedor exige registrar sua concordância externa e a referência dessa confirmação. O sistema não envia mensagens nem confirma aceite por conta própria.
- Aplicação e abatimento da nota gravados juntos. Estorno registra histórico e reverte ambos, sem alterar o outro lado. Estorno isolado do abatimento vinculado é bloqueado.
- Cancelamento lógico protegido contra aplicações e repasses ativos; senha exata do operador exigida para desfazer.
- Idempotência e travas no banco para impedir excesso de saldo com operadores simultâneos.
- Referência externa original preservada, chave normalizada e bloqueio de duplicidade entre pagamentos novos e registros documentais nos dois sentidos, inclusive concorrência e referências com acentos.
- Anexos privados de até 10 MB, validação de formato, acesso autenticado, download como arquivo e remoção lógica.
- Histórico das notas identifica a origem e permite abrir o pagamento vinculado.
- Seleção de notas abertas/parciais com paginação própria; documentos quitados não escondem notas antigas ainda abertas. Formulários preservam dados e identificação da tentativa após erro.

## Verificação

- Suíte canônica backend: **165 testes aprovados**. Inclui orçamento por relação, titularidade, datas, centavos, perfis, idempotência, estornos, repasses, concorrência e migração incremental.
- ESLint canônico: zero erros e avisos. TypeScript e build de produção aprovados. Lint com tipos: zero erros, 200 avisos preexistentes; arquivos desta sprint sem avisos.
- Revisão de código e segurança concluída sem achados bloqueantes restantes.
- Clone do banco operacional inicializado duas vezes: preservadas integralmente as linhas de **908 movimentações, 18 lançamentos e 274 conciliações**; nenhum estorno existente e nenhum pagamento importado. Evidência: `evidencias/migracao-clone.json`.
- Navegação com dados fictícios: PIX de R$ 300 cadastrado pela interface e aplicado em uma venda de R$ 1.000 e compra de R$ 900; saldos finais R$ 700 e R$ 600. Um único evento de pagamento.
- Upload e download autenticado de PDF sintético de 2.170.606 bytes aprovado pela interface.
- Paginação validada no build final: 101 notas quitadas recentes não ocultaram 56 abertas antigas; a nota mais antiga foi aplicada com sucesso pela segunda página.
- Layout validado em viewport 390 × 1024: largura do conteúdo e da área útil iguais (375 px), sem excesso horizontal no detalhe. Capturas em `evidencias/`.

## Limites e estado da entrega

O banco operacional **não foi migrado**. Nenhuma publicação, deploy, commit, push, envio de mensagem, transferência bancária ou crédito automático foi realizado. Backups locais estão ignorados pelo Git.

PIX e lançamentos antigos continuam no motor atual e não recebem saldo consumível neste módulo. A referência não resolve eventos com identificadores diferentes. O mutex dos novos registros não participa dos endpoints antigos: uma inclusão simultânea pelo motor legado pode escapar da comparação. Por isso, a classificação e transferência do legado continuam pendentes, com travas compartilhadas antes de integrar os motores.

Testes executados em SQLite e Python 3.11 no ambiente isolado disponível; compatibilidade concorrente PostgreSQL foi revisada no código, sem execução contra servidor PostgreSQL nesta entrega. A stack declarada pelo projeto é Python 3.14.

O painel geral, rodízio e relatórios legados continuam lendo o motor antigo; os resultados deste módulo devem ser consultados em Pagamentos e Notas e extratos até a integração explícita dessas visões.

## Próximo passo

Sprint 4: estruturar acertos com várias notas e confirmação acompanhada do fornecedor, seguida do tratamento explícito de saldo residual/crédito e compartilhamento. A migração/classificação dos registros antigos permanece uma etapa própria, necessária antes do piloto com dados operacionais.

Demonstração local: http://localhost:3013/pagamentos/1. Login exclusivo de demonstração: demo@rotapay.local / [credencial demonstrativa omitida do Git]. Banco e uploads em /tmp, sem dados operacionais. Esta demonstração depende dos processos locais e não é publicação.
