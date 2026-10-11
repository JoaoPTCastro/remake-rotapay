# Ativação de produção e cadastro — 03/10/2026

**Estado: ativação concluída e validada para testes da loja em produção.** Usuário autorizou produção com pré-aprovação da loja, página comercial na raiz e aplicativo em subdomínio.

## Implementado e validado

- Cadastro público de administrador e loja, com e-mail normalizado, senha forte, bloqueio de duplicidade e limite de tentativas.
- Cada cadastro cria ambiente próprio. Administrador restrito à sua loja; perfil global de consulta. Não concede acesso à organização legada.
- Login escolhe relação ativa com loja; sessões com cookies HttpOnly, Secure e SameSite.
- Página de cadastro, entrada e chamadas comerciais para app.rotapay.site.
- 566 testes locais aprovados, 1 aviso existente. Os 21 testes do cadastro também passaram na imagem Python 3.12 da VPS.
- Lint e TypeScript aprovados; build inicial de 58 rotas aprovado.
- A app → 2.24.108.54, TTL 300 confirmado na hospedagem e DNS autoritativo. Nameservers preservados.
- Caddy atualizado: raiz rotapay.site sempre página comercial; aplicativo no app.rotapay.site, com HTTPS e noindex. Primeiro acesso HTTPS respondeu; validação posterior expirou.
- Produção independente em /srv/rotapay-producao-20261003, projeto rotapay-prod, volume rotapay-prod_dados. API loopback 8130 e web 3130. Segredos novos restritos à VPS.
- Banco inicial vazio; backup inicial conferido, sem importar demonstração ou bancos antigos. Instalações antigas e homologação preservadas.

## Recuperação e validação final

A rota pública de cadastro foi corrigida e validada. Durante o primeiro build remoto, SSH e HTTPS deixaram de responder; causa exata não confirmada. Usuário autorizou continuar após pedido de reinicialização. Hostinger confirmou reinício; serviços legados e novos voltaram. Foram adicionados 2 GiB de swap em /swap-rotapay (permissão 600, fstab) e limite de heap Node de 1024 MiB no build. Build final aprovado e imagem rotapay-prod-web:20261003-v2 ativada.

Verificação HTTPS final: raiz comercial, www redirecionando à raiz, login e cadastro no aplicativo responderam 200; 14 assets conferidos. Cadastro técnico respondeu 200, sessão Secure/HttpOnly, páginas organizações/conta/notas/links acessíveis; logout e novo login aprovados com persistência no banco. A raiz comercial continua comercial mesmo recebendo cookie de sessão.

Conta técnica vinculada apenas à própria organização, perfil global consulta e vínculo admin local. Tentativa de selecionar organização legada respondeu 403. Conta, vínculo e loja técnicos foram inativados após verificação, sem remoção de dados. Não foram criados registros financeiros. Novos usuários criam suas próprias contas; credenciais de demonstração não se aplicam à produção.

Backup inicial verificado e restaurado em /backups/ensaio-pos-reinicio sem montar bancos ativos. Cópia privada local em backups-locais/2026-10-03-producao/backup-inicial.tar.gz. É backup anterior ao cadastro técnico, com banco central inicial vazio. Instalação antiga /srv/pix e volume próprio continuam preservados; nenhuma migração realizada.

Arquivo de reversão do proxy: /etc/caddy/Caddyfile.pre-producao-20261003. Compose com reinício automático; jamais apagar volumes para reverter. Próxima ação: loja criar conta real e testar cadastro de fornecedores, cobranças e acertos. Recuperação de senha, validação de e-mail e integração bancária exigem continuidade própria.

## Limites do MVP

Integração bancária Checkto não habilitada para novas lojas; confirmação automática não prometida. Verificação de e-mail e recuperação autônoma de senha ainda pendentes. Falha de provisionamento reserva cadastro inativo para suporte, evitando reutilização insegura de ID. Limites de algumas rotas antigas ainda usam IP compartilhado do serviço web. Backup periódico específico do produto ainda não configurado; hospedagem apresenta backup semanal. Nenhum commit/push realizado.
