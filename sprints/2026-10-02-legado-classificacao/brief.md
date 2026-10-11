# Sprint 13 — Legado, classificação e ensaio em cópia

Autorizado pelo usuário em 02/10/2026: “ok siga”.

Entregar inventário privado paginado do legado (PIX, lançamentos, projeções, conciliações, estornos e abatimentos documentais), divergências e pendências por evidência. Prévia e confirmação auditável/idempotente de classificação congelam origem e snapshot, sem criar notas, pagamentos, créditos ou saldo consumível. Identificadores legados preservados. Demonstração e ensaio somente em cópia sintética, com comparação antes/depois e repetição sem duplicidade.

Falta decisão da loja sobre coexistência/transição, planilha real autorizada e origem documental dos abatimentos externos. Não inferir quitação, relação adicional, caixa, obrigação ou crédito histórico. Projeção não é nota; conciliação antiga não prova dois abatimentos; crédito legado não vira crédito novo.

Trava comum de consumo entre motores permanece requisito antes da integração. Este sprint não habilita conversão ou consumo integrado: demonstrar bloqueio explícito e registrar a dependência. Sem leitura do pix.db operacional, envio, publicação, commit, push ou migração operacional.

Arquivos/dependências: onda1 backend novo app/legado_*.py, app/routers/legado.py, modelos e main (backend); inventário documental (raiz). Onda2 frontend /legado e lib/legado-* mais Shell (frontend), testes/test_legado.py e caso MVP (testes), revisão somente leitura após backend/frontend. Sem arquivos comuns nas ondas concorrentes.

Aceite: permissions reais; registros desconhecidos ficam pendentes; snapshot alterado invalida confirmação; repetição não duplica classificação; fonte repetida/conflitante rejeitada; nenhuma tabela financeira anterior alterada. Suite canônica e frontend lint/types/build. Navegador bloqueado anteriormente: respeitar, usar verificações HTTP/HTML sem alegar validação visual.
