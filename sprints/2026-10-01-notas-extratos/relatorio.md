# RotaPay — entrega de notas e extratos

Data: 01/10/2026. Situação: base de notas e extratos implementada, validada localmente e disponível em demonstração. Esta entrega avança a Etapa 2 do plano revisado; não conclui todo o planejamento.

## Resultado entregue

- Nova área **Notas e extratos**, acessível pelo menu, pela ficha do cadastro e pelos lançamentos anteriores.
- Notas de venda ao cliente e de compra do fornecedor, com titular, número de documento, emissão, descrição e valor original preservado.
- Número único por titular e relação, impedindo que um reenvio crie outra obrigação com o mesmo documento. A numeração histórica continua reservada após cancelamento.
- Vencimento por prazo do cadastro, prazo informado, data explícita ou sem vencimento. O prazo herdado fica congelado na nota; alteração posterior do cadastro não muda o documento antigo.
- Saldo parcial e histórico de abatimentos no mesmo ID. Nenhuma nota remanescente é criada por pagamento parcial.
- Abatimentos **documentais de acertos externos já realizados**, com referência, observação, data e confirmação explícita. Data futura e abatimento acima do saldo são recusados.
- Proteção contra duplicidade por chave de requisição e controle transacional de versão. Duas sessões concorrentes não podem consumir mais que o valor disponível na nota.
- Estorno com registro próprio, motivo e senha do operador; cancelamento lógico de nota exige ausência de abatimentos ativos. Operações originais permanecem no histórico.
- Extrato por titular e relação, com original, abatido registrado, saldo aberto e saldo vencido. Notas canceladas permanecem consultáveis e ficam fora dos totais.
- Filtros de titular, relação, situação e atraso; paginação aplicada no banco antes da resposta. Notas sem vencimento não entram em atraso.
- Anexos PDF, PNG, JPEG e WebP, com upload limitado, assinatura/extensão compatíveis, armazenamento com nome aleatório, download privado e remoção lógica. A interface permite até 10 MB por arquivo no padrão atual.
- Administrador e financeiro podem escrever; operador e consulta podem ler. O backend também protege permissões e titularidade dos registros. Cadastros com notas históricas não perdem o papel usado na relação.

## Significado dos saldos

O abatimento externo documenta um acerto efetuado fora do RotaPay. Ele reduz o saldo desta nota, mas **não consome PIX, não confirma aceite do fornecedor, não movimenta caixa e não aplica conciliação automática**. Referência e observação são obrigatórias, e a interface explica o efeito antes de confirmar.

As tabelas de notas são separadas do motor legado. Os lançamentos e conciliações antigos continuam nas telas existentes e não foram automaticamente convertidos. O extrato indica “Notas cadastradas no RotaPay”; seus totais não representam a conta completa da planilha da loja nem saldo bancário.

## Validações e evidências

| Verificação | Resultado |
|---|---|
| Suíte completa do backend | **132 testes aprovados** em 14,74 s; 33 novos testes nesta entrega |
| Lint normal | Sem erros ou avisos |
| Lint tipado | Sem erros; os mesmos 200 avisos legados da entrega anterior |
| TypeScript | `tsc --noEmit` aprovado |
| Build do frontend | Aprovado, incluindo `/notas`, `/notas/[id]` e proxy privado de anexo |
| Migração em cópia | Inicialização repetida duas vezes; tabelas novas vazias e registros financeiros anteriores iguais |
| Interface real | Nota de R$ 1.000, abatimento de R$ 100, saldo de R$ 900 e extrato do cliente conferidos |
| Upload pela interface | PDF demonstrativo de 2.170.606 bytes enviado e baixado com o mesmo tamanho |
| Layout | Sem overflow horizontal nas larguras de 390 e 1024 px; viewport temporário restaurado |

Há um aviso conhecido de depreciação Starlette/httpx na suíte Python. A validação usou o ambiente isolado Python 3.11 e SQLite; não houve execução desta etapa em PostgreSQL.

A revisão de código e segurança identificou três ajustes concretos: filtro SQL de saldo em centavos, preservação de espaços em senhas legítimas e limite do upload em server actions. Os três foram corrigidos. Os dois cenários de backend ganharam testes de regressão; o upload acima de 1 MB foi exercitado no navegador. A consulta de notas também foi ajustada para agregar saldos no banco, evitando leituras individuais por linha.

Na cópia migrada, os **908 pagamentos/movimentações, 18 lançamentos, 274 conciliações e zero estornos** mantiveram todas as linhas iguais. O banco operacional não foi migrado nesta entrega. [Resultado da comparação](evidencias/migracao-copia.json).

Capturas somente com dados demonstrativos:

- [Nota com saldo parcial — desktop](evidencias/nota-desktop.jpg)
- [Nota no celular](evidencias/nota-celular.jpg)
- [Extrato do cliente](evidencias/extrato-demonstrativo.jpg)

## Disponibilidade local

[Abrir demonstração](http://localhost:3012/notas/1). A lateral identifica **Ambiente demonstrativo**. O frontend compilado usa uma API separada em `127.0.0.1:8012`, com banco e uploads temporários de teste fora do repositório. Esses servidores locais dependem desta sessão do computador; a demonstração não é publicação na VPS.

Fontes alteradas nesta entrega: modelos de notas, contratos e router do backend; registro do router; proteção dos papéis de pessoas; telas e ações de notas; proxy de download; links do menu/cadastro/lançamentos; helper DELETE e limite de server actions. As alterações anteriores de marca e cadastros foram preservadas.

Backup de fontes e SQLite anterior à edição: `backups-locais/2026-10-01-notas-extratos/`, ignorado pelo Git. Nenhum commit, push, deploy, cobrança real ou envio de mensagem foi realizado.

## Pendências e próxima etapa

1. Concluir itens auxiliares de cadastros: importação com prévia, exportação e alertas adicionais de chaves.
2. Concluir itens auxiliares de notas: catálogos configuráveis de operações/formas/prazos e importação/classificação dos documentos antigos.
3. Implementar pagamentos reais por relação: um evento de pagamento, aplicação independente no lado cliente e fornecedor, dinheiro e repasse documentado. A integração deverá distinguir os abatimentos externos já registrados para evitar utilizá-los novamente como pagamento novo.
4. Implementar acertos, confirmação do fornecedor, crédito residual rastreável, reutilização e estorno por relação, conforme as regras confirmadas nos áudios.
5. Implementar preferências de tabelas, dashboard individual, acesso compartilhado com escopo e piloto da loja.

As decisões ainda abertas sobre gateway desabilitado, ordem/tolerância automática de crédito, contestação do fornecedor e compartilhamento continuam registradas no plano dos áudios. Esta entrega não escolhe essas regras por inferência.

Próxima prioridade: modelo de pagamentos por relação e seus testes de conservação de saldo, antes de conectar notas ao motor operacional. Ativar a versão no banco operacional exige backup atualizado, migração revisada e reinício da aplicação; isso ainda não foi realizado.
