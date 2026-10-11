# Sprint 5 — crédito de conta explícito

Usuário autorizou iniciar o próximo sprint em 01/10/2026. Regra de continuidade: ao finalizar, relatar entregas/testes/limites, propor próximo sprint e aguardar confirmação do usuário antes de iniciar. Autorização deste sprint não autoriza migração operacional, publicação, commit ou push.

## Domínio

Crédito deriva de sobra de acerto efetivado, titular/relação e pagamento presente nos itens. Reconhecimento explícito positivo limitado ao saldo corrente do pagamento e à sobra fotografada do acerto (incluindo reconhecimentos ativos anteriores da mesma origem). Sem crédito automático; nenhum dinheiro novo. Valor reconhecido sai da disponibilidade do pagamento naquele lado, por inteiro, até reversão; aplicações do crédito não devolvem orçamento à fonte. Não mexer no motor legado.

Crédito com original, data, origem/acerto/pagamento, responsável, referência/observação e histórico. Aplicação manual em nota do mesmo titular/relação, respeitando saldos e datas; abatimento atômico na nota original. Fornecedor exige concordância externa declarada e referência tanto no reconhecimento quanto no uso. Nenhum envio automatizado, transferência entre contas, validade presumida ou aplicação automática.

Estornar uso do crédito retorna disponibilidade somente ao crédito, não ao pagamento. Reverter reconhecimento só com todas aplicações previamente estornadas; então devolve valor à disponibilidade da fonte. Bloquear estorno do acerto de origem e cancelamento do pagamento enquanto houver crédito não revertido, inclusive integralmente usado. Histórico nunca apagado. Estorno isolado do abatimento da nota é bloqueado quando vinculado ao crédito.

Idempotência, limites agrupados, Decimal/centavos, CAS e ordem de locks compatível com acertos/pagamentos/notas. Todos cálculos e recursos paginados devem considerar valores destinados ao crédito. Referências documentais guardam duplicidade nos dois sentidos. Permissões admin/financeiro escrita, leitura perfis já usados. Sem mudanças no banco operacional.

Arquivos: backend app/**; frontend frontend/**; testes tests/**; coordenação sprints/** e backups ignorados. Contrato primeiro, depois integração frontend/testes; revisão posterior somente leitura.

## Aceite

PIX R$ 1.100, acerto aplica R$ 1.000: reconhecer R$ 100 -> disponível pagamento cliente R$ 0 e crédito R$ 100. Nota futura R$ 500 recebe R$ 60 -> saldo nota R$ 440, crédito R$ 40, fonte permanece R$ 0. Estornar uso -> crédito R$ 100 e nota R$ 500. Reverter reconhecimento -> crédito indisponível e fonte R$ 100. O lado fornecedor continua independente. Dois operadores nunca consomem a mesma sobra duas vezes.
