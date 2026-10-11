# Sprint 15B — isolamento financeiro por loja

Autorizado em 03/10/2026: “pode seguir”, após relatório/proposta da etapa 15A.

## Escopo

Controle central de identidades e vínculos; bancos SQLite financeiros separados para novas lojas, contexto assinado no JWT e revalidação por requisição. Arquivos por loja, extratos e links públicos com contexto explícito, painel com seleção e cadastro inicial do fornecedor por convite. A operação original mantém seu banco/URLs compatíveis. Nenhum novo ambiente herda credenciais globais Checkto/WhatsApp.

## Distribuição

- Root: ambientes/models, database/auth, middleware, provisionamento/seleção, proteção de identidade compartilhada, validação/ensaio em cópia e continuidade.
- Frontend: organizações/seletor/cadastro público/Shell/layout/proxy. Depende: contrato dos endpoints.
- Públicos/arquivos: routers de arquivos/links/extratos e frontend compartilhado/pagamento. Depende: helper upload_root e prefixos públicos.
- Testes/revisão: tests/test_ambientes.py, testes runtime sem override de get_db e revisão readonly. Depende: núcleo implementado.

Arquivos disjuntos por especialista; nenhum commit delegado ou autorizado.

## Aceite

IDs e referências coincidentes nas lojas A/B mantêm notas, pagamentos, saldos, exportações e mutações independentes. JWT inválido, vínculo revogado e organização inativa não liberam dados. Público não procura token em outro banco; anexos não atravessam raízes/symlinks. Identidade central compartilhada não pode ser tomada pelo administrador da loja. Novos bancos não contêm hashes de senha pessoais. Inicialização na cópia preserva registros anteriores e é idempotente. Sem banco operacional, envio, gateway externo, deploy, commit/push ou contorno do bloqueio do navegador.

## Limites desta etapa

Provisionamento SQLite local; PostgreSQL por organização não homologado. Administração interna de novas lojas e portal financeiro limitado de fornecedor exigem etapa específica; nenhum fornecedor recebe acesso amplo para compensar essa pendência. Checkto por organização e gestão/validação bancária dos recebimentos continuam futuras. Interface de cadastro por convite entregue sem mensagens enviadas. Operação original mantém compatibilidade, incluindo perfil global junto do vínculo; novas lojas usam papel do vínculo.
