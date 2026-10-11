# RotaPay — estado do projeto e retomada dos sprints

Última atualização: 03/10/2026, após Sprint 17: preparação e homologação local concluídas com 545 testes, backup/restauração e orientações entregues. Aceite da loja, comparação real e piloto operacional pendentes. Sprint 18: preparação e homologação técnica na VPS entregues; ativação aguarda pré-requisitos; nenhuma ativação operacional autorizada. Documento principal de continuidade Codex/OpenCode.

## Onde paramos

**Sprints 1–12, 14, 15 e 16 concluídos localmente. Sprint 13: preparação/classificação concluídas, migração financeira pendente. Sprint 17: preparação e homologação local concluídas (545 testes); aceite externo e piloto real pendentes. Sprint 18: homologação técnica na VPS entregue; ativação pendente.** Sem publicação ou migração operacional autorizadas.

O núcleo novo já cobre cadastros, notas originais, pagamentos independentes por relação, acertos, créditos explícitos e lotes com fontes mistas. O planejamento completo do mapa da loja ainda não está concluído. Código permanece no checkout local, com alterações anteriores preservadas e sem commit/push/deploy destas entregas. Banco operacional `pix.db` não foi migrado; demonstrações e testes usaram bases isoladas.

Regra do usuário: ao concluir cada sprint, apresentar o que foi feito, validações/limites e o que será feito no próximo; **aguardar confirmação antes de começar o próximo**. Atualizar este documento no fechamento de cada sprint e antes de interromper trabalho incompleto.

## Atualização de produto — 03/10/2026

Direção aceita: produto multiempresa, ambiente por loja, convites de fornecedores com identidade vinculável a várias lojas, acesso próprio do fornecedor e cliente final por link. [Respostas e áudios analisados](2026-10-03-definicoes-produto/analise-e-direcao.md). Não confundir dados de implantação da primeira loja com regra universal do produto. Respostas posteriores confirmam os dois trajetos (direto e via loja/repasse), pagamento disponível para abatimento sem crédito automático e stack atual no MVP; futuro Go+React+CSS sem Tailwind. Consulta externa de créditos/acertos é extensão futura do Sprint 12. Os testes anteriores ao Sprint 15 não provavam isolamento entre lojas. Sprint 15B agora valida sessão/banco/arquivos e públicos separados com IDs iguais; Sprint 16 entregou portal limitado do fornecedor, cadastro financeiro local explícito e equipe por vínculo. Checkto por organização continua pendente.

## Retomada em poucos passos

1. Ler `../CLAUDE.md`, `../AGENTS.md`, este documento e o relatório do último sprint. Aplicar também as instruções do workspace pai.
2. Conferir `git status --short` no repositório próprio de RotaPay. Não sobrescrever alterações existentes; não versionar o cliente pelo repositório pai.
3. Verificar a autorização mais recente do usuário. Se o próximo sprint ainda não estiver autorizado, apresentar sua proposta e aguardar confirmação.
4. Ler o plano revisado pelos áudios antes de recorrer ao blueprint antigo: ele corrige as regras financeiras do mapa.
5. Antes de editar, criar backup ignorado em `backups-locais/`, definir escopo/arquivos/dependências e usar bancos descartáveis. Não inicializar a API contra `pix.db` por engano.
6. Implementar, revisar e executar os comandos canônicos aplicáveis. Fechar com relatório, evidências e atualização desta página. Não anunciar validações antigas como se tivessem sido repetidas.

Pasta real: `/Users/clickcorp/Desktop/Projetos/00_Trabalho/1. Projetos pessoais/1. Emerge/Emerge -  MAZYOS/clientes/RotaPay`. Identidade própria em `../docs/design-system.md`: azul-petróleo/ciano, PT-BR. Não aplicar identidade da Emerge ao produto.

## Fontes e preparação anteriores aos sprints

- Nome anterior: PIX ATRAVESSADO; nome atual definido pelo usuário: RotaPay. Rebranding e ativos já existentes foram preservados, não contabilizados como entrega dos dez sprints realizados.
- [Mapa da loja e cobertura dos requisitos](2026-09-30-mapa-loja/evidencias/requisitos-mapa.md), [blueprint histórico](2026-09-30-mapa-loja/blueprint.md) e [revisão](2026-09-30-mapa-loja/revisao.md). Fonte original: https://whimsical.com/projeto-programa-pix-6weK7PYQFRv3TzSgG65fiU.
- [Sete áudios: análise e planejamento revisado](2026-10-01-respostas-audio/analise-e-plano-revisado.md). Processamento local por transcrição automática, não revisão auditiva declarada. Originais preservados em Downloads; evidências locais excluídas do Git. O plano revisado prevalece onde corrige o blueprint inicial.
- A preparação foi análise e planejamento; não deve ser confundida com um sprint de implementação ou autorização de publicação.

## Histórico resumido das entregas

| Sprint | Entrega | Resultado principal | Backend aprovado no fechamento | Relatório |
|---|---|---|---|---|
| 1 | Cadastros e chaves | Cliente/fornecedor/ambos; contatos e chaves múltiplos; principalidade/validade; destino fixado dos links | 99 testes | [Relatório 1](2026-10-01-cadastros-chaves/relatorio.md) |
| 2 | Notas e extratos | Venda/compra, vencimento congelado, saldo parcial na nota original, abatimento externo documental e anexos privados | 132 testes | [Relatório 2](2026-10-01-notas-extratos/relatorio.md) |
| 3 | Pagamentos por relação | Um evento real, orçamentos independentes, dinheiro na loja, repasse documentado e aplicação/estorno nas notas | 165 testes | [Relatório 3](2026-10-01-pagamentos-relacao/relatorio.md) |
| 4 | Acertos e confirmação | Vários pagamentos/notas, prévia, lote atômico, confirmação externa do fornecedor e estorno integral | 183 testes | [Relatório 4](2026-10-01-acertos-confirmacao/relatorio.md) |
| 5 | Crédito de conta explícito | Reconhecimento da sobra retira disponibilidade da fonte; uso futuro, estorno do uso e reversão com dependências | 204 testes | [Relatório 5](2026-10-01-creditos-conta/relatorio.md) |
| 6 | Fontes mistas nos acertos | Pagamentos e créditos no mesmo lote; prévia e limites agrupados; estorno integral restitui cada fonte | 226 testes | [Relatório 6](2026-10-01-acertos-fontes-mistas/relatorio.md) |
| 7 | Extrato individual consolidado | Totais globais por relação, cinco listas filtradas, histórico e acesso pelo cadastro | 244 testes | [Relatório 7](2026-10-01-extrato-consolidado/relatorio.md) |
| 8 | Intercâmbio, alertas e links | CSV com prévia/confirmação/idempotência, exportação filtrada, alertas de chaves e destinos históricos | 275 testes | [Relatório 8](2026-10-01-intercambio-cadastros/relatorio.md) |
| 9 | Configurações e tabelas | Catálogos suportados/descritivos, condições e snapshots; preferências por usuário nas três tabelas | 298 testes | [Relatório 9](2026-10-02-configuracoes-tabelas/relatorio.md) |
| 10 | Comprovantes e rastreabilidade | Viewer privado PNG/PDF, zoom/páginas/tela cheia; autor/origem e horários declarados; filtros e ocultação sem efeito financeiro | 323 testes | [Relatório 10](2026-10-02-comprovantes-rastreabilidade/relatorio.md) |
| 11 | Administração, perfil e permissões | Perfil pessoal, empresa/logo privada, gestão de usuários, matriz real e auditoria; correção da concorrência de admins | 358 testes, Python 3.14; visual manual confirmado | [Relatório 11](2026-10-02-administracao-permissoes/relatorio.md) |
| 12 | Extrato compartilhado | Cadastro/relação congelados, 7 dias, consulta restrita, revogação e somente hash persistido | 396 testes, Python 3.14; build e HTTP aprovados | [Relatório 12](2026-10-02-extrato-compartilhado/relatorio.md) |
| 13 | Preparação do legado | Inventário, pendências, prévia e classificação idempotente em cópia; conversão financeira desligada | 433 testes; build/HTTP aprovados | [Relatório 13](2026-10-02-legado-classificacao/relatorio.md) |
| 14 | Visão global e relatórios | Painel novo, contas independentes, fila de notas e CSV; legado separado | 461 testes; frontend e HTTP aprovados | [Relatório 14](2026-10-02-visao-global/relatorio.md) |
| 15A | Fundação multiempresa | Organizações, identidade compartilhada e convites; auditoria central separada | 478 testes; frontend e HTTP aprovados | [Relatório 15A](2026-10-03-multiempresa-base/relatorio.md) |
| 15B | Isolamento por loja | Bancos/arquivos próprios, seleção, públicos confinados e cadastro por convite | 496 testes; frontend e HTTP A/B aprovados | [Relatório 15B](2026-10-03-isolamento-lojas/relatorio.md) |
| 16 | Portal do fornecedor e equipe | Cadastro local explícito, notas/saldos/recebimentos/chaves próprios, declaração humana, revogação e último administrador | 519 testes; frontend e HTTP A/B aprovados | [Relatório 16](2026-10-03-portal-fornecedor/relatorio.md) |
| 17 | Homologação local e recuperação | Fluxos combinados, backup/restauração de três bancos/sete arquivos, roteiro e checklist | 545 testes; HTTP/SSR recuperado aprovado; aceite externo pendente | [Relatório 17](2026-10-03-homologacao-piloto/relatorio.md) |

