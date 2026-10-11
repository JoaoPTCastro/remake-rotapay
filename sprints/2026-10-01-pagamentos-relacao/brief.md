# Sprint 3 — pagamentos por relação

Autorização: usuário pediu seguir após apresentação da Sprint 3. Objetivo: conectar pagamentos reais novos às notas com aplicações independentes por relação, conservando saldo, identidade e histórico.

## Modelo e limites

- Um pagamento real, com valor, forma PIX/dinheiro, data, referência externa única e evidência privada.
- Cliente→fornecedor (PIX direto): elegibilidade do mesmo valor nos dois lados, nunca duas entradas de caixa.
- Cliente→loja (PIX ou dinheiro): somente lado cliente. Repasse posterior é outro evento real, vinculado ao recebimento, somente lado fornecedor. Soma dos repasses ativos não supera o recebimento original.
- Aplicação por relação respeita titular, saldo do pagamento naquele lado e saldo da nota. Não renumerar nota, editar valor original ou criar remanescente.
- Aplicação e abatimento da nota na mesma transação; estorno pela aplicação reverte os dois registros, sem afetar o outro lado.
- Idempotência, versão transacional, datas válidas, permissões e cancelamento lógico sem dependentes ativos.
- Não gerar crédito automático. Residual permanece disponível naquela relação.
- Não importar orçamento consumível do legado: seu saldo global não prova estado de cada lado. PIX antigos e abatimentos externos permanecem consultáveis, sem conversão automática. Referências coincidentes conhecidas exigem classificação manual.
- Declaração explícita de que o evento é novo e não duplica registro anterior. Não confirmar aceite do fornecedor, conciliação gateway ou transferência bancária automaticamente.

## Responsáveis e arquivos

| Responsável | Arquivos | Depende de |
|---|---|---|
| Backend | `app/**` | contrato definido |
| Frontend | `frontend/**` | contrato definido; integração depende do backend |
| Testes | `tests/**` | contrato definido; execução depende do backend |
| Coordenação | sprint e backups locais | testes, revisão e navegação |
| Revisão | leitura de fontes | implementação pronta |

Sem commit ou deploy. Os arquivos de cada implementador não se sobrepõem. Backup anterior em `backups-locais/2026-10-01-pagamentos-relacao/` ignorado pelo Git.

## Aceite principal

Venda R$ 1.000 e compra R$ 900; um PIX direto R$ 300 aplica no cliente e no fornecedor independentemente: saldos R$ 700 e R$ 600, apenas um evento real R$ 300. Estornar um lado não desfaz o outro. Dois operadores não excedem orçamento nem saldo da nota.

Dinheiro R$ 100 recebido na loja não reduz dívida de fornecedor até existir repasse documentado. O repasse não abre novo orçamento cliente. Nota com abatimento externo já registrado não recebe o mesmo pagamento outra vez por referência conhecida.

## Próximas etapas

Migração/classificação consumível do legado com transferência de domínio e travas; acertos em lote, confirmação do fornecedor, crédito residual rastreável, compartilhamento e piloto. Não inferir essas regras nesta entrega.
