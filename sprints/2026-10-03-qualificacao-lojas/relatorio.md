# Sprint — qualificação de lojas

## Entrega

O cadastro público agora é um formulário de avaliação. Ele coleta contato, localização, segmento, tamanho da equipe, volume mensal de pagamentos por PIX, quantidade de fornecedores, modelo de venda, controle atual e principal desafio. O envio grava uma solicitação na base central `interesse_lojas`, com consentimento e status inicial `novo`.

O formulário não cria conta, não pede senha e não dispara verificação de e-mail. A análise é manual pela equipe. O cadastro direto da API foi desativado no ambiente de produção (`REGISTER_PUBLIC_ENABLED=false`) para impedir que essa etapa seja contornada.

## Publicação e validação

- `https://rotapay.site/` respondeu 200.
- `https://app.rotapay.site/cadastro-loja` respondeu 200.
- Envio real de validação pelo formulário respondeu 201 com confirmação de recebimento. O registro técnico foi marcado como `teste` na base.
- API de produção respondeu 200 no healthcheck.
- Tentativa de cadastro direto respondeu 403.
- Lint e TypeScript do frontend passaram.
- Testes focados de cadastro e MVP: 51 passaram.

## Demonstração

O ambiente sintético foi religado e o login administrativo foi validado:

- URL interna atual: `http://127.0.0.1:3128/login`
- E-mail: `demo@rotapay.local`
- Senha: `[credencial demonstrativa omitida do Git]`

Usuário fornecedor sintético disponível no mesmo ambiente:

- E-mail: `fornecedor.s15@rotapay.local`
- Senha: `[credencial demonstrativa omitida do Git]`

O host `demo.rotapay.site` já foi preparado no Caddy para apontar ao ambiente sintético. Registro DNS criado em 04/10/2026 e configuração ativa do Caddy conferida. Acesso público: `https://demo.rotapay.site/login`, com HTTPS e os dois perfis validados.

## Próxima pendência

Revisar o fluxo manual de triagem das solicitações recebidas. DNS e HTTPS da demo concluídos em 04/10/2026.
