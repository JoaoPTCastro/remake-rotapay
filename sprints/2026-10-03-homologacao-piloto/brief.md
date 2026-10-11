# Sprint 17 — homologação local e preparação do piloto

Autorizado em 03/10/2026 por “ok faça esse”, após relatório e proposta do Sprint16.

## Escopo autorizado

Homologar em Python3.14/SQLite e stack atual os dois trajetos de pagamento, abatimento parcial, sobra sem crédito automático, crédito explícito, acerto misto, estorno, fornecedor e revogação. Ensaio de backup/restauração com controle, bancos de todas as lojas prontas e arquivos, em destino novo, verificando valores, vínculos, declarações e downloads após recuperação. Roteiro operacional, matriz de aceite e plano de recuperação.

## Responsabilidades e dependências

- Backup: scripts/backup_rotapay.py e tests/test_backup_rotapay.py. Sem edição de app/frontend. Depende do contrato SQLite/arquivos atual.
- Homologação: tests/test_homologacao_piloto.py e evidência matriz.json. Depende da API/contratos existentes; sem editar app ou outros testes.
- Coordenação: sprints/*, revisão somente leitura, cópias sintéticas e validação integrada. Correção de fonte somente se houver falha concreta.

Método fullstack-developer do workspace. Arquivos disjuntos, sem commit delegado ou autorizado. Backup offline exige interrupção das escritas; consistência entre bancos não será presumida em cópia concorrente. Nenhum destino existente será sobrescrito.

## Aceite desta entrega local

Cenários conferidos e evidências reproduzíveis; arquivos e relações recuperados em diretório novo; origem sintética preservada; adulteração/caminhos indevidos rejeitados; roteiro para loja com pendências explícitas. Sem promessa de banco PostgreSQL, carga ou usabilidade visual não ensaiados.

## Aceite externo separado

Comparação com planilha/controle da loja, escolha final de implantação, aceite do responsável e piloto real dependem do material e autorização correspondentes. Não declarar esse aceite concluído nem iniciar Sprint18 por aprovação de desenvolvimento. Sem Checkto/OCR, banco operacional, mensagens, publicação, deploy, commit ou push. Bloqueio anterior do navegador respeitado; HTTP/SSR é a verificação disponível.
