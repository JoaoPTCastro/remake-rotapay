# Inventário do legado e limites da transição

Análise de código/testes em 02/10/2026. Nenhuma planilha da loja disponível; nenhum acesso ao banco operacional. Não afirmar cobertura de abatimentos externos não fornecidos.

| Origem | Significado registrado | O que falta para transição |
|---|---|---|
| Movimentação PIX | Evento com saldo consumível legado e titulares opcionais | Trajeto documental, pessoa/relação/destino e proveniência comum entre motores; IDs não provam confirmação externa |
| Lançamento | Débito/crédito/pagamento/desconto e outros tipos genéricos | Documento e vínculo com obrigação; tipo/descrição não prova nota |
| Projeção | Previsão por par representante/fornecedor | Decisão sobre coexistência com obrigação já existente; nunca criar nota por previsão |
| Conciliação | Consumo PIX em lançamento/projeção | Destino documental inequívoco; não prova dois abatimentos independentes |
| Estorno | Registro histórico que desfaz conciliação | Consistência entre flag estornada e registro; preservar original |
| Abatimento documental novo | Declaração externa ligada à nota, sem evento consumível | Origem real e correspondência com legado; não recriar pagamento para mesmo evento |

Fontes: `app/models.py` (Movimentacao, Lancamento, Projecao, Conciliacao, Estorno, NotaObrigacao, NotaAbatimento e Pagamento); `app/services.py` conciliar/estornar; `app/routers/pagamentos.py` `_ref_livre`; `app/referencias_financeiras.py`.

## Duplicidade e concorrência

O legado usa lock em memória para conciliar/estornar; o novo motor usa versões/CAS e trava por referência. A trava de referências declara explicitamente que não integra o legado. A checagem nova bloqueia códigos PIX/algumas referências iguais, mas não reconhece o mesmo evento com referência diferente. Ausência de igualdade textual não comprova eventos distintos.

Classificação terá origem imutável `(fonte, fonte_id)` e snapshot congelado, recibo idempotente e confirmação de prévia. Essas constraints impedem duplicar a classificação, **não substituem a futura trava de consumo financeiro entre motores**. A ponte financeira permanece desligada. Não existe conversão de classificação para pagamentos/notas/créditos neste sprint.

## Reconciliação por evidência

PIX: valor menos soma das conciliações ativas deve explicar saldo disponível. Projeção: valor projetado menos valor conciliado explica saldo; não representa caixa. Lançamentos podem ter excesso reconhecido como crédito por tolerância, vinculado por texto de descrição em vez de FK; diferença exige revisão, sem reparar saldo automaticamente. Conciliacao estornada e Estorno devem ser consistentes.

Nenhuma soma entre PIX, lançamentos, projeções e notas deve ser apresentada como total de caixa/dívida: podem representar o mesmo evento em perspectivas diferentes. Valores na prévia são valores da fonte, agrupáveis por pessoa/relação apenas com vínculo explícito, sem virar saldo consolidado integrado.

## Decisões ainda necessárias

- Loja confirmar coexistência ou substituição do sistema atual de notas.
- Arquivo real e autorização de análise para conhecer layout, IDs, documentos e abatimentos externos.
- Aprovar mapeamento documental e origem do crédito antigo (inclusive tolerância).
- Implementar proveniência comum e trava transacional antes de permitir consumo integrado, com testes concorrentes entre motores e PostgreSQL.
- Ensaio financeiro de migração em cópia somente depois dessas decisões; migração operacional exige autorização separada.
