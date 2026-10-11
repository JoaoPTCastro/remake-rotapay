# Sprint 12 — Extrato compartilhado com escopo

Concluído localmente em 02/10/2026. Autorização: “ta certo, pode seguir para o sprint 12”; escopo confirmado: “Sim, use essa proposta”.

## Entrega

Admin/financeiro pode gerar acesso para o próprio cliente ou fornecedor do extrato selecionado. O cadastro e a relação ficam congelados. A interface usa validade de 7 dias, informa o escopo e exige confirmação. A lista apresenta autor, criação, validade e situação; permite revogar com motivo, sem apagar documentos financeiros.

O destinatário consulta somente valores e situações de notas/pagamentos, com totais e paginação. Não há comprovantes, dados bancários, contatos, observações privadas, identificadores internos ou links para telas internas. O acesso é somente leitura. Quem possuir o link pode consultar esse escopo: o nome do destinatário não representa verificação de identidade.

Token aleatório de 32 bytes, retornado uma única vez; apenas SHA-256 fica persistido. O link usa `/e#token`; o cliente envia o segredo por header ao proxy, que não repassa cookies/JWT internos. Expiração, revogação, desativação do cadastro ou perda do perfil autorizado do emissor bloqueiam novas consultas. Gestão exige autorização real do backend, independentemente do cookie de perfil.

Foi corrigida na revisão a compatibilidade entre relação cliente e o tipo legado `representante`; a classificação existente permanece preservada. Nenhuma regra de saldo, crédito ou abatimento foi alterada.

## Validação e evidências

- Suíte completa: **396 testes aprovados**, Python 3.14.0; um aviso preexistente de Starlette/httpx. Inclui 38 casos novos, isolamento A/B, relações, permissões, expiração/revogação, tentativas de troca de cadastro e ausência de segredos/dados privados.
- Frontend: lint sem erros/avisos; TypeScript aprovado; lint de tipos sem erros e 200 avisos preexistentes; build Next 16.3.8 aprovado, 50 páginas.
- Ensaio HTTP real na cópia sintética: API e proxy sem sessão interna, rejeição de JWT/troca de cadastro/escrita, bloqueio após revogação e headers de privacidade. Link de teste revogado ao terminar.
- HTML autenticado: admin vê gestão; consulta não vê, mesmo com cookie de perfil oposto. Nenhum JWT exposto no HTML.
- Preservação: registros e colunas anteriores de **34 tabelas** conferidos antes/depois; leitura pública não modifica tabelas. Nova tabela de compartilhamentos e novos eventos de auditoria são aditivos.
- Revisão final sem achados P1/P2 pendentes. Logs e scripts estão em [evidencias](evidencias/).

## Limites e continuidade

Não foi realizada conferência visual interativa/mobile. A automação do navegador havia rejeitado o acesso por política de URL/protocolo; esse bloqueio foi respeitado, sem usar superfície alternativa. HTTP/HTML não comprova comportamento visual ou clipboard no navegador.

Sem ensaio PostgreSQL neste sprint. Limitador público atual é por IP/processo; o proxy compartilha o IP do servidor no backend. Antes de publicação, ajustar política de IP confiável e limitação distribuída conforme infraestrutura. Revogação impede novas consultas; não apaga dados já vistos nem cancela retroativamente resposta em andamento.

O backend admite validade inteira de 1 a 30 dias; a interface e o escopo entregue usam 7. Nenhum link foi enviado a terceiros. Sem commit, push, deploy, publicação ou migração operacional.

Demo: [extratos](http://localhost:3022/extratos), API local 8022. SQLite `/tmp/rotapay-extrato-compartilhado-demo-20261002.db`, uploads `/tmp/rotapay-extrato-compartilhado-demo-uploads`. Dados sintéticos e processos temporários. Admin `demo@rotapay.local` / `[credencial demonstrativa omitida do Git]`; consulta `consulta.s11@rotapay.local` / `RotaPay-consulta-2026`.

Próximo: **Sprint 13**, inventário/classificação do legado por evidência, pendências explícitas e ensaio idempotente em cópia com comparação de saldos. Sem inferir quitação/crédito histórico ou executar migração operacional. Aguarda confirmação do usuário; dados reais e decisão de coexistência/transição continuam dependências.

Base técnica: fragmentos são tratados pelo cliente conforme [RFC 3986, seção 3.5](https://www.rfc-editor.org/rfc/rfc3986#section-3.5); proteção de respostas e validação de acesso seguem como referência [OWASP REST Security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html). Essas referências não substituem as verificações do código e os limites acima.