Os números são o total da suíte em cada fechamento, não quantidades para somar. Todas as entregas foram locais. Evidências, brief e registros estruturados ficam na pasta de cada sprint; os últimos incluem `sprint.json`. Relatórios históricos não são reescritos: pendências superadas são reconciliadas nesta página.

### Sprint 1 — cadastros e chaves

Concluído: criação/edição/desativação, papéis compatíveis com legado, contatos múltiplos e principal único, chaves múltiplas com validade e principalidade, permissões no backend, preservação de vínculos e migração idempotente. Links guardam a chave/destino conhecido; mudar a chave principal não redireciona um link anterior. Link sem destino conhecido permanece bloqueado.

Superado no Sprint 8: importação de cadastros com prévia, exportação e alertas de chaves. Ainda falta: eventual adaptação ao arquivo da loja e vocabulário definitivo cliente/intermediador/representante.

### Sprint 2 — notas e extratos

Concluído: notas por titular/relação, documento único, original preservado, quatro modos de vencimento, abatimentos e estornos sem renumerar a obrigação, extrato de notas, filtros/paginação e anexos privados até 10 MB. Abatimento externo documenta um fato fora do sistema; não confirma PIX, caixa ou fornecedor.

Superado depois: ligação com pagamentos, acertos e créditos foi entregue nos Sprints 3–6. Ainda falta: catálogos configuráveis e importação/classificação das obrigações antigas. O extrato individual consolidado do domínio novo foi entregue no Sprint 7.

### Sprint 3 — pagamentos por relação

Concluído: PIX direto cliente→fornecedor com disponibilidade legítima em ambos os lados; PIX/dinheiro na loja somente no cliente; repasse próprio vinculado à entrada; aplicações limitadas por fonte e nota; confirmação externa de fornecedor; cancelamento lógico; estorno com senha/motivo; comprovantes privados; idempotência e concorrência. Referências normalizadas protegem duplicidade entre os fluxos novos e registros documentais.

Ainda falta: classificar e integrar o legado; motor antigo não participa integralmente das novas travas de referências. Referências diferentes não provam que eventos reais são diferentes. Dashboard global/rodízio/relatórios antigos continuam lendo o motor legado.

### Sprint 4 — acertos e confirmação

Concluído: até 100 pares explícitos, prévia HMAC sem reserva, rascunho imutável, efetivação e estorno do lote inteiro, histórico e relação local autenticada para conferência/impressão. Cliente tem rascunho→efetivado; fornecedor exige envio e concordância externos declarados antes de efetivar. A versão alterada exige nova proposta; não há redistribuição silenciosa.

Superado depois: crédito de sobra e fontes mistas foram entregues nos Sprints 5–6. Ainda falta: compartilhamento externo com escopo aprovado; a relação local não foi enviada automaticamente nem constitui portal público/assinatura.

### Sprint 5 — crédito explícito

Concluído: reconhecer sobra de acerto efetivado por titular/relação e pagamento; limite pela sobra fotografada e orçamento corrente. Valor reconhecido sai integralmente da fonte até reversão, mesmo se o crédito for totalmente utilizado. Uso em nota futura modifica crédito e nota; estorno do uso devolve apenas ao crédito. Reversão exige todos os usos estornados. Origem protegida; fornecedor confirma reconhecimento e uso. Histórico preservado.

Superado depois: crédito como fonte de acerto em lote entregue no Sprint 6. Ainda falta/fora do escopo: automatismo, expiração e transferência entre titulares — não presumir essas regras.

### Sprint 6 — pagamentos e créditos no lote

Concluído: um item escolhe exatamente uma fonte; lote misto ou apenas créditos. Prévia e limites agregados por nota/fonte, confirmação de fornecedor, efetivação/estorno integrais, guard contra estorno isolado, paginação elegível, snapshots de origem dos créditos e compatibilidade de acertos antigos. Usar crédito não reabre orçamento no pagamento original. Sobra de fonte crédito não vira outro crédito automaticamente.

Aceite navegado: crédito R$ 100 + pagamento R$ 200 abatem R$ 60 + R$ 140 na nota R$ 500 → nota R$ 300, crédito R$ 40 e pagamento R$ 60. Estorno integral → nota R$ 500, crédito R$ 100 e pagamento R$ 200; fonte original segue indisponível. Fornecedor também validado pela interface, preservando o lado cliente.

Última validação: 226 testes em 45,14 s; lint principal sem erros/avisos; lint tipado sem erros e 200 avisos preexistentes; TypeScript e build aprovados; revisão sem P1/P2 pendentes. SQLite temporário/Python 3.11; projeto declara 3.14. PostgreSQL revisado, sem execução real. Migração repetida em cópias preservou registros antigos e acertos anteriores. Banco operacional não migrado.

### Sprint 7 — extrato individual consolidado

Concluído: totais globais separados por titular/relação, cinco listas filtradas e paginadas no SQL, histórico com origens e estornos, leitura nos quatro perfis, cache privado e acesso pelo menu/cadastro/notas. Totais em um único statement; filtros não alteram os indicadores globais. Disponibilidade não é caixa nem abatimento automático. Timeline usa calendário São Paulo/UTC; aplicações não se repetem como dinheiro nos eventos dos lotes.

Aceite: cliente500 em aberto com pagamentos200/créditos100; fornecedor300 em aberto com pagamentos60/créditos40. Relações opostas vazias. Filtro Quitado e período vazio preservaram totais. Origem e ficha navegadas, mobile/desktop conferidos. 19 tabelas financeiras da demo idênticas antes/depois.

Última validação: **244 testes em41,42s**, lint principal zero erros/avisos, tipado zero erros/200 avisos preexistentes, TypeScript/build aprovados; revisão sem P1/P2 pendentes. SQLite/Python3.11; PostgreSQL/3.14 não executados. Sem migração operacional/publicação. [Relatório7](2026-10-01-extrato-consolidado/relatorio.md).

### Sprint 8 — intercâmbio, alertas e links

Concluído: importação CSV de cadastros e novas notas abertas com prévia sem escrita, erro por linha, confirmação integral HMAC15min e recibo persistente/idempotente. Mutex compartilhado com cadastro manual; documento normalizado obrigatório para importação, ambiguidades preservadas e sem sobrescrita. Exportações filtradas BOM/`;`/duas casas monetárias, limite10mil explícito e proteção contra fórmulas. Alertas de dívida de fornecedor sem chave disponível, temporária expirada/avencer30dias. Consulta privada paginada dos links por titular/status com destino fixado; acesso em cadastro e pagamentos sem presumir vínculo financeiro.

Aceite navegado: arquivo inválido bloqueado; dois cadastros e duas notas criados; repetição devolveu recibo sem duplicação. Vencimentos08/10 e15/10; exportação filtrada com500,00; alertas e link com chave original após troca da principal. Registros anteriores de23tabelas idênticos. Mobile/desktop conferidos.

