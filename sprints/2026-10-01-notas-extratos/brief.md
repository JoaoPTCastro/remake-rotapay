# Notas e extratos — implementação local

Autorização: usuário pediu seguir com a próxima etapa após a entrega de cadastros. Fonte: plano revisado de 01/10 após os sete áudios e relatório da primeira entrega.

## Escopo e decisões

- Notas de venda na relação cliente e de compra na relação fornecedor, em tabelas próprias. Não converter lançamentos antigos nem inferir sua relação sem evidência.
- Valor original e ID preservados. Saldo calculado por abatimentos documentais ativos, com registro separado de estorno.
- Abatimento externo explícito com referência, observação e idempotência. Não consome PIX, não confirma fornecedor, não gera crédito, não conta como entrada de caixa.
- Prazo do cadastro congelado na criação; alternativas de prazo informado, vencimento explícito ou sem vencimento.
- Anexos privados com autenticação, limite de tamanho e validação de conteúdo. Cancelamento/desativação lógicos e auditoria.
- Extrato limitado às notas cadastradas nesta estrutura, separando relação cliente e fornecedor.

## Arquivos e dependências

| Responsável | Arquivos | Dependência |
|---|---|---|
| Backend especialista | `app/**` | contrato definido |
| Frontend especialista | `frontend/**` | contrato definido; integração aguarda backend |
| Engenharia de testes | `tests/**` | contrato definido; execução aguarda backend |
| Coordenação | esta sprint e backup local | validações finais |
| Revisão | leitura dos arquivos; correções com implementadores | fontes implementadas |

Nenhum implementador faz commit ou deploy. Não editar o banco operacional nem reiniciar seus servidores.

## Aceite

Nota de R$ 1.000 abatida em parcelas mantém ID e valor original; estorno restaura o saldo sem apagar a aplicação. Duplo envio não duplica abatimento e concorrência não excede saldo. Prazo alterado no cadastro não altera vencimento histórico. Sem vencimento fica fora do atraso. Usuário consulta não escreve. Anexos não abrem sem autenticação. Novos registros não modificam totais legados. Suíte completa, lint, tipos, build e navegação demonstrativa aprovados.

Backup antes da edição: `backups-locais/2026-10-01-notas-extratos/`, ignorado pelo Git. Alterações pré-existentes preservadas.

## Fora desta entrega

Catálogos configuráveis de operações/formas/prazos, importação de notas, classificação do histórico antigo, vínculo a pagamentos reais por relação, crédito residual, confirmação do fornecedor e dashboard compartilhado. Esses itens continuam no planejamento; não há integração automática com a planilha ou com o sistema externo da loja.
