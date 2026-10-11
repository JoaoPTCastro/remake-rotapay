# Sprint 15A — fundação multiempresa

Autorizado pelo usuário: “podemos começar”, após proposta do Sprint 15.

Diagnóstico: instância atual possui banco, arquivos e regras de autorização globais. Apenas adicionar organização aos usuários não isola as consultas financeiras ORM/Core nem os links públicos.

Divisão explicitada durante execução: 15A entrega controle de organizações, vínculos e convites; 15B separa persistência financeira, anexos, links e integrações. Não habilitar financeiro para novas lojas até aceite A/B. A divisão preserva os requisitos do Sprint 15; não encerra o isolamento completo por inferência.

## Tarefas e arquivos

- Root: integração em auth/database/main/ratelimit, bootstrap original, ensaio em cópia e continuidade. Depende: modelos backend.
- Backend: organizacoes_models/schemas/services/router e testes específicos. Depende: nenhum.
- Frontend: organizacoes página/forms/types/actions e menu Shell. Depende: contrato backend.
- Revisão: leitura de arquitetura e revisão final de acesso/convites. Depende: implementação.

## Aceite desta etapa

Organizações próprias apenas; administração de membros/convites por vínculo ativo; convite expira/revoga/aceita atomicamente e sem token persistido; fornecedor usa identidade compartilhada sem herdar papéis internos; nova loja não acessa financeiro da organização original; transição aditiva em cópia é idempotente e preserva registros financeiros. Sem envio, banco operacional, Checkto, commit/push/deploy.
