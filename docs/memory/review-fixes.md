---
name: review-fixes
description: Revisão multi-agente — o que foi corrigido e o que foi aceito com motivo
metadata:
  type: feedback
---
CORRIGIDO: estorno revertia valor cheio com tolerância (reverte só consumido);
webhook exigia transaction.id (idempotência furada); SECRET_KEY fail-closed em
prod; lock anti double-spend + tolerância (processo único; FOR UPDATE no PG
futuro); seed-admin/WA travados sem segredo; upload com nome único por hash;
rate limit nas rotas de dinheiro; /api/wa com auth; link absoluto via origin;
download via proxy autenticado; revalidação do dashboard; hydration do rail;
a>button virou .btn; PessoaForm único; a11y base (labels, alert, teclado).
ACEITO COM MOTIVO: chave-pix pública enumerável (chave PIX é pública por
natureza — é feita para distribuir); secundárias no mobile via Gerenciar
(menu definido pelo time); valor fixo burlável no devtools (PIX manual não
tem como travar — diferença aparece na conciliação); CORS * (fechar no deploy
prod com domínio fixo).
