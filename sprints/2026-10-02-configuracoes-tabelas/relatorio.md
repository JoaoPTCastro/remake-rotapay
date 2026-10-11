# Sprint 9 — configurações e preferências de tabelas

Data: 02/10/2026. Estado: concluído e validado localmente. Autorização: “continue”. Somente ambiente local.

## Entregas

- Catálogos de formas suportadas (PIX/dinheiro), operações descritivas e condições de prazo. Administração por admin/financeiro; consulta pelos quatro perfis. Criar, renomear, ativar/desativar; não há exclusão física. Significado, aplicação e prazo são fixos: outra condição exige novo item.
- Seleções opcionais em novas notas e pagamentos, com IDs e nomes congelados. Condição de prazo gera vencimento em dias a partir da emissão; documentos anteriores continuam sem vínculo inferido. Catálogos inativos ou incompatíveis não podem ser usados em novo documento. Operações apenas descrevem o documento e não modificam orçamento/saldo.
- Preferências persistidas no banco por usuário e tela em Cadastros, Notas e Pagamentos: mostrar/ocultar/reordenar colunas, ordenar, salvar filtros atuais, limpar filtros salvos e restaurar padrão. A identificação e as ações essenciais permanecem disponíveis. Notas/pagamentos são ordenados em SQL antes da paginação; cadastros usam a lista completa. Salvar ordenação volta à primeira página. Aba explícita de clientes/fornecedores prevalece sobre filtro de tipo salvo.
- Migração aditiva: duas tabelas novas e oito colunas opcionais nos documentos. Executada duas vezes somente na cópia sintética; registros anteriores preservados.

## Validações

- Backend: 298 testes passaram em 65,03 s; 23 novos casos, incluindo integração MVP e concorrência de preferências. Um aviso preexistente Starlette/httpx.
- Frontend: lint normal sem erros/avisos; lint tipado com 200 avisos preexistentes e zero erros; TypeScript e build passaram. Checks afetados repetidos após correções de navegação/layout, aprovados.
- Revisão independente: backend/frontend sem achados P1/P2; correções finais de navegação/layout revisadas sem pendências.
- Demo/API: nota de 21 dias e pagamento em dinheiro preservaram snapshots após renomear/desativar catálogos; preferências mantidas em nova consulta. Comparação dos registros originais nas 32 tabelas anteriores passou antes/depois do exercício.

- Interface: criação de forma PIX pela tela; nota#8 comcondição14dias/vencimento16/10; preferências nasnotas salvar/recarregar; pagamentos salvar/reset com controles atualizados; filtro salvo de clientes respeitado em /cadastro e prioridade de Fornecedores com aba explícita. Notas/cadastros/pagamentos/configurações mobile375px sem overflow; notasdesktop1265px sem overflow. Screenshots em evidencias/.

## Pendências e limites

Classificação de compra/devolução e Entrada/Saída versus Crédito/Débito permanece dependente da definição da loja. Nenhum novo efeito financeiro foi presumido. Preferências abrangem as três tabelas do escopo; telas legadas não foram migradas. Não houve publicação, commit, push nem migração operacional. PostgreSQL não foi executado; validação em SQLite isolado, Python 3.11 no runtime local de testes (projeto declara 3.14).

## Demo e evidências

Frontend previsto http://localhost:3019, API local 8019; banco descartável /tmp/rotapay-configuracoes-demo-20261002.db. Disponibilidade depende dos processos locais. Login sintético demo@rotapay.local / [credencial demonstrativa omitida do Git]. Evidências neste diretório, scripts restritos à demo; backup local em backups-locais/2026-10-02-configuracoes-tabelas/.

## Próximo sprint, sujeito à confirmação

Sprint 10: melhorar visualização privada de comprovantes (zoom/tela cheia), rastrear autor/origem e distinguir lançamento de transação quando a informação existir; revisar filtros e travas por origem. Políticas de correção, ocultação e gateway ainda dependem da loja. OCR real fica no Sprint 16. Não iniciar sem confirmação.
