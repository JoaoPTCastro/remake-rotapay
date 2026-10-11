# Sprint 12 — Extrato compartilhado com escopo

Autorizado em 02/10/2026: “ta certo, pode seguir para o sprint 12”. Usuário confirmou a conferência manual do Sprint 11 nessa resposta. Escopo confirmado: destinatário é o próprio cliente/fornecedor; valores e situações de notas/pagamentos; validade de 7 dias; sem comprovantes nem dados bancários.

Implementar criação/listagem/revogação admin/financeiro por cadastro/relação; token aleatório forte, somente hash no banco, token mostrado uma vez; consulta pública via bearer em header e token em fragmento do link de frontend; projeção explícita de campos permitidos, paginação limitada e isolamento; no-store/noindex/no-referrer; invalidação por expiração/revogação/conta ou emissor inativo. Nenhum link enviado ou publicado. Dados operacionais e financeira preservados.

Arquivos: backend app/**; frontend frontend/**; testes tests/**; controlador sprints/**. Dependência frontend/testes: contrato do backend. Revisão de segurança somente leitura depois da implementação. Sem commit/push/deploy ou migração operacional.
