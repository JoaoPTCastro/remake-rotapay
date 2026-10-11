# Sprint 6 — acertos com pagamentos e créditos

Entrega local validada em 01/10/2026. Autorizada pelo usuário após o fechamento do Sprint 5. Nenhum deploy, commit, push ou migração do banco operacional. Próximo sprint aguardando confirmação.

## O que foi feito

- Cada par do acerto utiliza exatamente um pagamento ou crédito de conta, identificado na interface e API. Um mesmo lote combina as fontes, respeitando titular e relação. Também é possível usar apenas créditos.
- Prévia separa saldo anterior, aplicação e sobra de cada fonte; soma os abatimentos por nota para impedir excesso quando várias fontes atingem a mesma obrigação. Prévia e rascunho não reservam saldo.
- Efetivação valida versões e assinatura da prévia antes de aplicar qualquer item. Mudança de saldo rejeita o lote inteiro, sem redistribuição silenciosa.
- Aplicações de pagamento e de crédito, abatimentos nas notas, histórico e efetivação são gravados juntos. O estorno integral devolve os valores às respectivas fontes e reabre as notas na mesma transação.
- Usar crédito não disponibiliza o dinheiro novamente no pagamento que originou seu reconhecimento. Estornar o lote devolve saldo ao crédito, preservando a destinação original do pagamento.
- Uso de crédito ligado ao acerto não pode ser estornado isoladamente no crédito ou na nota. Histórico mostra o acerto responsável; origem do crédito continua protegida.
- Fornecedor conserva o fluxo rascunho → envio externo declarado → concordância externa registrada → efetivado. Não há envio de mensagem ou verificação externa automatizados.
- Seleção e paginação independentes para pagamentos, créditos e notas, com elegibilidade filtrada antes do limite. Seleções e chave de repetição preservadas nas falhas.
- Documento local de conferência mostra pagamentos, créditos reutilizados, origem do reconhecimento e fotografia de saldos separadamente. Crédito não aparece como dinheiro novo ou caixa.
- Reconhecer sobra de um acerto considera somente suas fontes de pagamento; não cria crédito a partir de crédito reutilizado.
- Compatibilidade dos acertos anteriores apenas com pagamentos, incluindo assinatura antiga de valores canônicos. Valores equivalentes como 100 e 100.00 agora recebem representação consistente. Tokens antigos não canônicos que já falhavam antes continuam exigindo nova prévia; não houve atualização silenciosa de tokens persistidos.
- Migração preparada para campos e restrições necessários. Reconstrução SQLite preserva colunas, registros, IDs, índices e triggers dentro de transação/savepoint.

## Testes e revisão

226 testes backend aprovados em 45,14 s: 21 novos cenários de fontes mistas e uma integração MVP adicional. Cobertura inclui acerto misto e somente crédito, fornecedor, estorno integral, limites agrupados, datas/titular/relação, idempotência, prévia desatualizada, compatibilidade HMAC, migração antiga NOT NULL e concorrência sobre crédito/pagamento/nota. Um aviso de depreciação Starlette/httpx.

Revisão de backend e frontend encerrada sem achados P1/P2 pendentes. Lint principal: zero erros e avisos. Lint com tipos: zero erros e 200 avisos preexistentes. Build de produção e TypeScript aprovados. Validação em Python 3.11 isolado, embora o projeto declare 3.14; SQLite temporário. Caminho PostgreSQL revisado no código, sem teste em servidor PostgreSQL.

## Navegação e evidências

- Cliente: seleção pela interface, prévia e criação do lote com R$ 140 de pagamento e R$ 60 de crédito na nota original de R$ 500. Rascunho preserva nota R$ 500, crédito R$ 100 e pagamento R$ 200. Após efetivar: nota R$ 300, crédito R$ 40 e pagamento R$ 60; pagamento original continua R$ 0 disponível no lado reconhecido.
- Histórico do crédito e nota encaminha estorno ao acerto inteiro. Conferência mostra códigos e origens separados.
- Estorno integral pela interface: nota volta a R$ 500, crédito a R$ 100 e pagamento novo a R$ 200; origem do crédito permanece indisponível.
- Fornecedor: lote misto preparado no banco sintético e etapas de envio declarado/concordância/efetivação realizadas pela interface. Após efetivar: nota R$ 300, crédito R$ 40 e pagamento R$ 60 no lado fornecedor; R$ 200 do lado cliente preservados. Nenhuma mensagem ou aceite externos reais.
- Desktop e móvel 390 px conferidos. Largura de conteúdo igual à viewport, sem transbordamento horizontal. Resumo para impressão revisado; nenhuma impressão física ou exportação PDF executada.

Evidências: `previa-mista.png`, `conferencia-mista.png`, `credito-vinculado.png`, `lote-estornado.png`, `fornecedor-efetivado.png`, `lote-mobile.png`, `rascunho-sem-reserva.json`, `lote-efetivado.json`, `lote-estornado.json`, `fornecedor-efetivado.json`.

Migração executada duas vezes em cópia descartável preservou todas as linhas financeiras antigas: 908 movimentações, 18 lançamentos, 274 conciliações e zero estornos. Nenhum crédito automático criado. Outra cópia com acerto, itens e aplicações pré-Sprint 6 preservou os dados anteriores duas vezes. Evidências: `migracao-clone.json`, `migracao-demo.json` e `baseline-migracao-demo.json`. Banco operacional intacto.

Demo local atual: http://localhost:3016/acertos/4. Dados exclusivamente sintéticos; o acerto cliente #2 está estornado e o fornecedor #4 está efetivado para inspeção.

## Próximo sprint proposto — Sprint 7

Extrato individual consolidado por cadastro e relação, reunindo notas abertas/quitadas/atrasadas, pagamentos disponíveis, créditos reconhecidos/usados e acertos com links para origem e histórico. Exibir totais separados e filtros, evitando somar crédito com seu pagamento original ou combinar cliente/fornecedor como caixa. Integrar acesso pelo cadastro e navegação do domínio novo. Proposta de escopo interno e autenticado; compartilhamento público, OCR, integrações externas e publicação continuam fora desta etapa.

Sprint 7 não iniciado. Aguardar confirmação do usuário antes de começar, conforme regra combinada.