Última validação: **275 testes em50,89s**, lint principal zero erros/avisos, tipado zero erros/200avisos preexistentes, TypeScript/build aprovados, revisão sem P1/P2 pendentes. SQLite/Python3.11; PostgreSQL/3.14 não executados. Fechamento documental02/10/2026. [Relatório8](2026-10-01-intercambio-cadastros/relatorio.md).

Ainda falta: formato específico da loja, vocabulário definitivo e política adicional de links nunca usados. Pagamentos apenas modelo CSV; importação financeira histórica fica no Sprint13. Sem migração operacional/publicação.

### Sprint 9 — configurações e preferências de tabelas

Concluído em 02/10/2026: catálogos de formas PIX/dinheiro, operações apenas descritivas e condições de prazo. Criar/renomear/ativar/desativar, sem exclusão física; significado/prazo fixos. Seleções opcionais em novas notas/pagamentos congelam IDs/nomes e prazo. Preferências no banco por usuário/tela (cadastros, notas, pagamentos): colunas, ordem, ordenação, filtros e reset. Notas/pagamentos ordenados antes da paginação; cadastros ordenam lista completa. Aba explícita prevalece sobre tipo salvo sem sobrescrevê-lo.

Aceite: nota21dias e pagamento preservados após editar/desativar catálogo; nota criada pela interface com14dias venceu16/10/2026. Colunas persistiram após recarga e reset restaurou controles. Desktop e mobile sem overflow indevido. Migração executada duas vezes na cópia; registros anteriores das32tabelas preservados antes/depois.

Validação: **298 testes em65,03s**, lint principal0erros/0avisos; tipado0erros/200avisos preexistentes; TypeScript/build aprovados e repetidos após ajustes; revisão independente semP1/P2 pendentes. SQLite/Python3.11; PostgreSQL/3.14 não executados. [Relatório9](2026-10-02-configuracoes-tabelas/relatorio.md). Sem migração operacional/publicação.

Pendente externo: definição da loja para classificação compra/devolução e Entrada/Saída versus Crédito/Débito. Nenhum efeito novo foi presumido. Demo temporária http://localhost:3019/configuracoes, API8019 e banco sintético em /tmp; login demo@rotapay.local / [credencial demonstrativa omitida do Git]. Verificar processos ao retomar.

### Sprint 10 — comprovantes e rastreabilidade

Concluído em 02/10/2026: visualizador privado de imagens e PDF com zoom, páginas e expansão da janela; download original; fechamento por Escape e restauração de foco. PDF.js 6.3.289 com worker local e renderização limitada em canvas, sem execução de ações, formulários ou scripts do PDF. Acesso exige autenticação e valida assinatura, MIME e raiz do arquivo, com cache privado.

Pagamentos novos recebem origem Manual pelo servidor; antigos permanecem Não informada, sem preenchimento retroativo. Autor real e horários UTC explícitos; horário da transação opcional com fuso, coerência com a data em São Paulo e rejeição de horário futuro. Participantes opcionais são dados declarados. Filtros de valor e origem são aplicados antes da paginação e podem ser salvos nas preferências. Atualizar consulta e ocultação de anexo preservam os valores financeiros.

Aceite: PNG com zoom de 125%; PDF de duas páginas renderizado, com zoom de 125%; expansão da janela em desktop (1280×1000) e celular (390×1024); Escape retorna o foco. Pagamento #5 de R$ 20 em dinheiro criado pela interface, com horário 09:00-03 convertido para 12:00 UTC. Filtro Manual de R$ 25 a R$ 25 retorna somente #4. Proxy sem autenticação retorna 401, modo inválido 400 e anexo ocultado 404; download mantém os bytes originais. Migração de cinco colunas repetida duas vezes na cópia, preservando registros anteriores de 34 tabelas.

