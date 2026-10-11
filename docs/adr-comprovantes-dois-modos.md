# ADR — Dois modos de comprovante: manual e gateway

**Data:** 08/09/2026 · **Estado:** aceito

## Contexto

A loja recebe comprovantes hoje (foto via WhatsApp/arquivo). Com a fintech,
o pagamento acontece no checkout e o comprovante nasce automático. Os dois
mundos precisam cair no mesmo banco da loja.

## Decisão

**Um só modelo (`Comprovante`), três origens:**

| Modo | Origem | Como entra | Leitura | Revisão |
|---|---|---|---|---|
| Manual | `upload` | arrastar/soltar no detalhe do PIX | OCR stub → revisão com edição | obrigatória (aceitar/rejeitar) |
| WhatsApp | `whatsapp` | webhook futuro (número exclusivo) | mesma da manual | obrigatória |
| Gateway | `gateway` | webhook da fintech no pagamento | não precisa — dado oficial | dispensada (etapa já `registrado`) |

Regras que valem nos três modos: comprovante nunca concilia sozinho;
duplicado (hash/`pix_id`) é recusado; tudo é auditado.

## Contrato do webhook (`POST /webhooks/checkto` — Checkto real)

Validado contra `https://checkto.com.br/llms.txt`: **não há HMAC** — a
Checkto envia `token` no corpo; comparamos com o `webhookToken` guardado ao
criar a cobrança (ou `CHECKTO_WEBHOOK_TOKEN` do painel). `transaction.identifier`
= `link-{token}` liga o pagamento à chave da loja; `transaction.id` garante
idempotência. Só `TRANSACTION_PAID` + `COMPLETED` registra. Sempre 2XX.

## Cobrança (`POST /links/{id}/cobrar`)

Cria PIX na Checkto (`/gateway/pix/receive`, valores em reais, `callbackUrl`
fixa em `CHECKTO_CALLBACK_URL`) e guarda QR + token no link. Exige valor fixo
e vendedor com nome/email/telefone/documento. `/v/{token}` exibe o QR.

## Consequências

- WhatsApp vira funcionalidade futura opcional, não pré-requisito.
- OCR real pluga em `ocr.extrair()` sem mudar contrato.
- Conciliação automática continua proibida (decisão de produto).
