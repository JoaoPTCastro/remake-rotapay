# Sprint 16 — portal do fornecedor e vínculos por loja

Autorizado em 03/10/2026: “ok siga”, após proposta do Sprint 15B.

## Entregas e aceite

Vincular explicitamente a identidade do fornecedor ao cadastro financeiro local de cada loja, sem interpretar a FK central legada como cadastro de outro banco. Portal restrito às relações próprias, pagamentos recebidos, notas/saldos e chaves PIX. Registrar declaração humana de recebimento com autoria e referência, sem confirmação bancária, abatimento ou crédito automático. Administração de membros por loja com revogação local e proteção do último administrador e das credenciais compartilhadas.

Testar IDs coincidentes, dados de outro fornecedor/loja, revogação, chaves principais, concorrência, registros de recebimento e preservação financeira. Validar frontend, HTTP/SSR e inicialização em cópia sintética. Atualizar continuidade e relatório.

## Responsabilidades

- Backend: app/*, modelos, autorização, serviços e endpoints. Depende da base 15B.
- Frontend: frontend/*, portal, formulários e administração. Depende do contrato da API.
- Testes/revisão: tests/* e revisão de segurança somente leitura. Depende do contrato e implementação.
- Coordenação: sprints/*, cópias sintéticas, validação integrada e continuidade.

Arquivos disjuntos; fontes preservadas. Nenhum commit delegado ou autorizado. Método fullstack-developer do workspace, respeitando stack e identidade local.

## Limites

Sem banco operacional, Checkto, OCR, mensagens, publicação, deploy, commit ou push. Bloqueio anterior do navegador respeitado: validação HTTP/SSR sem declarar ensaio visual. PostgreSQL e operação real permanecem para homologação.
