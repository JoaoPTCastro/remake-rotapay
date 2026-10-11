# Sprint 14 — Visão global dos módulos novos

Retomado em 03/10/2026 após interrupção, por autorização “ok continue o sprint”. Concluído localmente: 461 testes aprovados no Python 3.14.0 em 274,49 segundos (28 casos novos), com um aviso preexistente de Starlette/httpx.

## Entrega

Home agora apresenta notas, pagamentos, créditos e acertos do domínio novo. O painel original foi preservado em `/?escopo=legado`, identificado como consulta separada. `/visao-geral` oferece o mesmo painel e posições por titular/relação, filtros por nome/ID, paginação independente das posições e fila, links para extratos e documentos.

Contas cliente/fornecedor permanecem independentes. Eventos cliente→loja, repasses loja→fornecedor e pagamentos diretos cliente→fornecedor ficam separados. Diferença entre entradas/repasses não é saldo bancário nem caixa completo. Pagamento direto não é entrada na loja; crédito reconhecido não é novo recebimento. Disponibilidade dos pagamentos já desconta recursos destinados ao crédito antes de somar crédito disponível.

Totais globais e extratos individuais usam o mesmo cálculo SQL por conta, com exclusão dos efeitos cancelados/estornados/revertidos e preservação do histórico de titulares inativos ou com papel alterado. O resumo monetário global e o fluxo declarado são lidos em um statement, sem consultas individuais por titular. Filtros/páginas afetam listas, não totais globais.

Fila somente de notas abertas com saldo positivo, ordenada por vencimento (sem vencimento por último), emissão e ID. Não usa projeções como obrigações nem programa pagamentos. Critérios comerciais de rodízio/prioridade continuam pendentes.

CSV privado de posições por relação, nome e ID, incluindo todas as páginas dos filtros: UTF-8/BOM, ponto-e-vírgula, valores com duas casas/vírgula e neutralização de fórmulas em nomes. Até 10.000 contas; acima disso rejeita e pede filtros, sem truncar. Proxy mantém JWT no servidor, rejeita parâmetros extras/duplicados, restringe destino upstream, não segue redirects e limita resposta a 16 MiB. Erros públicos do proxy são sanitizados; cabeçalhos private/no-store, nosniff e no-referrer.

## Validação e evidências

Lint normal sem erros/avisos, TypeScript aprovado, lint de tipos com zero erros e 200 avisos preexistentes. Build Next 16.3.8 aprovado, 53 páginas. Logs e resultados em `sprint.json` e [evidencias](evidencias/). Testes específicos incluem somas independentes, centavos 0,10+0,20, ambos os trajetos, disponibilidade de crédito, estornos/reversões/cancelamentos, perfis, filtros/páginas, histórico inativo, busca literal %/_, CSV e preservação de registros. Revisão separada do backend e frontend não encontrou P1/P2 pendentes.

Ensaio HTTP em cópia sintética: painel confere com soma dos extratos individuais, CSV confere com posições, fila positiva, relações inválidas recusadas e 37 tabelas anteriores preservadas. Inicialização repetida não criou novas tabelas deste sprint. Somente login acrescenta eventos de auditoria; nenhuma operação financeira foi criada pelo ensaio.

SSR conferido com admin e consulta: home novo, alias, painel legado e CSV privado; JWT ausente no HTML. CSV do proxy idêntico ao backend, parâmetros indevidos recusados, POST não suportado, sem sessão painel redireciona ao login e CSV retorna 401. Isso é verificação HTTP/HTML, não visual interativa/mobile.

## Limites

- Cobertura parcial explícita: legado excluído e consumo integrado desligado. Dados de migração da primeira loja são requisitos de implantação, não bloqueio universal do produto.
- Produto multiempresa, convites e acesso próprio dos fornecedores ainda não implementados/validados. Não usar aprovação destes testes como prova de isolamento entre lojas.
- Checkto existente não foi ativada nem alterada neste sprint; integração por organização, confirmação bancária e repasses precisam de trabalho específico. Nenhuma transação de gateway executada.
- Sem migração para Go ou remoção de Next.js. MVP mantém stack atual; CSS sem Tailwind, sem dependência nova. Código novo separa cálculo, endpoints e componentes por responsabilidade.
- Sem ensaio PostgreSQL, carga operacional ou validação visual. A revisão automática anterior rejeitou navegador por política URL/protocolo; bloqueio respeitado.
- Sem acesso ao banco operacional, commit, push, deploy ou publicação.

## Demo e próximo passo

Demo temporária: http://localhost:3024/, API 127.0.0.1:8024, SQLite `/tmp/rotapay-visao-global-demo-20261002.db`, uploads `/tmp/rotapay-visao-global-demo-uploads`. Admin sintético `demo@rotapay.local` / `[credencial demonstrativa omitida do Git]`; consulta `consulta.s11@rotapay.local` / `RotaPay-consulta-2026`. Bancos/processos em /tmp são descartáveis.

Replanejamento proposto, em resposta às definições de produto de 03/10: próximo Sprint 15 deve priorizar base multiempresa, vínculos de fornecedores, convites e isolamento de acesso. Critérios de programação/rodízio do Sprint 15 original ficam no backlog para especificação posterior. Checkto depende do contexto correto de organização/conta. Não iniciar próximo sprint antes da confirmação do usuário.
