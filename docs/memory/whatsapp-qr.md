---
name: whatsapp-qr
description: WhatsApp pareado por QR (Baileys); fotos caem na caixa de entrada
metadata:
  type: architecture
---
`wa-gateway/` (Baileys, porta 3101, sessão em `wa-gateway/data/` — volume no
compose). Segredo compartilhado `WA_SHARED_SECRET` no `.env` (nunca default em
prod). Fotos -> `POST /integracao/whatsapp/anexo` -> comprovante sem vínculo ->
`/caixa-entrada` cria a mov. Não-oficial: usar número exclusivo da loja;
se cair, parear de novo em `/whatsapp`.
