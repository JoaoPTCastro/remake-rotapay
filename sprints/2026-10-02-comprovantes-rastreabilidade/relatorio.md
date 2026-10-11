# Sprint 10 — comprovantes e rastreabilidade

Data: 02/10/2026. Autorização: “continue”. Estado: concluído e validado localmente. Somente ambiente local.

## Entregas

- Origem do registro derivada do servidor (Manual nos novos pagamentos; Não informada nos anteriores). Autor real por ID/nome do usuário autenticado, horários de registro/atualização em UTC explícito. Sem inferir origem, hora ou participantes antigos.
- Data/hora da transação opcional e declarada, com fuso obrigatório, coerência com a data do pagamento no calendário São Paulo e rejeição de horário futuro. Remetente, favorecido e intermediador opcionais, sem validação bancária presumida. Metadados fazem parte da identidade da tentativa idempotente: replay diferente é recusado.
- Filtros de valor mínimo/máximo e origem aplicados em SQL antes da paginação, inclusive nas preferências por usuário. Atualização da consulta. Saldos por relação permanecem independentes; um PIX direto continua sendo um único evento.
- Arquivos continuam privados e autenticados. Preview somente PDF/PNG/JPEG/WebP reconhecido por assinatura, com caminho contido na raiz e cabeçalhos no-store/nosniff/CSP. Download original preservado. Ocultação é desativação lógica; pagamento, saldos e histórico permanecem.
- Visualizador de imagens com zoom e fechamento/restauração do foco. PDF nativo não renderizou no navegador do aplicativo; implementação final utiliza PDF.js em canvas, controles de páginas/zoom e worker local versionado, sem executar ações/forms/scripts do PDF. Tela cheia nativa indisponível nesse navegador recebe fallback que ocupa a janela.

## Validações

- Backend canônico: **323 testes passaram em 76,35 s**, incluindo 24 novos cenários e uma integração MVP. Um aviso preexistente Starlette/httpx.
- Frontend final: lint normal zero avisos/erros, tipado200avisos preexistentes e zeroerros, TypeScript e build Next16.3.8 aprovados após correções. Apenas o worker gerado de terceiros em public/pdfjs/** é excluído do lint; fontes da aplicação continuam verificadas. Worker validado por versão exata e comparação com a dependência instalada.
- API demo: novo pagamento diretoPIX25 manual comautor/datetimeUTC; replay idêntico sem duplicação, diferente409; filtros exatos; PNG/PDFinline privados; ocultação de terceiro anexo manteve orçamentos e arquivo ocultado404.
- Migração aditiva de5colunas opcionais repetida duas vezes na cópia sintética. Comparação dos registros anteriores nas34tabelas existentes aprovada; nenhuma atualização operacional.
- Revisão independente final de segurança/backend/frontend/renderizador e configuração de lint: semP1/P2 pendentes.

- Visualização final: imagemPNG/zoom125%, PDF de duas páginas renderizado em canvas, próxima/anterior/zoom125%, fullscreen fallback1280×1000 e mobile390×1024, Escape fecha e devolve foco. Mobile conteúdo375px/viewport375px sem overflow; screenshot do PDF mostra conteúdo efetivo. Nativefullscreen não permitido pelo navegador do aplicativo; expansão da própria janela funciona.
- Formulário: pagamento#5 emdinheiro20 criado comhora09:00/fuso-03/remetente/favorecido/intermediador; detalhe confirma12:00UTC e autor do servidor. Filtro manual25–25 retorna apenas#4; Atualizar consulta preserva filtro.
- Proxy real da demo: PDFinline/download bytes iguais ao arquivo original; semsessão401, modoinválido400, anexoocultado404. Evidência proxy-demo.json.
- PDFcanvas é visualização raster da página, sem camada de seleção de texto; máximo500páginas/4096px por dimensão/8milhões pixels por página. PDFs não renderizáveis continuam com download privado original. Nenhum OCR.

## Dependências e fontes

PDF.js6.3.289 fixado no projeto; consulta às [instruções e exemplos oficiais](https://mozilla.github.io/pdf.js/examples/) e [releases oficiais](https://github.com/mozilla/pdf.js/releases). Npm audit identificou correção patch para Next16.3.4 no [aviso oficial](https://github.com/advisories/GHSA-vcvr-r3jv-pc5j); atualização local para16.3.8 concluída. Npm audit --omit=dev final: zero vulnerabilidades reportadas. Auditoria completa ainda indica uma dependência de desenvolvimento preexistente (brace-expansion), fora do runtime de produção. O aplicativo não usa next/og/ImageResponse no código inspecionado.

## Pendências e limites

Políticas de gateway, correções e contestação continuam dependendo da loja. Nenhum gateway foi exposto para edição, nem houve importação do legado, OCR, envio externo, confirmação bancária ou migração operacional. Textos de participantes são declarações do operador; definições finais com a loja permanecem pendentes. SQLite/Python3.11 no runtime local; PostgreSQL/Python3.14 não executados.

## Demo e continuidade

Frontend3020/API8020, banco /tmp/rotapay-comprovantes-demo-20261002.db e uploads separados. Login sintético demo@rotapay.local / [credencial demonstrativa omitida do Git]. Disponibilidade depende dos processos locais. Evidências e scripts neste diretório; backup em backups-locais/2026-10-02-comprovantes-rastreabilidade/. Sem commit, push ou publicação.

Próximo proposto: Sprint11, perfil/empresa/usuários e permissões por ação. Revisar a matriz existente, aplicar controles no backend e na interface e preservar os acessos necessários. Começar somente após confirmação.
