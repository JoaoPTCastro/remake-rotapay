# Remoção dos módulos WhatsApp e caixa de entrada

Escopo autorizado e executado: navegação, telas e redirecionamentos da caixa/triagem/revisão, componentes de pareamento, proxy web, gateway, serviço Compose e endpoints exclusivos desses módulos. A rota de leitura dos documentos foi separada em `app/routers/comprovantes.py` para preservar arquivos históricos e seus limites de acesso. Registros e arquivos existentes não foram apagados.

Validação local: lint, TypeScript e 38 testes de MVP, dashboard e OCR legado aprovados. O teste de regressão confirma 404 nas rotas removidas. Documentação operacional atualizada.

Publicação concluída na produção e na demonstração, usando imagens sem-whatsapp-20261004. Site principal, login e healthcheck da produção responderam 200. Login da demo validado; menu autenticado não contém os módulos retirados. Telas /whatsapp, /triagem, /caixa-entrada e /revisao e proxy /api/wa responderam 404 na sessão autenticada da demo. Endpoints /caixa-entrada e /integracao/whatsapp/anexo responderam 404 na API de produção. Compose de ambos os ambientes preservado em backup para reversão. Nenhum gateway WhatsApp estava ativo na VPS. Mudanças desta etapa ainda sem commit/push.
