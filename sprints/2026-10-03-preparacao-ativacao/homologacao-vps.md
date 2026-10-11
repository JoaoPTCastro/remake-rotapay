# Homologação do candidato na VPS existente

03/10/2026, autorizada pela confirmação “ok” após o inventário. Preparação técnica concluída; Sprint 18 operacional permanece aberto.

## Resultado

Construídas imagens próprias `rotapay-s18-api:homologacao` e `rotapay-s18-web:homologacao` na VPS. A API passou nos 545 testes em 422,61 s no Python 3.12 da imagem, com um aviso preexistente Starlette/httpx. O painel concluiu build e TypeScript na imagem Node22. Configuração Compose validada. Identificadores das imagens e dependências efetivamente instaladas registrados em evidencias/.

Candidato empacotado com lista/hash de 346 arquivos e hash do pacote; excluídos segredos, bancos operacionais, uploads reais e dependências locais. Pacote apenas com fontes, testes e ativos. Sem commit/push; o hash identifica este checkout local, não uma revisão publicada.

Backup do Sprint17 exclusivamente sintético transferido e restaurado via ferramenta da imagem em volume independente: central + lojas2/3, sete anexos/logos, dez arquivos no manifesto. Primeira compactação incluiu metadados Apple e foi rejeitada corretamente; pacote refeito em USTAR sem esses extras e verificado. Uma primeira tentativa usou caminho de destino diferente do caminho da aplicação e foi igualmente rejeitada antes de criar dados por causa dos arquivos extras. A restauração final usa `/data/ambiente`, também configurado na API: referências permanecem válidas dentro do container.

## Ambiente separado

Pasta `/srv/rotapay-homologacao-s18`; projeto Compose `rotapay-s18`; volume `rotapay-s18_dados_sinteticos`; rede independente. API em `127.0.0.1:8128`; painel em `127.0.0.1:3128`. Sem encaminhamento público pelo Caddy, sem portas externas. Segredo exclusivo gerado no servidor, arquivo privado .env, não copiado para evidências. Ambiente deixado ativo para continuidade.

Configuração local reproduzível em compose.homologacao.yml. O volume foi criado previamente para restauração e declarado explicitamente externo à gestão Compose; não utilizar volume da operação neste projeto. Sintéticos podem receber logs de acesso; verificar pacote imutável, não hash de banco ativo.

## Conferência HTTP

Login de administrador e fornecedor 200, organizações 200; portal do fornecedor nas lojas2/3 200; financeiro global do fornecedor 403; login do painel200 e páginas protegidas /organizacoes e /conta307 sem autenticação. Smoke HTTP não equivale à revisão visual nem ao aceite integral dos fluxos financeiros. A suíte completa cobre os cenários de aplicação, mas não comprova capacidade de carga.

## Preservação e limites

Containers operacionais pix-api-1/pix-web-1 continuam ativos há duas semanas nas mesmas portas; não houve reinício ou troca de volume/imagem operacional. Outros serviços intocados. Espaço após build: 24GB livres (50% usados). Imagens/cache de homologação consomem disco, sem remoção de imagens anteriores.

Sem publicação por domínio, migração financeira, banco operacional, integração Checkto ou seed real. Pendentes: aceite/visual/celular da loja; domínio/HTTPS; inventário de referências de anexos antigos e revisão da origem da versão instalada; política de correção/onboarding; reconciliação dos dados e janela/responsáveis; aprovação específica de promoção. Backups externos e retorno operacional ainda devem ser ensaiados com os dados reais em janela autorizada.

## Próximo passo

Encerrar o aceite do piloto com a loja e resolver inventário/reconciliação antes de apresentar uma proposta concreta de ativação. Sprint18 não deve ser anunciado como implantação concluída; nenhum próximo sprint iniciado automaticamente.
