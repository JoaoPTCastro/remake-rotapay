# Sprint 4 — acertos e confirmação acompanhada

Autorização: usuário pediu iniciar e concluir Sprint 4 em 01/10/2026.

Escopo: acertos por titular/relação com pagamentos e notas múltiplos; prévia; rascunho, envio externo documentado, confirmação externa, efetivação atômica, histórico, estorno integral e relação local para conferência. Somente módulos novos; nunca migrar ou consumir legado automaticamente. Sobra permanece disponível por pagamento/relação, sem crédito adicional ou reconhecimento automático. Crédito de conta explícito e migração legado são etapas seguintes.

Fornecedor exige enviado e confirmado com evidência externa antes de efetivar. Cliente permite efetivar rascunho após confirmação de operação. Rascunhos não reservam saldo; efetivar revalida todos os recursos. Saldo insuficiente ou nota alterada após prévia deve rejeitar integralmente, sem aplicação parcial silenciosa. Notas originais permanecem iguais. Aplicações de acerto só podem ser estornadas pelo acerto inteiro. Estorno de um lado não muda o outro. Idempotência e concorrência obrigatórias. Nenhum envio, banco real, deploy, commit ou push.

Arquivos: backend app/**; frontend frontend/**; testes tests/**; coordenação sprints/** e backups ignorados. Contrato backend definido primeiro; frontend/testes consomem contrato congelado. Revisão posterior somente leitura. Aceite: múltiplas fontes e notas, falta/sobra explícitas, fornecedor sem confirmação recusado, saldo concorrente bloqueado, estorno integral rastreável e relatório local sem exposição pública.

## Contrato e decisões de implementação

- Rascunho imutável: corrigir por cancelamento lógico e nova proposta. Máximo 100 pares únicos pagamento/nota por lote.
- Prévia vinculada a payload e versões por token HMAC do servidor; cadastro e efetivação rejeitam recursos alterados. Não prometemos reserva ou saldo garantido ao enviar para conferência.
- Locks ordenados: acerto, referências, pagamentos em ID crescente, notas em ID crescente; manter consistência com aplicações unitárias.
- Efetivação com confirmação explícita de operação; senha apenas para cancelamento/estorno.
- Cadastro/efetivação exigem titular ativo; histórico e estorno permanecem acessíveis após inativação.
- Eventos de envio e confirmação registram referências e observações externas. Gerar relação local não equivale a enviar mensagem ou criar portal.
- Totais separados: aplicações propostas, saldos restantes nas notas, sobra por fonte. Nenhuma soma de lados como caixa.
- Recursos elegíveis paginados no servidor após filtro de saldo, sem ocultar antigos por causa de documentos quitados.

## Validação de integração prevista

Cliente: notas R$ 700 + R$ 500, pagamentos R$ 800 + R$ 500. Pares: 700 na primeira, 100+400 na segunda; R$ 1.200 aplicados e R$ 100 disponíveis na segunda fonte. Mesmos IDs e originais das notas.
Fornecedor: pagamentos PIX diretos e notas desse fornecedor; enviado/confirmado externos antes da aplicação. Estorno do acerto fornecedor devolve só esse lado.
Concorrência e proposta obsoleta: operações fora do lote nunca permitem exceder saldo; se proposta mudou, nada é aplicado.
