# Sprint 15A — fundação multiempresa e fornecedores

Autorização: “podemos começar”, em 03/10/2026. Etapa local do Sprint 15; isolamento financeiro completo continua pendente para 15B. Sem publicação, commit/push, migração operacional, envio de convites ou chamadas financeiras Checkto.

## Entregas

Organizações com vínculos próprios de usuários. Listagem mostra somente organizações ativas com vínculo ativo. Administração de membros e convites exige papel administrador naquela organização; um administrador da loja B não administra A. Criação de organizações nesta fase é controlada pelo administrador interno da instância original; contratação/autocadastro comercial de novas lojas ainda não foi implementado.

Fornecedor possui identidade compartilhada e vínculo por loja, separados da Pessoa financeira existente. Aceites em duas lojas reutilizam a mesma identidade. Vincular fornecedor não concede papel interno nem acesso financeiro. Membros internos existentes conservam seus papéis ao aceitar um convite; vínculo inativo não é reativado pelo convite.

Convites guardam somente SHA-256 do token aleatório de 32 bytes, expiram em sete dias, podem ser revogados antes do aceite e são consumidos atomicamente. Código aparece somente na resposta da criação, sem URL nem persistência no navegador. Aceite exige conta autenticada com email destinatário. Cadastro inicial por convite está disponível pela API, com email derivado do convite, senha protegida e sem emitir sessão automaticamente; interface pública de cadastro ainda pendente. Não houve envio de mensagens.

Operações concorrentes de aceite/revogação/cadastro são serializadas no SQLite; conflitos retornam 409. PostgreSQL possui bloqueios de linha previstos, mas não foi homologado neste sprint. Token/senha não aparecem nos erros de validação das novas rotas.

Administração antiga de usuários restringe-se aos membros internos da organização original. Identidades de fornecedores compartilhadas não podem ser promovidas nem ter senha redefinida pela loja, inclusive quando vinculadas à organização original. Fornecedor pode alterar sua própria senha.

Auditoria central de organizações e identidades compartilhadas é armazenada separadamente. Eventos de loja B, logins e IPs de fornecedores externos não aparecem na auditoria financeira nem CSV da loja original. Não há tela de consulta da auditoria central nesta etapa; consulta autorizada por organização será definida no próximo trabalho.

Frontend `/organizacoes` e detalhes `/organizacoes/[id]` apresentam vínculos, membros e criação/aceite/revogação de convites. Fornecedor tem navegação restrita e home redireciona para seus vínculos. Telas informam que novas lojas ainda não têm financeiro habilitado. CSS Modules sem Tailwind, mesma stack do MVP.

## Transição e proteção financeira

Seis tabelas aditivas: organizações, membros, identidades/vínculos de fornecedor, convites e auditoria central. Inicialização registra a organização original e fotografa os usuários internos existentes uma única vez. Reiniciar não concede acesso a fornecedores nem reativa vínculos desativados. Administração explícita de usuários internos mantém seu vínculo original.

Endpoints financeiros continuam vinculados à instância original e exigem vínculo interno ativo quando a fundação está inicializada, além do perfil global permitido. Contexto HTTP de outra organização é rejeitado. Não há seletor financeiro de lojas, banco financeiro B nem alegação de isolamento A/B completo. Compatibilidade dos testes/instâncias anteriores sem organizações é mantida; inicialização aditiva habilita as travas.

Ensaio em cópia sintética preservou integralmente os registros e colunas anteriores de 37 tabelas; segunda inicialização foi idempotente. Banco operacional `pix.db` e arquivos reais não foram acessados. Veja [transição](evidencias/transicao.json).

## Validações

**478 testes passaram em 158,94 segundos no Python 3.14.0**, com um aviso preexistente Starlette/httpx. Lint sem erros/avisos, TypeScript aprovado, lint tipado sem erros e com 200 avisos preexistentes. Build Next 16.3.8 aprovado, com 54 páginas geradas. Resultados e logs em `sprint.json` e `evidencias/`. Revisão independente corrigiu os riscos de tomada da identidade compartilhada e vazamento de auditoria; nenhum P1/P2 ficou pendente no escopo 15A.

17 casos novos cobrem autorização A/B, vínculos múltiplos, idempotência, expiração/revogação, destinatário incorreto, cadastro protegido, concorrência real SQLite, bootstrap sem reativação, alterações da própria senha, promoção/reset indevidos e privacidade da auditoria. O orçamento do dashboard separa uma consulta fixa de autorização das oito consultas financeiras permitidas, preservando a verificação de ausência de N+1. Cada cenário novo usa origem HTTP própria, para que rate limiting de cenários anteriores não contamine as verificações; limites da aplicação permanecem ativos.

Ensaio HTTP/HTML demonstra admin e fornecedor, identidade única em duas lojas, financeiro negado para fornecedor/contexto B, ausência de JWT no HTML e tokens ausentes nas listagens. Evidência: [HTTP](evidencias/http.json). Sem verificação visual interativa ou mobile: bloqueio anterior do navegador por política URL/protocolo foi respeitado.

## Próximo trabalho — Sprint 15B

Separar persistência financeira e raízes de arquivos por loja, contexto de autorização e permissões por vínculo, resolução segura dos links públicos, exportações e testes A/B com IDs coincidentes. Proposta técnica: controle central de identidades/vínculos e banco operacional por loja para o MVP, diante das consultas ORM/Core existentes; confirmar o contrato de provisionamento durante o planejamento de 15B. Essa escolha não equivale a migração para Go ou homologação PostgreSQL.

Também completar entrada do fornecedor por convite e preparar seu acesso limitado às relações autorizadas. Gestão de chaves, confirmação de recebimentos e Checkto por organização precisam de implementação própria; não foram habilitadas. Integrações globais antigas não devem ser herdadas automaticamente por novas lojas. Público legado permanece restrito ao banco original nesta etapa.

Antes de iniciar a etapa seguinte, apresentar resultados e obter confirmação conforme protocolo de sprints. Sprint 15 completo permanece aberto enquanto o isolamento financeiro estiver pendente.

## Demonstração local

http://localhost:3025/organizacoes, API 127.0.0.1:8025. SQLite `/tmp/rotapay-multiempresa-base-demo-20261003.db`, uploads `/tmp/rotapay-multiempresa-base-demo-uploads`. Admin sintético `demo@rotapay.local` / `[credencial demonstrativa omitida do Git]`; fornecedor sintético `fornecedor.s15@rotapay.local` / `[credencial demonstrativa omitida do Git]`. Serviços temporários, não publicação. Frontend demonstrativo anterior 3024 encerrado para recompilar sem misturar assets.
