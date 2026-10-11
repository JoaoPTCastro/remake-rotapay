# Relatório de Reunião + Alinhamento Funcional — RotaPay

**Data:** 08/09/2026
**Participantes:** João Pedro Castro, Luiz Henrique, Matheus Emanuel
**Objetivo:** apresentar todas as funcionalidades do aplicativo para aprovação do time antes de reordenar os itens do menu principal
**Status do ambiente:** painel em http://localhost:3000 · login `admin@local` / `admin123` · base com 901 PIX (R$ 898.761,88, fiel à planilha)

---

## 1. Visão geral

Sistema web de controle financeiro de PIX atravessados (cadeia cliente → vendedor/rifeiro → loja → fornecedor → fabricante). Responde às 5 perguntas do PRD: o que entrou, de quem veio, para quem vai, qual obrigação quita, quanto falta.

Stack: Next.js 16 (painel) → FastAPI (API) → SQLite (migração Postgres prevista).

---

## 2. Inventário de funcionalidades por tela

### 2.1 Início — Dashboard (`/`)
- Cards: total a pagar, PIX disponível, PIX pendentes, PIX conciliados, projeções abertas
- Tabela de saldo em aberto por fornecedor + exportação da posição em CSV
- Checklist "Primeiros passos" (some sozinho quando completo; ocultável)
- Status: ✅ pronto

### 2.2 PIX + Controle — Extrato único (`/movimentacoes`, `/controle`)
- Registro de PIX em <30s: data, valor, remetente, representante, destinatário, fornecedor, autor, forma, natureza, observação
- **Controle** reproduz a planilha: cliente, data, valor, autor, remetente, fornecedor destino, forma, natureza e ☑/☐/◐ de conciliação com botão Conciliar por linha
- Busca por código/remetente; filtros por período, status e pessoas; paginação
- Detalhe com anexo/download de comprovante (PDF/PNG/JPG, 10 MB) e cancelamento lógico (conciliada nunca some — exige estorno)
- Exportação CSV respeitando os filtros da tela
- Status: ✅ pronto

### 2.3 Conciliar (`/conciliacoes`: selects reais + criar débito/projeção inline) + Triagem (`/triagem`: caixa + revisão OCR)
- Liga PIX → débito ou projeção, com conciliação parcial (saldo restante automático)
- Excedente nunca vira crédito silencioso: fica no PIX; acima da tolerância é recusado
- Estorno com motivo, preservando o histórico
- Status: ✅ pronto

### 2.4 Links — Links do vendedor (`/links`)
- A loja gera link individual (vendedor + chave do fornecedor + valor fixo opcional) e envia ao vendedor
- Copiar URL, revogar sem apagar histórico; só fornecedor com chave cadastrada entra na lista
- Status: ✅ pronto

### 2.5 Projeções (`/projecoes`)
- Uma projeção aberta por Representante + Fornecedor; saldo calculado pelo sistema
- **Simulador**: quanto o rifeiro pode pagar sem exceder (considera tolerância) — sem persistir nada
- Exportação CSV
- Status: ✅ pronto

### 2.6 Lançamentos — Débitos/Créditos (`/lancamentos`)
- Débito, crédito, despesa, imposto, salário, desconto, pagamento, perda — com saldo em aberto e cancelamento
- Crédito por tolerância gerado explicitamente e auditado
- Status: ✅ pronto (tela dedicada de "Compras por fornecedor" ainda não existe — ver §4)

### 2.7 Chaves PIX (`/chaves`)
- Todas as chaves que a loja gerencia: chave, banco, conta, titular, prazo, tolerância
- Copiar chave, abrir página de pagamento; alerta "sem chave"
- Status: ✅ pronto

### 2.8 Cadastro com abas (`/cadastro`: fornecedores|pessoas|chaves; `/pessoas` e `/chaves` são a mesma tela)
- Representantes (cliente/rifeiro/autores) e fornecedores: documento, contato, endereço, apelido, chave PIX + dados, prazo, tolerância de crédito
- Status: ✅ pronto

### 2.9 Histórico (`/historico`, só admin/financeiro)
- Quem fez o quê e quando em todas as operações financeiras
- Status: ✅ pronto

### 2.10 Ajuda (`/ajuda`)
- Guia passo a passo em 6 etapas linkando as telas reais + regras que o sistema aplica sozinho
- Status: ✅ pronto

### 2.11 Páginas públicas (sem login)
- `/pagar/[fornecedor]`: nome → valor → chave copia-e-cola + dados do favorecido
- `/v/[token]`: mesma jornada vinculada ao vendedor (valor pode vir travado pela loja)
- `GET /chave-pix/[fornecedor]`: dados mínimos para pagamento
- Status: ✅ pronto (split/gateway dinâmico fica para Release 2)

### 2.12 Exportações
- CSV compatível com Excel PT-BR (`;`, BOM, 2 casas) em 6 formatos; toda exportação é auditada
- Status: ✅ pronto

### 2.13 Segurança e regras automáticas
- Login JWT com 4 perfis (admin, financeiro, operador, consulta); Auditoria restrita
- Dinheiro em precisão fixa; código PIX sem duplicidade; conciliação limitada ao saldo; projeção única; estorno com registro próprio
- 8 testes automatizados verdes; lint zerado
- Status: ✅ pronto

---

## 3. Menu atual (pós-redesign)

**Desktop:** sidebar 256px colapsável (Principal: Início, PIX, Cadastro, Controle, Links · Gerenciar: Conciliar, Caixa de entrada, WhatsApp, Projeções, Lançamentos, Histórico, Ajuda) + topbar com perfil.
**Mobile:** bottom bar fixa — Início, PIX, Cadastro, Controle, Links. Telas secundárias via atalhos "Gerenciar" no dashboard.
**Regra de segurança:** estorno e cancelamentos exigem a senha do usuário (anti-clique-sem-querer).

---

## 4. Pontos para decisão do time

| # | Decisão | Proposta atual | Alternativa |
|---|---|---|---|
| 1 | Ordem/fixas da bottom bar | Início, PIX, Conciliar, Links, Mais | Trocar Links ↔ Projeções, ou outra combinação |
| 2 | Tela de Compras dedicada | Usar Lançamentos filtrados | Criar `/compras` (compras por fornecedor/distribuidora) |
| 3 | Distribuidoras como entidade | Representante/fornecedor cobre | Novo tipo na cadeia |
| 4 | Split/gateway dinâmico | Release 2 (Checkto/Mercado Pago) | Antecipar |
| 5 | Piloto com 1–3 clientes | Após aprovação deste documento | — |

**Critério de aceite do menu:** usuário novo conclui o guia `/ajuda` sem ajuda externa.

---

## 5. Aprovação

- [ ] Funcionalidades (§2) aprovadas como estão
- [ ] Menu principal (§3) aprovado ou ajustado conforme decisão 1
- [ ] Decisões 2–4 priorizadas no backlog (`docs/issues/`: 22 prontas, 7 parciais, 16 a fazer)
- [ ] Piloto liberado (Sprint 8)

| Nome | Papel | Assinatura/Data |
|---|---|---|
| João Pedro Castro |  |  |
| Luiz Henrique |  |  |
| Matheus Emanuel |  |  |
