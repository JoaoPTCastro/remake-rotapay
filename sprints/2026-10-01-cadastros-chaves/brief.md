# Implementação — Cadastros e chaves PIX

Autorização: usuário pediu iniciar o planejamento, executar com qualidade e entregar relatório.

Primeira etapa: pessoas unificadas com papéis, contatos e chaves múltiplas, interface operável, migração compatível e validações. Financeiro dos dois lados será etapa posterior; não modificar saldos neste sprint.

## Divisão

- Backend: app/**. Contrato publicado antes de integrar UI; não edita frontend/testes.
- Frontend: frontend/**, respeitando marca e mudanças anteriores. Depende do contrato de backend.
- Testes: tests/**, banco isolado. Depende do contrato; prepara cenários antecipadamente.
- Coordenação: documentos, backup, validação integrada, revisão. Não escreve arquivos de implementadores em paralelo.

Baseline: árvore de trabalho já continha mudanças de marca RotaPay. Backup de fontes e pix.db em backups-locais/2026-10-01-cadastros-chaves, ignorado pelo Git. Não restaurar esse backup por cima de alterações novas sem revisar.

Critérios: cadastro ambos aparece nos fluxos legados; contato/chave principal únicos; validação de temporária; chave expirada/inativa não disponível em página pública; desativação não apaga histórico; usuário consulta não escreve; frontend lint/typecheck/build; suíte financeira continua verde.

Entrega local. Nenhum commit, push, deploy, envio de mensagem ou chamada de cobrança real.
