# Sprint 17 — homologação local e preparação do piloto

Estado: preparação técnica local concluída. Aceite da loja, comparação com controle real e piloto operacional permanecem pendentes. Autorizado em 03/10/2026 por “ok faça esse”. Não iniciar ativação operacional/publicação por inferência.

## Entregas

Matriz integrada dos dois trajetos, abatimentos parciais, sobra sem crédito automático, crédito explícito, acerto misto, estorno, declaração humana e isolamento/revogação. Quatro novos testes exercitam o resolvedor real das sessões/bancos e combinam etapas já existentes. Evidências de valores em [matriz.json](evidencias/matriz.json).

Ferramenta de backup offline SQLite em [backup_rotapay.py](../../scripts/backup_rotapay.py): controle central, todos os bancos registrados como prontos, uploads e manifesto SHA-256. Verificação de integridade e referências, pacote privado, recusas para arquivos ausentes/adulterados, caminhos indevidos, links simbólicos e destino existente. Criação/restauração exige declaração de operação parada; não detecta automaticamente se escritores foram interrompidos nem oferece backup atômico entre bancos em uso.

Restauração prepara diretório novo e reendereça somente os caminhos de comprovantes/anexos na cópia. O pacote não depende do diretório antigo nem da pasta de trabalho para recuperar referências relativas já normalizadas. Logos e arquivos inativos também são conferidos: arquivo inativo permanece guardado e bloqueado pela API. Vinte e dois testes novos conferem essas proteções, permissões, preservação, origem perdida e recuperação.

[Roteiro operacional](roteiro-operacional.md), [backup/recuperação](recuperacao.md) e [checklist de aceite](aceite-piloto.md) foram entregues, com passos, responsabilidades e pendências do produto que precisam ser resolvidas/aceitas antes de liberar o piloto real.

## Resultado da homologação

**545 testes aprovados (26 novos), 228,84 segundos, Python3.14.0**, com um aviso Starlette/httpx preexistente. Os 26 testes focados passaram em 5,91 segundos. Nenhum P1/P2 pendente na revisão das fontes novas. `git diff --check` aprovado.

Fontes da aplicação/frontend do Sprint16 permaneceram inalteradas, conferidas por SHA-256. Lint, tipos e build daquele sprint não foram repetidos; não anunciados como verificações novas. O mesmo build Next16.3.8 foi aberto com a API recuperada e validado novamente por HTTP/SSR. Não houve mudança de dependências, configuração `.env` ou código financeiro.

Backup/recuperação verificados com **três bancos** e **sete arquivos**, em pacote de dez arquivos mais manifesto. Controle com 46 tabelas e duas lojas com 45 tabelas cada; todas as contagens e registros foram preservados, exceto reendereçamento intencional de `arquivo_path`. Fontes antigas permaneceram intactas. Integridade SQLite e referências conferidas. Evidências em [preparacao-demo.json](evidencias/preparacao-demo.json) e [recuperacao.json](evidencias/recuperacao.json).

A recuperação foi aberta pela aplicação: fornecedor manteve recebimentos de R$120/R$360 e notas de R$240/R$720 nas lojas #2/#3; declarações permaneceram válidas; notas e arquivos não atravessaram lojas. Logo original, três anexos ativos de pagamento e dois anexos de notas foram baixados e comparados byte a byte. O quarto anexo original de pagamento, inativo, permaneceu no pacote e retornou 404. Portais HTTP/SSR e extrato público/proxy confinados conferidos, sem JWT no HTML.

## Revisão e ajustes realizados

Caminhos absolutos do legado tornariam anexos inacessíveis em recuperação para outra pasta. A ferramenta normaliza/reendereça as referências somente nos bancos copiados, preservando dados financeiros. Verificar/restaurar usa o pacote, sem consultar symlinks/arquivos que possam ter substituído a origem após desastre. Logo referenciado ausente também provoca recusa do pacote, evitando recuperação aparentemente completa com arquivo faltante.

As demos anteriores tinham referências a diretórios sintéticos de diferentes sprints. Foram reunidos somente os arquivos desses diretórios conhecidos em uma nova cópia de ensaio, com saldos/contagens e hashes das origens preservados. Não se aplicou essa correção ao banco operacional. O primeiro ensaio HTTP tratava anexo inativo como acessível; foi corrigido para exigir 404 e repetido em nova restauração. A proteção de acesso original foi preservada.

## Como retomar a demo

Frontend: http://localhost:3028/organizacoes · API: http://127.0.0.1:8028.
Administrador: `demo@rotapay.local` / `[credencial demonstrativa omitida do Git]`.
Fornecedor: `fornecedor.s15@rotapay.local` / `[credencial demonstrativa omitida do Git]`.

Ambiente recuperado: `/private/tmp/rotapay-s17-restaurado-final/`. Pacote privado e imutável: `/private/tmp/rotapay-s17-backup/`. Origem sintética: `/private/tmp/rotapay-s17-origem/`. A API escreve auditoria/sincroniza referências técnicas ao usar a demo; não verificar o hash do banco ativo contra o manifesto do backup original depois disso. O pacote permanece separado. Demo3027/API8027 do Sprint16 foi preservada/reiniciada após copiar os dados. Processos e `/tmp` são temporários: conferir ao retomar.

## O que ainda falta

Aceite visual e operacional da loja, comparação com planilha/controle real, responsáveis e rotina de guarda/retenção/recuperação não foram presumidos. PostgreSQL e carga não ensaiados. O bloqueio anterior de acesso ao navegador por URL/protocolo foi respeitado; HTTP/SSR não comprova usabilidade visual/celular.

Antes do piloto real, definir tratamento de associação incorreta, declaração contestada e onboarding de funcionário novo; registrar divergências e aceite no checklist. Associações/declarações atuais permanecem imutáveis; não corrigir por alteração manual do banco nem cancelar dinheiro real para modificar texto. Políticas configuráveis de visibilidade e extensão externa de créditos/acertos seguem no backlog.

Sem banco operacional, gateway Checkto, OCR, envio de mensagens, publicação, deploy, commit ou push. Backup não criptografa, agenda nem transmite dados. Não é homologação de integração bancária nem autorização para ativar a primeira loja.

## Próximo passo proposto

Sprint18: preparar a ativação com ambiente escolhido, dados reconciliados, responsáveis, janela, backup atual e plano de retorno. Começar somente após confirmação do usuário. Migração/publicação exige autorização específica e pré-requisitos de aceite correspondentes; se faltarem, concluir apenas a preparação e registrar a dependência. Checkto/OCR por organização permanecem sprints próprios opcionais, sem promessa de integração nesta ativação manual.
