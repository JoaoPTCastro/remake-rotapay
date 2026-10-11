# RotaPay — planejamento a partir da revisão da loja

> Atualização em 01/10/2026: as respostas em áudio corrigem a interpretação financeira deste documento. Consulte [análise e plano revisado](../2026-10-01-respostas-audio/analise-e-plano-revisado.md). Em especial: dois acertos independentes por pagamento e abatimento parcial na nota original, sem criar nova nota quando falta valor. Este documento permanece como histórico da análise do mapa.

Estado: proposta de implementação, sem mudança de código. Fonte e cobertura em evidencias/requisitos-mapa.md. Classificação: pedido explícito = mapa; atual = código inspecionado; recomendação = desenho proposto; lacuna = decisão ainda aberta.

## Diagnóstico e direção

O mapa pede uma conta financeira por pessoa/empresa, com pagamentos registrados separadamente e acertos entre múltiplos créditos e débitos. A aplicação atual registra PIX e concilia uma movimentação com um lançamento/projeção. É evolução do domínio, não só reorganização visual.

Recomendação: manter API, frontend, trilha de pagamentos e histórico; ampliar cadastros, lançamentos e introduzir acerto com itens. Não reescrever o projeto. Não implementar remanescente antes de definir titularidade, origem do crédito e conservação dos saldos.

## Comparação completa

| Área | Atual observado | Planejamento |
|---|---|---|
| Login | JWT e quatro perfis | Manter autenticação; ajustar autorização por ação ao introduzir permissões personalizadas. |
| Menu | Início, PIX, Cadastro, Controle, Links e telas secundárias | Organizar em Cadastros, Créditos e Débitos, Pagamentos, Projeção e Configurações; decidir posição de Início. Preservar rotas antigas por compatibilidade. |
| Pessoas | Tipo único representante ou fornecedor; contato/email únicos | Papéis cliente/fornecedor/ambos, contatos múltiplos, principal e responsável. Não presumir representante=cliente até validar terminologia. |
| Lista cadastral | Listas e busca existentes | Lista unificada; cliente/fornecedor/todos; busca ID/chave/nome; WhatsApp, chave principal, copiar; importar/exportar. Importação com prévia, duplicidades e confirmação de lote. |
| Tabelas | Colunas e filtros definidos por tela | Mostrar/ocultar/reordenar colunas, ordenar, limpar filtros e salvar preferências por usuário/tela. Interpretar orientação como ordenação até confirmação. |
| Chaves | Uma chave armazenada em Pessoa | Entidade própria: múltiplas, principal, tipo, agência, tipo conta, fixa/temporária, validade, ativa; alertas dívida sem chave válida/vencimento. |
| Links | Vendedor+fornecedor, valor fixo opcional, revogação e Checkto | Escolha de chave válida, acesso no cadastro e pagamentos, compartilhar/status, ativar/desativar; preservar histórico de links usados. Definir exclusão de links sem uso. |
| Dashboard individual | Dashboard global por fornecedor | Extrato de cada cadastro com aberto/pago/crédito/atraso, documentos e transações. Link de leitura limitado a esse cadastro, revogável, com anexos conforme permissão. |
| Lançamentos | Tipos fixos, descrição, data, saldo; sem vencimento/anexo próprios no modelo | Natureza crédito/débito + operação cadastrável; titular/contraparte, vencimento ou sem vencimento, prazo herdado, observação, anexos nota/pedido; edição/cancelamento conforme vínculos. |
| Acerto | Uma movimentação → um alvo por conciliação; parcial e estorno | Seleção de múltiplos créditos/débitos, totais, prévia da diferença, fechamento atômico e remanescente ligado ao acerto. Detalhe e estorno integral com dependências. |
| Pagamentos | Movimentações + triagem de comprovantes | Relação única com origem manual/gateway/WhatsApp, intermediador, remetente, favorecido, autor e operador distintos; data lançamento separada de data/hora transação; filtro valor, atualizar e cards. |
| Comprovantes | Upload/download, hash, fila e revisão | Popup lateral, zoom/tela cheia; política por origem no backend; gateway imutável e ocultação separada de cancelamento financeiro. |
| OCR | Simula dados já presentes na movimentação | Extrair do arquivo antes de cadastrar, confiança por campo, revisão de campos incertos, tratamento erro; não conciliar nem confirmar pagamento apenas pela imagem. Provedor a decidir. |
| Usuários | Criar/editar/perfil/ativação/reset de senha | Convites, contato, CPF, nascimento/foto e permissões por ação. Envio de convites depende de canal configurado e autorização de envio. |
| Conta pessoal | Tela de senha e conta existentes | Perfil pessoal editável; nível exibido, alteração apenas por administrador autorizado. |
| Empresa | Nome/documento/endereço/telefone/email | Acrescentar logo; separar Empresa e Minha Conta. |
| Configuração financeira | Strings/tipos fixos e prazo no fornecedor | Catálogos de formas, prazos e operações; ativação e restrição de exclusão; prazo/descrição congelados nos lançamentos para preservar histórico. |
| Auditoria | Logs estruturados e histórico | Linha do tempo legível, antes/depois, quem/quando/motivo, acertos, remanescentes, mudanças de chave e permissões. |
| Projeção | Par representante/fornecedor, simulador, sugestões e fila | Reaproveitar; desenvolver prioridade de débitos, inadimplência, programação e dashboard após especificação da loja. O mapa só nomeia esses ramos. |

