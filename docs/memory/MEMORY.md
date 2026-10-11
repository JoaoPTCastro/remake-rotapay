# Memory — índice sempre carregado

Regras de uso em `INSTRUCTIONS.md`. Uma linha por fato, linkando o tópico.
Só entra aqui o que uma sessão futura agradeceria saber antes de começar
(teste: surpresa + gratidão; resto é ruído).

- [Sem crédito automático](no-auto-credit.md) — excedente permanece no PIX.
- [Dinheiro em Numeric](money-numeric.md) — `Numeric(12,2)` + `round(x, 2)`.
- [Código PIX sem race](pix-code-norace.md) — derivado do id pós-flush.
- [Testes nunca tocam pix.db](tests-isolated-db.md) — dependency override + tmp.
- [Rotas públicas fora do proxy](public-routes.md) — `/pagar/*`, `/v/*`, `/api/*`.
- [Lint do frontend](frontend-lint.md) — gates do toolkit, teto 500, adaptado.
- [Seeds com trava](seed-guard.md) — só com `ALLOW_SEED=true`, nunca em prod.
- [Comprovante e jobs](comprovante-jobs.md) — entidade própria + fila; OCR consome jobs.
- [Checkto sem HMAC](checkto-token.md) — webhook valida por token; QR via pix/receive.
- [Sprint D](sprint-d.md) — rate limit, /metricas, k6 e Playwright instalados.
- [WhatsApp via QR](whatsapp-qr.md) — Baileys sem Meta; segredo em .env; caixa de entrada.
- [Revisão multi-agente](review-fixes.md) — falhas corrigidas e riscos aceitos.
- [Fusões de telas](fusoes.md) — Extrato, CadastroTabs, Triagem; deploy Render.
