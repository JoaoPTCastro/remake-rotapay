# Sprint 16 — portal do fornecedor e vínculos por loja

Estado: concluído localmente; validações finais aprovadas. Autorizado em 03/10/2026 por “ok siga”.

## O que foi implementado

A conta central do fornecedor agora pode ser vinculada explicitamente ao cadastro financeiro local de cada loja. A associação não utiliza nem interpreta automaticamente a FK legada `FornecedorVinculo.pessoa_id`. O par organização/cadastro local é único e a associação aceita não pode ser transferida pelo formulário para outro cadastro. IDs iguais entre lojas continuam independentes.

Portal em `/organizacoes/[id]/fornecedor`: notas próprias e seus saldos, recebimentos diretos e repasses destinados ao fornecedor, valores aplicados/disponíveis e declarações de recebimento. Não expõe nomes/dados pessoais dos clientes, pagamentos de outros fornecedores, anexos ou acesso ao financeiro interno. Consultas agregam os abatimentos sem consulta adicional por nota. Disponível significa orçamento registrado para abatimento; não é saldo bancário.

Gestão das chaves próprias por loja: inclusão, alteração, principalidade, ativação e validade temporária. O destino de um link anterior não é substituído silenciosamente. Alterar/desativar a chave pode tornar links existentes indisponíveis; a interface orienta a loja a revisar as cobranças.

Declaração humana de recebimento com autoria central, referência, observação, data, valor e versão do pagamento preservados. Repetição idêntica é idempotente; alteração posterior não reescreve a declaração. Cancelamento/alteração do valor do pagamento sinaliza cancelamento/divergência no histórico e exclui a declaração dos totais válidos. A declaração não muda o pagamento, aplica abatimento, gera crédito ou confirma recebimento bancário. Referência e autoria são evidência declarada; anexos/contestação da declaração não foram acrescentados.

Administração de equipe por loja: adicionar conta interna existente pelo email exato, alterar papel e ativar/desativar vínculo. Não cria conta interna nova, modifica senha, expõe lista global ou transforma fornecedor em funcionário. Revogação afeta somente a relação na loja. Escritas são serializadas, com proteção do último administrador ativo. Na loja original, o perfil interno acompanha o perfil legado da conta; lojas novas mantêm papel independente por vínculo. Identidades compartilhadas e credenciais pessoais permanecem protegidas.

## Verificação

- 23 cenários novos cobrem isolamento, IDs coincidentes, cadastro explícito/único/imutável, FK legada sem autoridade, fornecedor com vínculo interno legítimo, lojas inativas, revogação, perfis, chaves próprias, concorrência, último administrador, loja original, declarações repetidas/divergentes/canceladas, campos forjados e ausência de efeito financeiro. Suíte completa final: **519 testes aprovados (23 novos), 180,30 s, Python 3.14.0**, com um aviso preexistente Starlette/httpx. Lint sem erros/avisos; TypeScript aprovado; lint de tipos sem erros e com 200 avisos preexistentes; build Next16.3.8 aprovado, 55 páginas geradas. Evidências de execução em `evidencias/`. Revisão sem P1/P2 pendentes no escopo.
- Ensaio aditivo em três bancos sintéticos preservou 44 tabelas anteriores por banco. Controle ganhou cadastro/recebimento; bancos locais ganharam somente recebimento. Segunda inicialização idempotente. Checkpoint das fontes finais em `backups-locais/2026-10-03-portal-fornecedor-checkpoint/`, sem dados operacionais. Evidências: `evidencias/transicao.json` e script correspondente.
- HTTP/SSR real em duas lojas: cadastro local #2 e pagamento #2, recebimentos R$120/R$360, notas com saldo R$240/R$720 após declarar. Abatimento parcial e estorno mudaram os saldos e preservaram a declaração. Administração de equipe validada via HTTP: inclusão de conta existente, revogação local sem desativar conta pessoal e último administrador protegido. HTML do portal/admin aprovado, nenhum token JWT no HTML, financeiro interno negado. Evidência: `evidencias/http.json`.
- Revisão corrigiu três problemas concretos: mutex acionava `Pagamento.updated_at`, agora preservado integralmente; vínculo incompatível na loja original podia ser contado como administrador efetivo, agora rejeitado e fora da contagem protetora; versões usadas em abatimento/estorno não invalidam a declaração de recebimento.
- Um primeiro ensaio amplo executado durante a estabilização encontrou uma expectativa incorreta do teste sobre o formato de `/creditos` (lista); o teste foi corrigido e a suíte completa repetida após as últimas alterações. Nenhuma tolerância foi acrescentada para ignorar mutação financeira.

Uma rodada posterior encontrou oito erros de preparação de arquivos temporários quando o Mac ficou sem espaço; 511 testes passaram nessa rodada. Liberado somente cache derivado da compilação do RotaPay (307 MB), sem apagar fontes ou dados. Demo retomada e suíte repetida com pasta temporária própria em `/tmp/rotapay-s16-validacao-final/`. A repetição completa final passou com 519 testes, sem erros. A pasta temporária própria resolveu a preparação dos arquivos; não foram apagados dados do usuário.

## Demo local sintética

Frontend: http://localhost:3027/organizacoes · API: http://127.0.0.1:8027.

Administrador: `demo@rotapay.local` / `[credencial demonstrativa omitida do Git]`.
Fornecedor: `fornecedor.s15@rotapay.local` / `[credencial demonstrativa omitida do Git]`.

O fornecedor possui portal nas lojas #2 e #3. Caminhos: `/organizacoes/2/fornecedor` e `/organizacoes/3/fornecedor`. Na loja original #1, o vínculo demonstra a mensagem de preparação quando ainda não associado. Bancos sintéticos em `/tmp/rotapay-portal-fornecedor-demo-20261003.db` e `/tmp/rotapay-portal-fornecedor-bancos-20261003/`. Demo temporária; dados e caminhos não representam implantação operacional.

## Limites e pendências

Sem banco operacional, mensagens, gateway Checkto, OCR, commit, push, deploy ou publicação. Operação SQLite local; PostgreSQL, carga e homologação real não ensaiados. Bloqueio anterior do navegador por protocolo/URL respeitado, sem contorno: verificação HTTP/SSR não comprova aparência, comportamento visual ou usabilidade no celular.

Associação ao cadastro deliberadamente imutável; correção administrativa de associação equivocada exige fluxo específico antes de operação real. Chaves são por cadastro/loja, sem validação bancária de titularidade ou sincronização global. Políticas configuráveis de visibilidade, consulta externa de créditos/acertos e contestação da declaração seguem no backlog. Conta com identidade de fornecedor e papel interno preservado pode usar a API/URL própria do portal; links de entrada da interface são apresentados ao papel fornecedor. Não atribuir a esta etapa um fluxo completo de onboarding de funcionários novos.

## Próximo sprint proposto

Sprint 17: homologação local e preparação do piloto. Completar matriz ponta a ponta (dois trajetos, abatimento parcial, sobras, crédito explícito, acerto, estorno, revogação e fornecedor), ensaiar backup/restauração e preparar orientações e checklist de aceite. Esclarecer/corrigir os fluxos de associação e declaração necessários ao piloto antes de usar dados reais. Comparação com planilha/ambiente da loja depende do material e autorização correspondentes. Checkto e OCR permanecem trabalhos próprios opcionais; não ativar integração nem publicar por inferência. Aguarda confirmação após fechamento deste sprint.
