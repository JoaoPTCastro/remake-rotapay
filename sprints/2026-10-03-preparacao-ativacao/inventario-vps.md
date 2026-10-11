# Inventário remoto — leitura apenas

03/10/2026. Usuário confirmou usar o mesmo acesso anterior. SSH por chave e host conhecido funcionou como root em 2.24.108.54. Nenhuma credencial registrada neste documento.

- Linux; raiz 48 GB, 20 GB usados, 28 GB livres (43%).
- Docker 29.4.3; Compose v5.1.3.
- API `pix-api-1` / imagem `pix-api`, painel `pix-web-1` / imagem `pix-web`: ativos há duas semanas.
- Portas da aplicação restritas a loopback: 8000 e 3000.
- Volume real da API: `pix_pixdata`, montado em `/data`.
- Python da API: 3.12.14.
- Central configurada em `sqlite:////data/pix.db`; arquivo existe. UPLOAD_DIR=/data/uploads, diretório ausente. Isso não prova perda de anexos: inventário de referências e caminhos antigos ainda necessário.
- TENANT_DATABASE_DIR não definido; diretórios /data/ambientes e /srv/ambientes-locais ausentes no container observado. Não foi consultado conteúdo financeiro nem cadastro central para concluir quantas lojas existem.
- Caddy do host ativo. Domínio/configuração e HTTPS ainda não conferidos.
- `/srv/pix` contém três arquivos Compose, mas não é repositório Git: procedimento antigo `git pull` não se aplica diretamente.
- Outros serviços OpenClaw existentes; um em reinício contínuo. Não alterados e fora do escopo.

## Próxima etapa

Preparar candidato em ambiente separado, sem reutilizar projeto/volume/portas operacionais. Conferir Compose e imagem com Python real, repetir cenários sintéticos, backup e recuperação. Registrar a origem da versão atual antes de planejar promoção. Conferir domínio e referências de anexos antes da janela. Nenhum build, upload de candidato, reinício, migração ou publicação executado nesta etapa.