## Acertos: regra financeira proposta

O mapa exige fechar os itens escolhidos e criar remanescente. A regra atual conserva sobra no PIX ou cria crédito explícito dentro da tolerância. Não substituir silenciosamente essa regra.

Exemplo, na perspectiva da loja: débitos selecionados de R$ 1.000 e créditos disponíveis de R$ 800 → itens selecionados encerrados pelo acerto e novo débito de R$ 200 vinculado ao acerto. Débitos R$ 1.000 e créditos R$ 1.200 → crédito remanescente de R$ 200. Igualdade → nenhum remanescente.

Invariantes: dívida líquida antes/depois deve ser igual; o remanescente transfere saldo existente, não gera dinheiro; crédito pago não pode existir simultaneamente como saldo PIX utilizável e lançamento utilizável. Um pagamento pode originar um crédito rastreável, mas apenas uma representação pode ser consumida. Não somar obrigações e projeções como se ambas fossem dívidas distintas.

Registrar valor original, saldo consumido, fonte, titular, acerto e descendência de remanescentes. Exibir encerrado por acerto quando uma nota não foi integralmente paga: a diferença foi transferida. Não chamar toda nota encerrada de dinheiro pago. Se remanescente já foi usado, estorno do acerto anterior exige tratar os acertos posteriores; nunca reabrir saldo duplicado.

Antes de gravar: simular; validar titular e elegibilidade; reapurar saldos na transação; impedir clique repetido/reuso concorrente; gravar itens, fechamento, remanescente e auditoria juntos ou não gravar nada. Usar valores decimais na nova lógica e locks transacionais adequados à implantação.

## Modelo e migração propostos

- Pessoa com papéis (ou associação PessoaPapel), PessoaContato, ChavePix. Evitar duplicar pessoas apenas para conferir ambos os papéis; fusões só com revisão.
- FormaPagamento, CondicaoPrazo, OperacaoFinanceira; vínculo aos cadastros. Operação tem classificação financeira validada: Entrada/Saída não equivale automaticamente a Crédito/Débito.
- Lancamento ampliado com natureza/operacao/titular, vencimento opcional, referência de prazo congelada e anexos próprios.
- Pagamento preserva Movimentacao como origem; acrescentar origem e referência externa, data/hora com fuso, informações bancárias e visibilidade. Referência externa idempotente quando fornecida pelo gateway.
- Acerto e AcertoItem com fontes e valores; remanescente explicitamente ligado ao acerto. Adaptar conciliações antigas sem recriar ou consumir saldo.
- PreferenciaTabela, Permissao/override de usuário, ConviteUsuario e AcessoDashboard com token revogável/escopo.
- Migração incremental com cópia de segurança e relatório de contagens/saldos por pessoa; manter IDs e conciliações existentes. Converter chave única em chave principal; tipo de chave não identificável fica para revisão; horário desconhecido dos PIX antigos permanece desconhecido, não inventar meia-noite como horário real.
- Não criar créditos históricos em lote sem estratégia de representação única e simulação de impacto.

## Jornadas e estados essenciais

1. Cadastro → Dados/Financeiro/Dashboard. Sem chave: alerta e impedimento de gerar link inválido. Sem movimentos: exclusão elegível; com histórico: desativação.
2. Crédito/Débito → natureza/operação → formulário → revisão → salvar. Prazo calculado pode ser revisado; sem vencimento não entra em atraso automaticamente.
3. Pagamento manual → anexo → OCR → campos sugeridos → revisão → registro. OCR indisponível permite preenchimento manual; arquivo repetido e campos faltantes têm mensagens claras.
4. Gateway → confirmação verificável/idempotente → registro imutável. Desabilitar oculta, sem apagar obrigação ou prova; conteúdo fica disponível em filtro avançado conforme permissão.
5. Acerto → titular → selecionar fontes elegíveis → totais/diferença → confirmar → recibo de acerto e remanescente. Sem itens/saldo ou concorrência: impedir fechamento e atualizar prévia.
6. Dashboard compartilhado → somente cadastro autorizado. Token inválido/revogado não revela dados; nenhuma rota permite edição ou consulta de terceiros.

