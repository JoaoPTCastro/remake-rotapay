# Deploy em produção (VPS Ubuntu + Docker)

Procedimento histórico de VPS. Para a versão multiempresa, leia primeiro [preparação de ativação](../sprints/2026-10-03-preparacao-ativacao/plano-ativacao.md). Não execute migração/publicação sem autorização específica.

## 0. Pré-requisitos (uma vez)
- VPS Ubuntu 22/24 com Docker (imagem Docker da Hostinger já vem pronto).
- Domínio com registro **A** apontando para o IP da VPS (propaga em minutos).
- Acesso SSH (root ou sudo).

## 1. Na VPS (primeira vez)
```bash
# firewall: só SSH, HTTP e HTTPS
ufw allow 22 && ufw allow 80 && ufw allow 443 && ufw --force enable

# código
mkdir -p /srv && cd /srv
git clone https://github.com/cl1ck1/rotapay.git pix && cd pix

# segredos (GERADOS na hora, nunca commitados)
openssl rand -hex 32  # -> SECRET_KEY
openssl rand -hex 16  # -> SETUP_TOKEN (descartável, apague após o seed)
cat > .env <<EOF
SECRET_KEY=<cole o 1º>
SETUP_TOKEN=<cole o 2º>
DOMAIN=seudominio.com
EOF

# sobe tudo (build demora alguns minutos na 1ª vez)
docker compose -f docker-compose.prod.yml up -d --build

# acompanha o HTTPS (Caddy emite o certificado sozinho)
docker compose -f docker-compose.prod.yml logs -f caddy
```

## 2. Primeiro acesso (uma vez)
```bash
# cria o admin (exige o SETUP_TOKEN do .env)
curl -X POST http://localhost:8000/auth/seed-admin \
  -H "Content-Type: application/json" \
  -d '{"setup_token":"<SETUP_TOKEN>"}'
# apague o SETUP_TOKEN do .env depois (endpoint trava sozinho após o 1º uso;
# sem ele no .env, os ups seguintes funcionam normal)
```
Entre em `https://seudominio.com/login` com `admin@local` / `admin123` e **troque a senha** em Conta.

## 3. Atualizar (cada release)
```bash
cd /srv/pix && git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```
O banco fica no volume `pixdata` — **deploy não zera nada**.

## 4. Backup e retorno multiempresa

Não usar cópia compactada do volume com a API escrevendo. O banco central, os bancos de todas as lojas e os anexos precisam de um ponto de parada comum. O Docker agora persiste `/data/pix.db`, `/data/ambientes` e `/data/uploads` no volume `pixdata`.

O script `scripts/backup_rotapay.py` está incluído na imagem da API. O procedimento completo exige parar todos os escritores, criar e verificar o pacote, restaurar em destino novo e conferir saldos/anexos antes da troca. Consulte o [plano de ativação e retorno](../sprints/2026-10-03-preparacao-ativacao/plano-ativacao.md). Não apagar volumes com `down -v`. A restauração prepara uma cópia; não substitui automaticamente o ambiente operacional.

## 6. Caso desta VPS (Hostinger, 2.24.108.54)
- O Caddy **do host** já ocupava a porta 80 (placeholder). Em vez de brigar por ela:
  - backup em `/etc/caddy/Caddyfile.bak`; bloco `:80` atual = `reverse_proxy 127.0.0.1:3000`;
  - stack sobe com override local `/srv/pix/docker-compose.ip.yml` (publica api/web só em localhost; o serviço `caddy` do compose **não** é usado aqui).
- Sem domínio: acesso por `http://2.24.108.54`. Com domínio: aponte o DNS, troque o bloco do host para o domínio (HTTPS automático) e ajuste `DOMAIN=` no `.env`.
- `openclaw_mateus` estava em crash-loop **antes** da nossa chegada — não mexemos nele.

## 7. Problemas comuns
- `site não abre`: confira o DNS (`dig +short seudominio.com`) e `docker ps`.
- `certificado pendente`: Caddy precisa da porta 80 livre e DNS propagado; veja os logs.
- `Credenciais inválidas` do nada: banco é persistente aqui — só acontece se alguém apagou o volume. Restaure o backup.
