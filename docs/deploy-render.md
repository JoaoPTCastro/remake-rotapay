# Deploy no Render — passo a passo (sem domínio próprio)

> **Quanto custa?** Grátis para demonstração, **~US$ 7,25/mês para piloto real**.
> Por quê: o plano grátis apaga o banco e os comprovantes a cada reinício
> (sistema de arquivos efêmero) e o Postgres grátis expira em 30 dias.
> Para colaboradores testarem de verdade, o mínimo é: API Starter (US$ 7)
> + disco 1 GB (US$ 0,25). O painel web pode ficar no grátis (não guarda nada).

## 1. Subir o código para o GitHub
1. Crie um repositório privado no GitHub.
2. Na pasta do projeto:
   ```bash
   git init && git add -A && git commit -m "MVP painel PIX"
   git remote add origin <url-do-repo> && git push -u origin main
   ```
3. Confirme que `.env` **não** foi junto: `git show --name-only | grep -c "^\.env$"` deve dar `0`.
   (`.gitignore` já barra `.env`, `pix.db` e `uploads/`.)

## 2. Criar via Blueprint
1. https://dashboard.render.com → New → Blueprint → conecte o repo.
2. O `render.yaml` cria `pix-api` + `pix-painel` + disco `pixdata`.
3. Em `pix-api` → Environment, confira/adicione:
   - `ENV=prod` (trava seed-admin e exige SECRET_KEY)
   - `SECRET_KEY` (gerada sozinha; se vazia, gere)
   - `WA_SHARED_SECRET` (invente uma frase longa)
   - `CHECKTO_PUBLIC_KEY` / `CHECKTO_SECRET_KEY` (as mesmas do `.env` local)
   - `CHECKTO_CALLBACK_URL=https://<sua-api>.onrender.com/webhooks/checkto`
4. Deploy. Aguarde os dois ficarem "Live".

## 3. Ligar painel → API
1. Copie a URL pública da `pix-api` (ex.: `https://pix-api-xyz.onrender.com`).
2. Em `pix-painel` → Environment → `API_URL` = essa URL → Save (redeploy automático).
3. Abra a URL do painel → `/login`.

## 4. Primeiro acesso em produção
1. Em `pix-api` → Environment, adicione `SETUP_TOKEN` com uma frase secreta
   (ex.: `loja-2026-trocar`) → Save (redeploy).
2. Crie o admin **uma única vez**:
   ```bash
   curl -X POST https://<sua-api>.onrender.com/auth/seed-admin \
     -H 'Content-Type: application/json' \
     -d '{"setup_token":"loja-2026-trocar"}'
   ```
   Depois disso o endpoint trava sozinho (409). Apague o `SETUP_TOKEN` do
   ambiente para encerrar a janela.
3. Entre com `admin@local` / `admin123` e cadastre tudo (base começa zerada).

## 5. Limites e modos de uso
- **Modo demonstração (grátis):** suba sem o disco (remova o bloco `disk` do
  `render.yaml`) — funciona, mas **zera tudo** a cada deploy/reinício. Bom só
  para mostrar telas.
- **Modo piloto (~US$ 7,25/mês):** API Starter + disco 1 GB + painel free.
  Dados persistem; backup = exportar CSVs (já auditado).
- wa-gateway (WhatsApp) **não** vai para o Render (sessão efêmera) — mantenha
  numa máquina da loja ou VPS.

## 6. Domínio próprio (futuro)
Render → pix-painel → Settings → Custom Domain → aponte o DNS. Nada muda no código.
