# Sprint 15B — operação financeira isolada por loja

Concluído localmente em 03/10/2026. Autorização: “pode seguir”; confirmação de continuidade durante o fechamento: “pode continuar”. Completa a base multiempresa do Sprint 15, dividida em 15A e 15B. Sem publicação, migração operacional, commit/push, mensagens ou transações externas.

## O que mudou

Identidades e vínculos permanecem no controle central. Novas lojas são provisionadas com banco SQLite vazio e raiz própria de arquivos; caminhos são derivados da configuração privada do servidor e do ID da organização, nunca fornecidos pelo cliente. Preparação é explícita e restrita ao administrador daquele vínculo. Inicialização repetida não duplica o ambiente. Não existe contratação/autocadastro comercial de lojas nesta etapa; a criação inicial continua controlada pelo administrador da instância original.

Seleção da loja renova o token com organização assinada, atualiza o painel e identifica a loja ativa. Vínculo ativo, organização ativa e papel local são conferidos novamente em cada operação. Cabeçalho que tenta selecionar outra loja é recusado; trocar apenas ID do registro não troca o banco. Perfis de administrador/consulta podem diferir entre lojas, sem alterar a identidade global. Administração global antiga de usuários fica bloqueada nos ambientes novos.

O resolvedor suporta o conjunto de consultas existente, inclusive SQL/Core, agregações, CSV, importações e operações financeiras, por meio da sessão do banco correto. Bancos novos guardam referências técnicas dos membros internos para FKs e autoria: nome e papel daquela loja, email sintético e senha vazia. Senhas continuam exclusivamente centrais. Leituras podem atualizar essas referências técnicas; não criam recebimentos, créditos ou abatimentos por esse motivo.

Upload/download de notas, pagamentos, comprovantes, WhatsApp e logos usam raiz da organização. Leituras e gravações rejeitam caminhos de outra loja, escapes e atalhos simbólicos. A raiz original é preservada; uma referência legada também não pode apontar para a subpasta de uma loja nova.

Links de pagamento novos usam `/v/{loja}/{token}`. Extratos usam `/e?loja={id}#token={segredo}`; o segredo permanece no fragmento/header. Backend admite somente aliases públicos de link/extrato, sem transformar um prefixo de loja em acesso geral a endpoints. Um token nunca é procurado nos outros bancos. Vínculo revogado do autor invalida o acesso público daquela loja. Links antigos da organização original mantêm os caminhos compatíveis. Consulta pública de chave por ID numérico fica bloqueada quando há ambiente multiempresa preparado; usar links com segredo.

Checkto global é recusada nos ambientes novos antes de qualquer chamada externa, inclusive tentativa de cobrança automática. Webhooks/WhatsApp antigos continuam restritos à organização original; não há aliases para novas lojas nem herança automática de segredos. Integração bancária por organização continua pendente.

Cadastro inicial de fornecedor ganhou interface `/convite`: código informado no formulário, email derivado do convite, senha protegida, sem segredo em URL e sem sessão emitida automaticamente. Fornecedor existente aceita autenticado. Fornecedor continua sem acesso ao financeiro interno; seu portal por relação será uma etapa específica.

Identidades compartilhadas de fornecedores e também de usuários internos não podem ser alteradas/desativadas ou ter senha redefinida pelo administrador original. A própria pessoa mantém a gestão pessoal de sua senha. Administração de equipe de novas lojas, papéis e desligamento por vínculo precisam de interface/fluxo próprios; não usar a administração global antiga como alternativa.

## O que permaneceu

Stack FastAPI/SQLAlchemy + Next.js/React/TypeScript e CSS sem Tailwind. Regras de notas, pagamentos, abatimentos, acertos e créditos explícitos; nenhum crédito automático. Legado não foi convertido em financeiro novo nem integrado por inferência. Instância original mantém dados, schema aditivo e URLs compatíveis; seu perfil global ainda é conferido junto do vínculo. Migração para Go e PostgreSQL por loja não foi realizada.

## Validações

**496 testes aprovados**, Python 3.14.0, 218,37 segundos, um aviso preexistente Starlette/httpx. São 18 novos casos nesta etapa (11 runtime e sete de públicos/arquivos), além dos 478 anteriores. Lint zero erros/avisos, TypeScript aprovado, lint tipado zero erros e 200 avisos preexistentes. Build Next 16.3.8 aprovado, 55 páginas geradas. Revisão separada sem P1/P2 pendentes no escopo.

Casos reais com o resolvedor de produção, sem override de `get_db`, usam bancos 2/3 e IDs, números de documento, referências e chaves de idempotência iguais. Verificam notas/pagamentos/caixa/CSV/cancelamento independentes, perfis por vínculo, claims/headers inválidos, organização/vínculo revogados, senha central, anexos de bytes distintos, caminhos adulterados, extratos/links públicos confinados, revogação do autor e gateway global nunca chamado em novas lojas. A primeira suíte detectou quebra no formato legado de `/auth/me`; formato antigo foi preservado para dependências sem organização, e a suíte final passou.

Ensaio de inicialização na cópia sintética preservou registros de **43 tabelas anteriores**, acrescentou `ambientes_organizacao` e foi idempotente. Nenhum acesso ao banco operacional. [Transição](evidencias/transicao.json).

Ensaio HTTP/HTML com duas lojas: pessoa/nota/pagamento ID 1 em ambas, notas R$ 100 e R$ 900, entradas R$ 25 e R$ 225; CSV, anexos, público, proxy, home e organizações conferidos. Segredos cruzados retornam 404, contexto conflitante e administração global retornam 403. Sem JWT no HTML, sem senha nos bancos financeiros, sem gateway externo. `/convite` retorna página pública; isso é validação HTTP/HTML, não submissão visual pelo navegador. [HTTP](evidencias/http.json).

## Limites e próximo trabalho

Sem PostgreSQL multiempresa, carga/homologação operacional, verificação visual interativa ou mobile. O bloqueio anterior do navegador por política de URL/protocolo foi respeitado. Cópias/bancos e processos são locais e temporários; não equivalem a implantação. Provisionamento atual é SQLite, com backup/restauração multi-banco ainda a homologar no piloto.

Proposta revisada para Sprint 16: portal do fornecedor, vínculo explícito com seu cadastro financeiro local por loja, consulta limitada, gestão das próprias chaves, declaração/confirmacão de recebimento com evidência e permissões; administração de vínculos/equipe com revogação local e preservação das identidades compartilhadas. Referência `FornecedorVinculo.pessoa_id` da fundação não foi consumida nesta etapa; o vínculo com Pessoa do banco local exige contrato/migração próprios antes do portal. Banco confirmado continua dependente da integração, e confirmação humana não vira confirmação bancária.

OCR e integrações de origem da proposta anterior permanecem no backlog para etapa posterior, com provedor/custo/privacidade definidos. Checkto por organização requer documentação e contrato próprios; sem criar repasse bancário presumido. A próxima etapa só começa após apresentação e confirmação do usuário.

## Demonstração

http://localhost:3026/organizacoes, API 127.0.0.1:8026. Controle sintético `/tmp/rotapay-isolamento-lojas-demo-20261003.db`; bancos por loja `/tmp/rotapay-isolamento-lojas-bancos-20261003/`; arquivos `/tmp/rotapay-isolamento-lojas-uploads-20261003/`. Admin `demo@rotapay.local` / `[credencial demonstrativa omitida do Git]`. Use Organizações → Entrar para alternar entre lojas demonstrativas. Frontend 3025 encerrado para recompilar sem misturar assets; API antiga não foi alterada.
