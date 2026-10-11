# Sprint 8 — intercâmbio, alertas e links

Autorizado pelo usuário em 01/10/2026: “ok, pode seguir”, após proposta de fechamento Sprint7. Usar fullstack-developer do workspace como método; especialistas conforme AGENTS. Nenhum commit/push/deploy ou migração operacional.

## Escopo e responsabilidades

- Backend, app/**: CSV cadastros/notas prévia sem escrita, erros por linha, confirmação de lote válido integral, idempotência persistente, revalidação e concorrência; exportação filtrada e modelos; alertas de dívida/chaves; links privados por pessoa e estados com origem preservada.
- Frontend, frontend/**: interface de intercâmbio e confirmação, downloads seguros, alertas, acesso aos links via cadastro/notas/menu, responsivo PT-BR.
- Testes, tests/**: nova lógica, integração MVP e revisão final somente leitura.
- Coordenação, sprints/**: autorização, relatórios, evidências e continuidade; backups locais antes de editar.

Backend define contrato antes do frontend dependente. Sem colisões de arquivos. Não aplicar etapa de commit do workflow sem autorização do usuário.

## Decisões de implementação

CSV UTF-8 com separador `;` e BOM exportado; dinheiro com duas casas e vírgula. Modelos próprios documentados enquanto loja não fornece formato (pergunta opcional enviada). Importação limitada a cadastros e novas obrigações abertas; não inferir saldos históricos consumíveis, pagamentos, quitação ou créditos. Arquivo inválido bloqueia confirmação integral; prévia não grava. Repetição não duplica; conflito não sobrescreve cadastro nem nota. Cadastros importados exigem identidade por documento; ambiguidades requerem tratamento manual. Token de confirmação vinculado ao usuário, conteúdo e informações relevantes da prévia; alterações exigem nova conferência.

Exportações identificam filtros; prevenir fórmulas de planilha em texto livre. Alertas de chave só informam; não cancelam dívida ou link. Links sem uso permanecem preservados, revogação manual existente; não adotar exclusão/retarget automático. Chave principal nova não altera destino fixado. Estado de uso se limita à evidência interna, não prova pagamento bancário. Vocabulário atual preservado enquanto decisão loja pendente. Nenhum gateway/mensagem externa acionado.

## Aceite

- Prévia sem writes, erro por linha, confirmação explícita, atomicidade e repetição segura.
- Validação igual aos cadastros/notas manuais, bloqueio de dados financeiros legados.
- Exports/formatos/campos/limites legíveis, filtros corretos e sem omissão silenciosa.
- Dívida sem chave válida e validade temporária visíveis; destinos antigos preservados.
- Backend/lint/tipos/build/revisão e navegação sintética cliente/fornecedor; banco real intocado.

Demo planejada: API8018/frontend3018, SQLite `/tmp/rotapay-intercambio-demo-20261001.db`, cópia da demoSprint7. Backup ignorado: `backups-locais/2026-10-01-intercambio-cadastros/`.