Validação: **323 testes em 76,35 s**; lint sem erros ou avisos; lint tipado sem erros e com 200 avisos preexistentes; TypeScript e build Next 16.3.8 aprovados; revisão final sem P1/P2 pendentes. Atualização Next 16.3.4 → 16.3.8; auditoria de produção sem vulnerabilidades reportadas. Auditoria completa ainda indica brace-expansion preexistente em dependência de desenvolvimento. Worker minificado excluído do lint somente em public/pdfjs/**, com versão e correspondência de conteúdo verificadas. SQLite/Python 3.11 validados; PostgreSQL/Python 3.14 não executados. [Relatório 10](2026-10-02-comprovantes-rastreabilidade/relatorio.md).

Pendente externo: política de gateway, correção e contestação; definição final dos papéis dos participantes. Demo temporária em http://localhost:3020/pagamentos/4, API 8020 e banco/uploads sintéticos em /tmp; login demo@rotapay.local / [credencial demonstrativa omitida do Git]. Sem migração operacional ou publicação.

## Regras financeiras que não podem se perder

1. Um PIX direto pode abater duas relações independentes; não equivale a duas entradas de caixa da loja. Limite de consumo vale por relação.
2. Pagamento parcial mantém ID, número e valor original da nota; apenas saldo e histórico mudam. Não criar nova nota remanescente por falta.
3. Sem crédito automático. Reconhecimento explícito substitui disponibilidade da fonte; nunca disponibilizar crédito e o mesmo saldo original simultaneamente.
4. Estorno de uso devolve ao crédito. Só reversão do reconhecimento libera a fonte, após desfazer todos os usos.
5. Estorno de aplicação de acerto é integral no lote; documentos vinculados não podem ser desfeitos isoladamente.
6. Confirmação externa é declaração com evidência do operador, não identidade verificada ou mensagem enviada pelo sistema.
7. Dinheiro na loja não cria orçamento de fornecedor até repasse/pagamento próprio documentado.
8. Legado não recebe saldos consumíveis nem segundo lado concluído por inferência. Preservar IDs/histórico; migração requer evidência e comparação.
9. Pagamentos/créditos de cliente e fornecedor não devem ser somados como caixa/receita. Obrigações e projeções também não são dívidas duplicadas.
10. Não relaxar regras financeiras para fazer testes passarem; concorrência e falha devem deixar o lote inteiro sem consumo parcial.

## Backlog atual reconciliado

### Última entrega — Sprint17 local concluído; aceite/piloto real pendentes; Sprint18 aguarda confirmação

O usuário encerrou o Sprint 11 ao responder “ta certo, pode seguir para o sprint 12”. A conferência visual foi confirmada manualmente pelo usuário; o bloqueio do navegador não foi contornado e não se presume screenshot automatizado.

Escopo do Sprint 12 confirmado: link para o próprio cliente/fornecedor, valores e situações das notas/pagamentos, validade de 7 dias, sem acesso a comprovantes ou dados bancários. Entregues somente leitura, isolamento por cadastro/relação, token seguro, validade/revogação e administração por admin/financeiro. Token em fragmento do link e header no backend, somente hash persistido; nenhum envio ou publicação. [Brief 12](2026-10-02-extrato-compartilhado/brief.md). [Relatório 12](2026-10-02-extrato-compartilhado/relatorio.md): 396 testes, build e HTTP aprovados; sem conferência visual interativa. Sprint 13 entregou inventário/classificação e ensaio de classificação em cópia. [Relatório 13](2026-10-02-legado-classificacao/relatorio.md): 433 testes, frontend e HTTP aprovados. A migração financeira, os dados reais e a trava comum continuam pendentes; consumo integrado desligado.

## Sequência proposta dos próximos sprints

Planejamento organizado a partir do backlog do mapa e das correções dos áudios. **Sprints 1–12 e 14 executados e validados localmente; preparação do 13 concluída e migração financeira pendente, com limites nos relatórios. Sprint 15 foi autorizado e dividido; 15A e 15B entregues localmente. Sprint 16 entregue localmente. Sprint17 foi autorizado e sua preparação local foi concluída; aceite externo/piloto real pendentes. Sprint18 é proposta sem data de entrega.** Cada escopo deve ser revisado e confirmado antes de começar; pode ser dividido caso a complexidade exija. Decisões pendentes impedem apenas a parte que depende delas. Fundação/isolamento 15A/15B e portal/equipe 16 foram implementados; aceite externo/ativação continuam pendentes.

| Sprint | Objetivo | Dependências principais | Estado |
|---|---|---|---|
| 9 | Catálogos financeiros e tabelas personalizadas | Regras de operações; telas existentes | Concluído localmente; novos efeitos dependem da loja |
| 10 | Comprovantes e rastreabilidade dos pagamentos | Pagamentos novos; política por origem | Concluído localmente; políticas da loja pendentes |
| 11 | Perfil, empresa, usuários e permissões por ação | Permissões vigentes preservadas; matriz personalizada depende da loja | Concluído localmente; visual manual confirmado |
| 12 | Compartilhamento seguro do extrato | Sprints 7 e 11; escopo confirmado pelo usuário | Concluído localmente; visual interativa não realizada |
| 13 | Classificação do legado e ensaio de migração | Formatos/importação; evidências da loja | Preparação concluída; migração financeira condicionada |
| 14 | Painel global e relatórios consolidados | Sprint 7; classificação do Sprint 13 | Concluído localmente: módulos novos, legado separado |
| 15 (15A + 15B) | Base multiempresa, convites e isolamento financeiro | Direção de produto confirmada em 03/10 | Concluído localmente; portal limitado entregue no Sprint 16 |
| 16 | Portal fornecedor e gestão de vínculos | Base Sprint 15; vínculo com cadastro local | Concluído localmente com 519 testes; OCR/integrações preservados no backlog |
| 17 | Homologação técnica e piloto acompanhado | Núcleo integrado; dados reconciliados | Preparação local concluída com 545 testes; aceite externo/piloto real pendentes |
| 18 | Ativação operacional e publicação | Piloto aprovado e plano de recuperação | Exige autorização específica |

### Sprint 9 — configurações financeiras e preferências de tabelas

**Objetivo:** completar configurações operacionais e personalização sem alterar documentos históricos.

- [x] Catálogos de formas, operações e condições de prazo, com ativação/desativação e proteção dos vínculos.
- [ ] Definir com a loja classificação de compra/devolução e Entrada/Saída versus Crédito/Débito antes de implementar efeitos financeiros novos.
- [x] Congelar descrição/prazo relevantes nos documentos; editar catálogo não muda nota antiga.
- [x] Mostrar/ocultar/reordenar colunas, ordenar, limpar filtros e salvar preferências por usuário/tela.

**Aceite:** documento antigo mantém suas condições; item de catálogo usado não é apagado; preferência de um usuário não altera a de outro. **Fora:** crédito automático, transferências ou regras de devolução presumidas.

Implementação e validações encerradas em 02/10/2026; ver [Relatório 9](2026-10-02-configuracoes-tabelas/relatorio.md). A decisão da loja permanece pendente e não impede o fechamento do escopo seguro entregue.

### Sprint 10 — documentos e proveniência dos pagamentos

**Objetivo:** melhorar conferência e identificar claramente quem registrou e qual foi a origem de cada pagamento.

- [x] Visualização de comprovantes com painel/modal, zoom e tela cheia, preservando downloads privados e validações existentes.
- [x] Distinguir data de lançamento de data/hora da transação quando conhecida; não inventar horários antigos.
- [ ] Revisar campos de autor, operador, remetente, favorecido e intermediador com a loja.
- [x] Filtros de valor/origem, atualização e indicadores por relação sem dupla contagem.
- [ ] Definir e implementar travas por origem; ocultação de documento não pode cancelar efeito financeiro silenciosamente.

**Aceite:** API aplica as mesmas restrições da interface; ocultação preserva histórico/saldo; comprovante não confirma pagamento automaticamente. **Decisões:** política de gateway, correções e contestação. OCR real continua no backlog específico, após a repriorização do portal fornecedor.

Escopo seguro entregue e validado em02/10/2026. Autor real e campos opcionais declarados implementados; definições da loja para papéis e política gateway permanecem pendentes. Origem dos novos registros é fixada pelo servidor, sem permitir edição de gateway. Ocultar anexo é lógico e não cancela pagamento. [Relatório10](2026-10-02-comprovantes-rastreabilidade/relatorio.md).

### Sprint 11 — administração, perfil e permissões

**Objetivo:** organizar acesso por ação e completar Minha Conta/Empresa. Concluído localmente; conferência visual manual confirmada pelo usuário.

- [x] Inventário/matriz derivados dos controles reais do backend; quatro perfis preservados. A matriz personalizada aprovada pela loja continua pendente.
- [x] Perfil pessoal com nome/email e confirmação de senha para alterar email; gestão administrativa não contorna os fluxos pessoais de email/senha.
- [x] Empresa com dados validados e logo raster privada; identidade da loja separada da marca RotaPay.
- [x] Usuários com nome/email, busca ID/nome/email, filtro por perfil, status e motivo opcional; correção da concorrência na proteção do último admin ativo.
- [x] Auditoria legível de usuários/empresa com autor, horários e antes/depois permitidos; detalhes administrativos somente para admin; segredos ausentes nas exportações.
- [x] Conferência visual manual confirmada pelo usuário ao autorizar o Sprint 12; conferência automatizada final foi bloqueada e não foi repetida.
- [ ] Aprovação da loja para permissões personalizadas e necessidade/acesso de contato, CPF, nascimento e foto. Esses campos adicionais não foram coletados.
- [ ] Canal e política de convites; nenhum convite enviado.
- [ ] Ensaio PostgreSQL e definição de retenção/expurgo dos logos anteriores privados.

**Aceite técnico obtido:** perfil pessoal não eleva acesso; consulta não escreve operações financeiras nem empresa; alterações de acesso ficam auditadas; último admin preservado em duas requisições concorrentes SQLite; dados secretos não vazam na auditoria/exportações. **358 testes / Python 3.14.0**, lint/TypeScript/build aprovados. [Relatório 11](2026-10-02-administracao-permissoes/relatorio.md). Fechamento local confirmado pelo usuário.

### Sprint 12 — extrato compartilhado com escopo

**Objetivo:** disponibilizar consulta externa limitada ao cadastro autorizado.

- [x] Escopo confirmado: próprio cliente/fornecedor, valores/situações das notas e pagamentos, validade de 7 dias, sem anexos ou dados bancários. Relação selecionada e congelada ao gerar link.
- [x] Acesso somente leitura, token seguro e isolamento entre titulares.
- [x] Permitir revogar/expirar acesso sem remover histórico financeiro.
- [x] Testes de acesso indevido por troca de IDs e proteção dos arquivos.

**Aceite:** acesso do cadastro A nunca permite consultar B; token revogado/expirado não revela dados; anexos respeitam o escopo. **Dependência:** Sprints 7/11 e política da loja. Publicar ou transmitir o acesso depende de autorização específica; implementação local não equivale a envio.

### Sprint 13 — legado, classificação e ensaio de migração

**Objetivo:** preparar coexistência ou transição com rastreabilidade e saldos reconciliados.

- [x] Inventário privado das seis fontes registradas, com vínculos e divergências; não cobre dados externos não fornecidos.
- [x] Prévia e confirmação auditável/idempotente de classificação por evidência, sem inferir quitação; desconhecidos/inconsistentes ficam pendentes.
- [x] Recibos imutáveis com origem/snapshot; repetição e concorrência sem duplicidade; alerta de origem alterada.
- [x] Ensaio **de classificação** em cópia sintética, com preservação de IDs/vínculos e dados financeiros.
- [ ] Inventário completo e importação dos abatimentos externos reais: aguarda arquivo/layout autorizado da loja.
- [ ] Mapeamento de transição e comparação financeira por pessoa/relação: aguarda decisão coexistir/substituir e evidências reais.
- [ ] Compartilhar travas de consumo entre motores antes da integração; unicidade da classificação não substitui essa trava.
- [ ] Ensaiar **migração financeira** idempotente em cópia, sem gerar crédito automático; consumo integrado permanece desligado.

**Aceite da preparação obtido:** 433 testes, lint/tipos/build/HTTP aprovados; repetição não duplica classificação; dados financeiros preservados. **Aceite financeiro ainda pendente:** comparação por pessoa/relação, proveniência comum e travas de consumo. Conciliação antiga não vira dois abatimentos por inferência; pendências ficam visíveis. **Decisões:** substituir ou coexistir com o sistema de notas; dados reais autorizados para análise. Migração operacional fica fora deste ensaio.

### Sprint 14 — visão global, rodízio e relatórios

**Objetivo:** fazer as visões gerais refletirem o domínio consolidado com perspectiva explícita.

- [x] Integrar dashboard global, posição por titular e relatórios às notas/pagamentos/créditos/acertos.
- [x] Separar contas de cliente e fornecedor e distinguir fluxo de caixa de pagamento direto.
- [x] Fila documental de notas abertas, sem somar projeções/legado ou programar pagamentos.
- [ ] Rodízio/prioridades comerciais: dependem de especificação posterior, sem impedir consulta da fila.
- [x] Exportações e navegação do resumo para a origem do valor.

**Aceite:** totais globais conciliam com extratos individuais; excluir cancelamentos/estornos corretamente; PIX direto e crédito não multiplicam caixa. **Dependência:** extratos e decisão/classificação do legado. Se houver fontes ainda não integradas, indicar claramente a cobertura parcial.

### Sprint 15 — base multiempresa concluída localmente

A direção confirmada em 03/10 prioriza isolamento antes do piloto com várias empresas/Checkto. Autorizado em 03/10/2026 por “podemos começar”. Dividido após análise de acesso global:

- 15A concluído localmente: organizações, vínculos, convites e bloqueio de financeiro para novas lojas. 478 testes e frontend/HTTP aprovados. [Relatório 15A](2026-10-03-multiempresa-base/relatorio.md).
- 15B concluído localmente, autorizado por “pode seguir” e continuidade “pode continuar”: persistência financeira, anexos, links públicos e contexto por loja. 496 testes e ensaio A/B com IDs coincidentes aprovados. [Relatório 15B](2026-10-03-isolamento-lojas/relatorio.md).

Requisitos completos preservados:

- [x] Fundação de organizações/ambientes e vínculos, com acesso por loja nas rotas de organizações. Financeiro de novas lojas provisionadas usa banco e arquivos próprios desde 15B.
- [x] Identidade do fornecedor vinculável a várias lojas e convites controlados. Cadastro por convite API/interface e portal limitado entregues; consultar Sprint 16.
- [x] Contexto de autorização e isolamento de leituras/escritas, documentos e exportações; testes runtime A/B em bancos separados.
- [x] Ensaio aditivo da fundação em cópia, 37 tabelas preservadas e init idempotente. 15B acrescentou ensaio aditivo com 43 tabelas preservadas e bancos novos vazios. Migração operacional/dados reais permanece pendente.

Checkto por conta/organização depende dessa base; nenhuma transação externa autorizada neste fechamento. Se o escopo exceder um sprint, dividir em etapas com aceite explícito.

### Backlog replanejado — projeções, inadimplência e programação

**Objetivo:** transformar os ramos pouco especificados do mapa em regras aprovadas e testáveis.

- [ ] Levantar critérios de prioridade, dívida vencida, rodízio e programação com a loja.
- [ ] Definir diferença entre previsão, obrigação efetiva e pagamento confirmado.
- [ ] Implementar filtros/indicadores/sugestões e histórico das decisões de programação.
- [ ] Manter confirmação humana antes de qualquer aplicação financeira sugerida.

**Aceite:** previsão não altera dívida real; prioridade segue critérios aprovados; sugestão não executa pagamento/acerto automaticamente. **Dependência:** especificação da loja e visão consolidada. Não inventar regras para os ramos vazios do mapa.

### Sprint 16 — concluído localmente: portal do fornecedor e gestão de vínculos

Prioridade após isolamento: habilitar a participação própria do fornecedor definida pelo usuário. Autorizado em 03/10/2026 por “ok siga”; concluído localmente com 519 testes. [Relatório 16](2026-10-03-portal-fornecedor/relatorio.md). [Brief 16](2026-10-03-portal-fornecedor/brief.md).

- [x] Vincular identidade compartilhada à Pessoa do banco financeiro local, com contrato que não confunda IDs iguais entre lojas; não consumir FK legada central por inferência.
- [x] Portal somente das relações autorizadas, com pagamentos/saldos e gestão de suas chaves PIX.
- [x] Confirmar recebimentos com identidade/evidência e sem confundir declaração com evento bancário confirmado.
- [x] Administração de equipe/vínculos por loja, revogação local, último administrador e proteção da identidade compartilhada.
- [x] Testes de acesso indevido por fornecedor, troca de loja/ID, concorrência de chaves e revogação.

Checkto por organização continua futura, com leitura da documentação e contrato próprio antes da implementação. Sem acesso amplo de fornecedor ao painel interno.

### Backlog preservado — OCR e integrações de origem (proposta anterior do Sprint 16)

**Objetivo:** reduzir digitação com dados extraídos e eventos de origem verificável.

- [ ] Selecionar provedor OCR, custo, privacidade e destino dos arquivos; preservar alternativa manual.
- [ ] Extração real de campos, confiança por campo e revisão obrigatória de dados incertos.
- [ ] Definir contrato do gateway e/ou origem WhatsApp que será integrada; validar autenticidade/idempotência dos eventos e política de correção.
- [ ] Tratar arquivo duplicado, erro do provedor, evento repetido e campos ausentes sem inventar dados.

**Aceite:** imagem não confirma PIX nem fornecedor; webhook repetido não cria pagamento duplicado; falha mantém operação manual. **Dependência:** Sprint 10, serviços/canais e autorizações para envio de documentos/custos. OCR e gateway podem virar sprints separados; integrações opcionais não bloqueiam piloto manual do núcleo.

### Sprint 17 — homologação e piloto acompanhado

**Objetivo:** verificar o fluxo ponta a ponta antes de ativar a operação. Autorizado em 03/10 por “ok faça esse”; preparação local concluída. [Relatório17](2026-10-03-homologacao-piloto/relatorio.md).

- [ ] Testar stack de implantação definida, incluindo PostgreSQL se escolhido e Python declarado, autenticação, arquivos e concorrência.
- [x] Homologar localmente, com dados sintéticos, cenários cliente/fornecedor, dinheiro/repasse, nota parcial, sobra/crédito, lote misto, bloqueios de acesso definidos (contestação formal da declaração pendente) e estorno.
- [ ] Comparar resultados com o controle atual da loja; registrar divergências e corrigir antes de aprovação.
- [x] Preparar orientação operacional, backup/restauração e plano de recuperação.

**Aceite:** loja aprova os cenários e as divergências estão resolvidas ou explicitamente aceitas; restauração é ensaiada; sem falhas críticas pendentes. **Dependência:** escopo necessário ao piloto fechado e dados reconciliados. Uso de dados/ambiente operacional exige autorização; serviços opcionais podem ficar fora do piloto com limites declarados.

Validação local: 545 testes, 26 novos, Python 3.14/SQLite, três bancos e sete arquivos recuperados, HTTP/SSR aprovado. Item stack/implantação segue parcialmente pendente: stack atual verificada; PostgreSQL/carga apenas se escolhidos, ainda não homologados. Comparação real, aceite visual da loja e piloto acompanhado permanecem abertos. [Checklist](2026-10-03-homologacao-piloto/aceite-piloto.md).

### Sprint 18 — ativação operacional e publicação

**Objetivo:** colocar a versão homologada em uso, após autorização específica.

- [ ] Confirmar ambiente, versão, janela, backup e plano de recuperação.
- [ ] Executar migração operacional aprovada e verificar saldos/vínculos.
- [ ] Publicar a versão autorizada e validar domínio, rotas privadas/públicas aplicáveis, anexos e operações.
- [ ] Acompanhar a conferência inicial da loja e registrar o que está efetivamente ativo.

**Aceite:** versão e migração identificadas, dados reconciliados, rotas verificadas e recuperação disponível. **Bloqueio deliberado:** nenhuma ativação, publicação, commit ou push por inferência da aprovação de um sprint de desenvolvimento; obter autorização correspondente.

### Como esta sequência será atualizada

Ao aprovar um sprint, registrar autorização e escopo final nesta página. Ao concluir, mover seu resumo para o histórico, vincular relatório/validações e atualizar a sequência restante. Se houver divisão, reordenação ou adiamento, registrar o motivo e a nova numeração. Não transformar proposta em conclusão nem apagar requisitos pendentes. Esta sequência não define prazo ou quantidade garantida de sprints.

### Pendências posteriores, ainda sem sprint autorizado

- [ ] Adaptar modelos de cadastros/notas ao eventual formato da loja; importação financeira de pagamentos/legado após classificação (Sprint13). CSV de cadastros/notas e exportações já entregues no Sprint8.
- [ ] Definir política adicional para links antigos sem destino conhecido/nunca usados. Alertas de chaves e consulta de destinos entregues no Sprint8; links bloqueados não são redirecionados automaticamente.
- [ ] Catálogos configuráveis de formas, operações e prazos; regras de compra/devolução.
- [ ] Preferências de tabelas por usuário/tela: colunas, ordem, filtros e ordenação.
- [ ] Completar perfil/empresa/usuários e permissões por ação; convites dependem de canal e autorização de envio.
- [ ] Dashboard compartilhado revogável, duração, escopo e política de anexos previamente definidos.
- [ ] Evoluir visualização dos comprovantes e política de origem/gateway; OCR real somente após decidir provedor.
- [ ] Classificar conciliações antigas, integrar motores e travas, reconciliar saldos por pessoa; nenhuma importação automática consumível.
- [ ] Integrar dashboard global, rodízio e relatórios às novas fontes sem dupla contagem.
- [ ] Detalhar projeções, prioridade, inadimplência e programação com a loja.
- [ ] Homologar PostgreSQL/stack declarada se fizerem parte da implantação escolhida.
- [ ] Piloto acompanhado e comparação com o controle atual antes de ativar o banco operacional.
- [ ] Migração operacional e publicação somente com autorização específica, backup atualizado e revisão final.

### Decisões ainda abertas com a loja

Ocultar versus cancelar gateway; correções oficiais e contestação de comprovante; classificação Entrada/Saída versus Crédito/Débito; ordem/tolerância de eventual crédito automático; vencimento/expiração/transferências de crédito; política de compartilhamento/anexos; prioridade/inadimplência/programação; vocabulário de intermediador/representante; substituição versus coexistência com o sistema atual de notas. Os sprints realizados adotam crédito manual, confirmação declarada e sem transferência automática; não presumem respostas para os demais pontos.

## Ambiente, arquivos e cuidados na retomada

Frontend `../frontend/`; API `../app/`; testes `../tests/`; relatórios nesta pasta. Backups em `../backups-locais/`, ignorados. Segredos, `pix.db`, uploads e dados pessoais brutos não devem ser publicados.

Última demo registrada: http://localhost:3028/organizacoes, API127.0.0.1:8028, ambiente recuperado `/private/tmp/rotapay-s17-restaurado-final/` (central.sqlite3, tenants/, uploads/). Backup privado imutável `/private/tmp/rotapay-s17-backup/`; origem sintética `/private/tmp/rotapay-s17-origem/`. Demo3027/API8027 preservada/reiniciada; nenhuma configuração operacional alterada. Admin `demo@rotapay.local` / `[credencial demonstrativa omitida do Git]`; fornecedor `fornecedor.s15@rotapay.local` / `[credencial demonstrativa omitida do Git]`, lojas#2/#3. Processos/tmp são temporários; conferir ao retomar. O banco ativo pode receber novos logs técnicos; não confundir seu hash com o pacote imutável de backup. Dados exclusivamente sintéticos. [Recuperação](2026-10-03-homologacao-piloto/recuperacao.md).

Ambiente canônico do Sprint 11: `/tmp/rotapay-validacao-s11-py314/bin/python` (Python 3.14.0), com requirements e Pillow 12.3.0. Ambiente anterior `/tmp/rotapay-validacao-20261001/bin/python` permanece uma referência histórica. Comandos: `PYTHONPATH=. python -m pytest tests/ -q` na raiz; `npm run lint`, `npm run lint:types`, `npm run build`, `npx tsc --noEmit` no frontend. Usar banco isolado; não executar seed em produção. Não reiniciar serviços antigos 8000/3000 por suposição. Ao fazer novo build, encerrar somente o frontend demonstrativo sob controle do agente para evitar misturar assets.

## Como manter este documento atualizado

Obrigatório para cada fechamento de sprint:

- Atualizar data, último sprint, status de entrega local/operacional/publicada e autorização do próximo.
- Acrescentar linha e resumo do sprint com link ao relatório real, resultados efetivamente obtidos e limites.
- Reconciliar backlog: marcar o que foi concluído e preservar decisões abertas; não deixar uma pendência antiga como atual.
- Registrar demo/evidências e qualquer trabalho interrompido, falha ou bloqueio. Não depender de arquivos temporários como única documentação.
- Atualizar o `sprint.json` correspondente e apresentar relatório + próximo escopo ao usuário.
- Aguardar confirmação para o próximo sprint. Não atualizar o status para autorizado sem mensagem do usuário.

Se houver interrupção no meio de um sprint, registrar aqui: escopo autorizado, arquivos já alterados, testes feitos/não feitos, próximo passo exato e dependências. Este documento registra o trabalho; não cria agendamento, execução automática ou autorização de publicação.

## Mensagem pronta para retomar em outro chat

> Retome RotaPay em clientes/RotaPay. Leia CLAUDE.md, AGENTS.md, sprints/ESTADO-PROJETO.md e relatório 17; confira Git/processos. Sprint 17: preparação e homologação local concluídas com 545 testes (26 novos), Python 3.14/SQLite. App/frontend do Sprint 16 inalterados por SHA-256; lint/tipos/build anteriores não repetidos; nova verificação HTTP/SSR recuperada aprovada. Backup offline em scripts/backup_rotapay.py exige operação parada, inclui ambientes prontos/uploads, valida integridade/referências e restaura somente em diretório novo, reendereçando arquivo_path nas cópias. Origem perdida não impede recuperação; logos/anexos inativos validados. Três bancos (46/45/45 tabelas) e sete arquivos, saldos e declarações preservados. Demo3028/API8028 em /private/tmp/rotapay-s17-restaurado-final; pacote imutável /private/tmp/rotapay-s17-backup. Roteiro, recuperação e checklist entregues. Aceite visual, planilha real e piloto externo pendentes; sem PostgreSQL/carga, gateway, OCR, banco operacional, mensagens ou commit/push/deploy. Sprint 18: preparação e homologação técnica na VPS entregues; ativação aguarda pré-requisitos; migração/publicação só com autorização específica. Dois trajetos, sem crédito automático, stack atual no MVP; futuro Go+React+CSS sem Tailwind. Bloqueio do navegador respeitado. Atualizar continuidade a cada sprint.

## Fechamento da etapa 15A — 03/10/2026

Fundação de organizações/vínculos/convites entregue, identidade fornecedor compartilhada sem permissão financeira global; auditoria central separada e administração legada protegida contra tomada da conta compartilhada. 478 testes, lint/TypeScript/build/HTTP e preservação de 37 tabelas aprovados. [Relatório 15A](2026-10-03-multiempresa-base/relatorio.md). Naquele fechamento, cadastro inicial por convite somente API; interface entregue posteriormente em 15B. Nenhum P1/P2 na revisão deste escopo. Sem prova de isolamento financeiro A/B completo, PostgreSQL ou conferência visual; sem banco operacional, envio, integração Checkto, commit/push/deploy. Naquele fechamento o Sprint 15 permanecia aberto. A proposta 15B foi depois autorizada e concluída; consultar fechamento atual abaixo.

## Fechamento da etapa 15B — 03/10/2026

Sprint15 base multiempresa concluído localmente, 496 testes (18 novos), frontend/build/HTTP e ensaio em cópia aprovados. [Relatório 15B](2026-10-03-isolamento-lojas/relatorio.md). Bancos/arquivos próprios nas lojas novas, mesma PK sem compartilhar dinheiro/documentos, links públicos confinados e proteção de identidades internas/fornecedor compartilhadas. Senhas centrais não são copiadas; referências técnicas dos membros locais podem ser sincronizadas em leituras. Instância original mantém compatibilidade; nenhuma migração operacional ou ativação Checkto. Naquele fechamento, portal limitado do fornecedor, vínculo à Pessoa local e equipe estavam pendentes. Entregues posteriormente no Sprint16, conforme fechamento abaixo. OCR/integracoes originais mantidos no backlog. Demo3026/API8026 temporária; sem ensaio visual/PG/carga/operacional, envio, commit/push/deploy.

## Fechamento do Sprint 16 — 03/10/2026

Autorizado por “ok siga”; concluído localmente. [Relatório 16](2026-10-03-portal-fornecedor/relatorio.md). 519 testes (23 novos), 180,30s/Python3.14, lint sem erros/avisos, TypeScript, lint tipado sem erros/200avisos preexistentes, build55páginas e HTTP/SSR aprovados. Três bancos sintéticos,44tabelas anteriores preservadas porbanco, inicialização idempotente. Portal com associação explícita porloja, chaves próprias, notas/saldos/recebimentos, declaração humana sem crédito/abatimento/banco automático, equipeporvínculo e último admin protegido. Abatimento/estorno conserva declaração válida; alteração do valor/cancelamento preserva histórico sinalizado. Correções de timestamp, perfilcompatível/admin original e versão de alocação aprovadas. Revogação local não muda conta pessoal. Nenhum P1/P2 pendente na revisão deste escopo.

Uma rodada encontrou falta de espaço no temporário do Mac (511passed/8erros de preparação); cache derivado307MB foi removido, demo voltou e suíte final519passou em pasta própria. Sem dados do usuário apagados. Limites: associação imutável requer fluxo futuro de correção, criação de nova conta interna não incluída, políticas configuráveis/contestação/extensão externa de créditos/acertos futuras. Sem PostgreSQL/carga/visual interativo ou banco operacional; sem mensagens, Checkto, OCR, deploy, commit/push. Demo3027/API8027 sintética. PróximoSprint17: homologação local pontaaponta, backup/restauração e orientação/aceite do piloto; aguarda confirmação. Dados/planilha e ativação real continuam dependências por implantação, não autorização implícita deste desenvolvimento.

## Fechamento local do Sprint 17 — 03/10/2026

Autorizado por “ok faça esse”. [Relatório 17](2026-10-03-homologacao-piloto/relatorio.md). Preparação e homologação local concluídas: 545 testes (26 novos), 228,84 s, Python 3.14, um aviso Starlette preexistente. Fontes app/frontend do Sprint 16 inalteradas por SHA-256; lint/tipos/build anteriores não repetidos. Quatro cenários integrados e 22 testes de backup, com HTTP/SSR recuperado conferido. Backup/restauração em destino novo: controle com 46 tabelas, duas lojas com 45 tabelas cada, sete arquivos preservados, anexos/logos/saldos/declarações conferidos pela aplicação. Anexo inativo continua bloqueado. Caminhos das cópias e validação de logos corrigidos; origens sintéticas preservadas e nenhuma alteração operacional. Roteiro, recuperação e checklist entregues; pacote privado sem envio. Sem P1/P2 pendentes nas fontes novas revisadas.

Aceite completo do Sprint 17 depende da loja: comparação com controle real, conferência visual/celular, tratamento de associação/declaração incorreta, onboarding interno, responsáveis/rotina/guarda e implantação. Não declarar piloto real aprovado. PostgreSQL/carga/Checkto/OCR não ensaiados. Sem envio, migração operacional, commit/push/deploy. Próximo Sprint 18: preparar ativação com ambiente, dados reconciliados, janela, backup e retorno; aguarda confirmação e pré-requisitos. Publicação/migração exige autorização específica.


## Preparação local do Sprint 18 — 03/10/2026

Autorizada por “vamos seguir”. [Relatório](2026-10-03-preparacao-ativacao/relatorio.md) e [plano de ativação/retorno](2026-10-03-preparacao-ativacao/plano-ativacao.md). Persistência Docker corrigida para `/data/ambientes`; ferramenta de backup incluída na imagem; roteiro de VPS atualizado. 22 testes de backup passaram em 0,28 s. Docker indisponível: imagem e Compose não executados, Python 3.12 da imagem ainda precisa ser homologado frente ao ambiente local 3.14. Instalações antigas podem ter bancos fora do volume: preservar antes de recriar containers. Nenhum banco operacional, servidor, integração, publicação, commit/push foi alterado. Sprint 18 operacional aberto: aceite real, ambiente, reconciliação, políticas, janela, homologação da imagem e autorização específica pendentes. Próxima ação é cumprir esses requisitos; não iniciar outro sprint sem confirmação.


### Definição de hospedagem do Sprint 18

Usuário confirmou VPS existente. [Roteiro](2026-10-03-preparacao-ativacao/vps-existente.md), `docker-compose.ip.yml` e `.dockerignore` preparados. Hostinger/IP2.24.108.54 e Caddy do host são registros históricos, não inventário atual. Acesso SSH não identificado; aguardando endereço/usuário ou alias. Sem acesso remoto, build, publicação ou migração. Validação de Compose/imagem ainda pendente.


### Inventário atual da VPS — Sprint 18

Acesso anterior confirmado por chave como root em 2.24.108.54, leitura apenas. [Inventário](2026-10-03-preparacao-ativacao/inventario-vps.md). Docker29.4.3/Compose5.1.3, Python3.12.14, API/painel ativos, volume pix_pixdata, 28GB livres. /srv/pix não é checkout Git; uploads configurados ausentes e caminhos/cadastro precisam ser conferidos antes de migração. Sem alteração remota. Próxima etapa: candidato separado e homologação sintética; publicação permanece não autorizada.


### Homologação técnica na VPS — Sprint 18

Autorizada por “ok” após inventário. [Relatório](2026-10-03-preparacao-ativacao/homologacao-vps.md). API/web construídas na VPS, Python3.12 homologado com545tests/422,61s/1aviso, TypeScript/build do painel e Compose aprovados. Backup sintético3bancos7arquivos restaurado em volume próprio; smoke HTTP admin/fornecedor/lojas e proteção aprovado. Pasta /srv/rotapay-homologacao-s18, projeto rotapay-s18, volume rotapay-s18_dados_sinteticos; portas apenasloopback8128/3128. Operação pix preservada, sem promoção, seed/migração real, Checkto, commit/push. 24GB livres apósbuild. Evidências/manifesto de candidato registrados; ambiente sintético ativo. Próximo: aceite real, domínio/HTTPS, referências antigas, reconciliação, políticas e janela, depois autorização específica de ativação. Sprint18operacional permanece aberto; não iniciar outro sprint automaticamente.


### Domínio informado e conferido

rotapay.site confirmado pelo usuário. DNSA atual2.57.91.91 diverge da VPS2.24.108.54; www alias, semAAAA observado. HTTPSfalhou; Caddyhost apenas:80. [Proposta de domínio](2026-10-03-preparacao-ativacao/dominio.md) e Caddyfilecandidato preparados, sem alterarDNS/proxy. Conectar domínio à versão atual é ação separada da promoçãoS18 e requer autorização específica.


### Entrega pública de testes pelo domínio

Usuário autorizou entrega antes do aceite. [Relatório](2026-10-03-preparacao-ativacao/dominio-publicado-testes.md). DNSA/@ atualizado2.24.108.54/TTL300; nameservers mantidos. Caddyhost validado/recarregado, certificados HTTPS e wwwredirect aprovados. rotapay.site encaminha à homologação3128/dados sintéticos, comnoindex. Operação3000/bancos preservados. BackupCaddyfile /etc/caddy/Caddyfile.pre-rotapay-s18. Login e páginas autenticadas/controles públicos conferidos. Migração/pilotooperacional nãoautorizados; próximo receber testes da loja.


## Página de vendas — 03/10/2026

Usuário autorizou construção com copy revisada, referências, GSAP e parallax. [Relatório](2026-10-03-pagina-vendas/relatorio.md). Página publicada no ambiente de testes em https://rotapay.site/conheca; raiz semsessão exibeLP, raiz comsessão preservapainel. Lint0/0, TypeScript/buildremoto56rotas,HTTP13assets e loginpreservado, revisão desktop/mobile390, tabs/FAQ/simulação/menuaprovados. Sówebhomologação atualizado para rotapay-s18-web:lp-final-20261003; API/operacionalpreservados. Semcommit/push/migração. Próximo: avaliação visual/comercial do usuário; canalcontato/preço/provasreais/indexação posteriores. PendênciasoperacionaisS18 mantidas; não iniciaroutr sprint automaticamente.


## Produção com cadastro — 03/10/2026

Usuário autorizou ativação com pré-aprovação da loja e separação dos domínios. [Relatório](2026-10-03-producao-cadastro/relatorio.md). **Concluída e conferida:** vendas https://rotapay.site/; aplicativo https://app.rotapay.site/; cadastro https://app.rotapay.site/cadastro-loja. Cadastro isolado por loja, 566 testes locais e 21 na imagem Python3.12 aprovados; lint/TypeScript/build final e HTTPS/14 assets aprovados. Cadastro técnico, acesso, logout/login persistente e bloqueio de outra organização 403 conferidos; conta técnica inativada. Produção independente /srv/rotapay-producao-20261003, projeto rotapay-prod, volume rotapay-prod_dados, loopback web3130/API8130. Imagem web20261003-v2. Banco sem demonstração; backup inicial verificado, restaurado em ensaio e copiado para reserva local privada. VPS reiniciada com autorização após indisponibilidade; adicionados swap2GiB e limiteheap1024MiBbuild. Causa original não confirmada. Legado preservado, sem migração, Checkto ou commit/push. Próximo: loja criar conta real e testar operação; validaçãoemail/recuperaçãosenha/backupperiódico específico e integração bancária permanecem pendentes. Não iniciar novo sprint sem confirmação.


## Banner de compartilhamento — 03/10/2026

Banner1200×630 publicado em /brand/rotapay-compartilhar-v1.png, OG/Twitter completos na página comercial e canonical raiz. Lint/TypeScript/revisão/build aprovados; HTML e imagem pública conferidos. Web agora rotapay-prod-web:og-20261003. [Relatório](2026-10-03-banner-compartilhamento/relatorio.md). Cache da prévia depende do aplicativo destinatário. Sem alterações de banco/auth, commit/push ou mensagem externa.


## Refinamento de cadastro — 03/10/2026

Tela pública /cadastro-loja melhorada e publicada, imagem web rotapay-prod-web:cadastro-ui-20261003. [Relatório](2026-10-03-cadastro-interface/relatorio.md). Labels/campos alinhados, CSSModulesisolado, ajuda senha integrada, desktop duascolunas/mobile uma. Lint/TS/detector/revisão/build aprovados; visual pública desktop1280/mobile390 semoverflow. Contrato de cadastro preservado, sem banco/auth ou commit/push. Próximo: avaliação do usuário; não iniciar novo sprint automaticamente.


### Banner humano de compartilhamento

Versão2 publicada a pedido do usuário, vendedor orientando cliente final pagando pelo linkPIX. OG/Twitter usam /brand/rotapay-compartilhar-v2.jpg; JPEG1200×630 e HTTP200 conferidos. Web rotapay-prod-web:banner-v2-20261003. Lint/TS/revisão/build aprovados. Sem alteração de aplicação ou dados.


### Banner versão3 — venda porta a porta

A pedido do usuário, cena substituída por vendedor com catálogo/bolsa na entrada da casa e cliente usando PIX no celular. Editado por imagegen, JPEG1200×630 /brand/rotapay-compartilhar-v3.jpg; OG/Twitter atualizados. Lint/TS/revisão/build aprovados; HTML e asset público200 conferidos. Web rotapay-prod-web:banner-v3-20261003. Sem banco/auth/commit/push ou envio externo.


## Link demonstrativo na página de vendas

03/10/2026: prévia interativa publicada em /#link-demonstrativo, valorfixo/editável e valor informado pela cliente, com hero vinculado. Demonstração fictícia semAPI ou pagamento real; não altera modelo de cobrança do aplicativo. Lint/TS/revisão/detector/build e interação desktop/mobile aprovados; cadastro/OGpreservados. Web rotapay-prod-web:link-demo-20261003. [Relatório](2026-10-03-link-demonstrativo/relatorio.md). Próximo avaliação do usuário; não iniciar sprint automaticamente.


## Simuladores retirados e narrativa por rolagem

03/10/2026: usuário rejeitou LinkPreview/Example, ambos removidos da renderização. PaymentStorypassiva com fotoportaaporta limpa e camadas GSAP/pin/scrub, etapas link/pagamentoilustrado/comprovante, sem filme de personagens. Emaltura<720/reduced-motion mostra etapas estáticas. Lint/TS/detector/revisão/build e navegação pública aprovados. Web story-final-20261003. Limpeza cacheDocker após disco cheio, sem tocar dados ou serviços emuso. [Relatório](2026-10-03-narrativa-rolagem/relatorio.md). Próximo aprovação visual/possívelvídeoreal e integraçãohero; não iniciar sprint semconfirmação.


## Contraste do custo da desorganização

03/10/2026: bloco claro, frases grandes separadas e entrada sequencial GSAP. Contraste13,19/5,85:1, lint/TS/detector/revisão/build e visual desktop/mobile aprovados. Web contraste-20261003. [Relatório](2026-10-03-contraste-desorganizacao/relatorio.md). Sem banco/auth/commit/push. Próximo avaliação do usuário.


## Sincronização com GitHub — 04/10/2026

Usuário autorizou commit e push das entregas acumuladas. Preparado envio do código, ativos públicos e documentação dos sprints ao repositório próprio do RotaPay. Backups, bancos, ambientes locais, evidências, respostas em áudio e dados privados ficam ignorados. Credenciais da demonstração foram removidas dos documentos versionados. Validação atual: 566 testes aprovados, lint e TypeScript aprovados. A conclusão do push deve ser confirmada pela igualdade entre HEAD e origin/main.


## Remoção de WhatsApp e caixa de entrada — 04/10/2026

Solicitação do usuário: remover os módulos de integração WhatsApp e caixa de entrada. Retiradas telas WhatsApp, triagem, caixa de entrada e revisão, menus e ajuda, proxy /api/wa, gateway Baileys e serviço Compose. Retirados endpoints de recebimento externo, listagem da caixa, criação de movimentação pela caixa e rejeição da caixa. Leitura autenticada de arquivos preservada no router comprovantes, com confinamento por ambiente. Anexos manuais, pagamentos, conciliação, históricos e dados já armazenados preservados. Atalho de contato usa telefone. Campos de contato do formulário comercial não são integração e continuam disponíveis. Validação: lint/TypeScript e 38 testes focados aprovados; build e publicação concluídos em produção e demo; login/menu autenticados e rotas removidas 404 conferidos. [Relatório](2026-10-04-remocao-whatsapp/relatorio.md). Alterações desta etapa ainda sem commit/push.


## Diagnóstico do acesso à demo — 04/10/2026

Usuário tentou credenciais antigas da homologação pela raiz comercial/produção. API da produção responde 401 porque a base contém somente a conta técnica inativa; não contém os usuários da demonstração. Os dois acessos de homologação foram validados novamente pelo BFF: login 200 e painel de organizações 200, incluindo perfil fornecedor. A remoção de WhatsApp não invalidou credenciais. Subdomínio demo.rotapay.site ainda sem registro DNS. Painel Hostinger aberto e aguardando autenticação do usuário para adicionar A demo -> 2.24.108.54. Não anunciar demo pública antes de confirmar DNS, HTTPS e sessão pelo domínio.


### Acesso público à demonstração restabelecido — 04/10/2026

DNS A demo -> 2.24.108.54 criado via painel Hostinger no Comet, TTL300. Configuração ativa real /etc/caddy/Caddyfile corrigida (arquivo no diretório do projeto não era o ativo), demo -> web3128, HTTPS válido e noindex. Dois usuários de homologação validados via https://demo.rotapay.site/api/login e sessão/cookies reais em /organizacoes: administrador e fornecedor responderam 200. Produção app.rotapay.site permanece separada, sem usuários demo. Resolver local/Comet ainda guardava NXDOMAIN anterior; possível espera de propagação/cache. Não houve redefinição de senhas.


## Apresentação e sincronização GitHub — 04/10/2026

Usuário confirmou o nome remoto `rotapay` e autorizou atualização do GitHub. README refeito em PT-BR com banner oficial, capturas atuais da demo (dados sintéticos), funcionalidades, stack e pendências reais; descrição e homepage do repositório atualizadas. Visibilidade privada preservada. Remoção de WhatsApp incluída neste envio. Validações locais: lint, TypeScript e 38 testes focados aprovados. A sincronização é concluída somente com push e igualdade HEAD/origin/main; nenhuma implantação adicional faz parte desta etapa. Próximo desenvolvimento depende de confirmação do usuário.