## Fases e critérios de aceite

### 0 — Definição das regras e baseline
Resolver perguntas financeiras abaixo; fotografar os saldos por entidade em ambiente autorizado; definir matriz de permissões e vocabulário. Aceite: três exemplos de acerto (igual, sobra e falta), pagamento direto e devolução aprovados pela loja, sem ambiguidade de titular.

### 1 — Cadastros e configurações
Papéis, contatos, chaves múltiplas, prazos/formas/operações, logo e preferências de tabela. Aceite: pessoa com ambos os papéis; chave principal vencida; cadastro com movimento não excluível; alterar prazo não muda dívida antiga; importação apresenta erros antes de gravar.

### 2 — Obrigações e conta individual
Lançamentos com vencimento/anexos, extrato e dashboard individual. Aceite: dívida vencida aparece em atraso; sem vencimento fica fora; totais por pessoa batem com os registros e distinguem transferência de saldo de pagamento.

### 3 — Motor de acerto
Prévia, itens múltiplos, remanescente, histórico e estorno. Aceite: conservação de saldo nos três exemplos; mesma fonte não consumida duas vezes; falha intermediária reverte tudo; estorno com remanescente reutilizado não duplica crédito/débito.

### 4 — Pagamentos e documentos
Lista/detalhe, proveniência, travas backend, visualizador, OCR real, links com escolha da chave. Aceite: gateway não editável via API; ocultação não altera saldo; webhook repetido não duplica; chave vencida não gera novo link; OCR não inventa campos ausentes e manual continua disponível.

### 5 — Acesso, compartilhamento e piloto
Convites, perfil, permissões por ação, dashboard compartilhado e piloto persistente. Entitlement backend deve existir desde a primeira ação nova; esta fase completa administração e convites. Aceite: consulta sem escrita; usuário não eleva próprio perfil; link de cadastro A não acessa B; revogação funciona; piloto passa por fluxo real acompanhado.

Projeção detalhada entra após as definições da loja; não transformar ramos vazios em escopo supostamente aprovado. Corrigir nome/marca RotaPay em etapa própria, com identidade validada. Deploy/commit/push/publicação e envio de convites precisam de autorização específica.

## Decisões abertas, por impacto

1. Crédito/débito são vistos da perspectiva da loja? O titular do acerto é fornecedor, cliente ou ambos? O mesmo acerto pode combinar diferentes pessoas/fornecedores?
2. Todo pagamento aprovado gera crédito para o favorecido? Quando cliente paga fornecedor, também abate saldo do cliente perante a loja? Essas são duas contas diferentes; explicitar vínculo sem duplicar valor.
3. Remanescente é sempre criado ao fechar o lote, como escrito no mapa, ou pode manter itens parcialmente abertos? Como vence o débito remanescente? Ele mantém vínculo com as notas e seus vencimentos?
4. Desabilitar gateway significa só ocultar ou rejeitar o registro para fins financeiros? Proposta: só ocultar; cancelamento/estorno é ação separada.
5. Papel de Autor, Remetente, Responsável, Intermediador, Credor/Devedor e Favorecido. O mapa coloca Remetente sob Destino; confirmar se quis dizer destinatário.
6. Qual regra define operação Entrada/Saída versus Crédito/Débito? Tipos como compra/devolução precisam de exemplos concretos.
7. Principalidade é por contato, por telefone/email ou por responsável? Como escolher chave quando principal vence? Proposta: não trocar destino automaticamente; pedir escolha de chave válida.
8. Dashboard compartilhado exige login? Quem pode ver anexos? Expiração e revogação? Proposta: leitura escopada, sem privilégios do painel.
9. Sentido de programação: agenda de pagamentos, recebimentos esperados ou roteamento de chaves? Qual cálculo de inadimplência e prioridade por débito? O mapa não especifica.
10. Catálogos: excluir apenas itens nunca usados; desativar itens usados. Congelar prazo nos lançamentos. Confirmar interpretação da nota contraditória sobre exclusão e pagamentos em andamento.

## Coordenação Codex/OpenCode

Usar este documento e evidencias/requisitos-mapa.md como referência compartilhada. Cada tarefa descreve decisão aprovada, arquivos, critério de aceite e migração. Um responsável por alteração financeira por vez; evitar edições simultâneas no mesmo arquivo. Registrar decisões no projeto; conversas de um ambiente não são automaticamente visíveis no outro. Não há estimativa de prazo fechada sem resolver a fase 0.
