# Sprint 13 — Preparação do legado e classificação

Etapa de preparação concluída localmente em 02/10/2026, autorizada por “ok siga”. **Migração financeira não concluída nem habilitada.** O escopo executado é inventário, classificação auditável e ensaio idempotente de classificação em cópia; as dependências para transição permanecem abertas.

## O que foi entregue

Tela privada `/legado`, acessível pelo menu, com seis fontes paginadas: movimentações PIX, lançamentos, projeções, conciliações, estornos e abatimentos documentais já registrados. Valores, vínculos explícitos e pendências ficam separados por origem; não se somam perspectivas como caixa ou dívida consolidada.

Admin/financeiro prepara uma prévia e confirma a decisão `pendente`, `manter_legado` ou `avaliar_transicao`, com evidência e cadastro/relação opcionais apenas entre vínculos compatíveis existentes. A interface revisa uma origem por vez; a API admite lotes de até 100 origens, sem repetições. Consulta/operador lê inventário e não classifica; recibos/evidências exigem admin/financeiro.

Novas tabelas `legado_lotes` e `legado_classificacoes` guardam recibo imutável, autoria, horário UTC, evidência, origem `(fonte, fonte_id)` e hash do estado financeiro pertinente. Unique constraints e rollback impedem duplicar classificação ou deixar lote parcialmente gravado. Repetição da mesma chave/carga devolve o recibo; conteúdo divergente gera conflito.

A prévia é revalidada na confirmação. Snapshot inclui titulares/papéis, alvos, conciliações/estornos, tolerância e dependências de notas/abatimentos/aplicações relacionadas. Estado alterado invalida prévia antiga; alteração posterior sinaliza `snapshot_atual=false`, sem reescrever o recibo. Classificação pendente é registro histórico, não resolução da pendência; edição/reclassificação de recibos não foi implementada.

Titular desconhecido, órfão/incompatível/divergente, estorno inconsistente, valores negativos ou saldos divergentes impedem decisões diferentes de pendente. Projeção não vira nota, crédito antigo não vira crédito novo e conciliação não vira dois abatimentos. Pendências documentais continuam visíveis mesmo em “avaliar transição futura”.

Nenhum endpoint de conversão foi criado. Nenhuma nota, pagamento, crédito, aplicação, quitação ou saldo consumível é produzido pela classificação. Os registros legados mantêm IDs e vínculos originais.

## Validação

- **433 testes aprovados**, Python 3.14.0, em 130,48 segundos; um aviso preexistente de Starlette/httpx. São 37 casos novos: 36 na suíte de legado e um no MVP.
- Testes incluem snapshot de todas as tabelas financeiras, leitura sem alterações, perfis, IDs/relações, dados privados omitidos, paginação, estados alterados, lote conflitante e duas requisições realmente concorrentes SQLite. A corrida de mesma chave inicialmente retornava conflito após outro recibo terminar; corrigida para devolver o recibo idempotente e revalidada.
- Frontend: lint sem erros/avisos, TypeScript aprovado, lint de tipos sem erros e 200 avisos preexistentes; build Next 16.3.8 aprovado com 51 páginas.
- Inicialização repetida do esquema na cópia preservou os registros anteriores de **35 tabelas**. Ensaio HTTP com cenários fictícios confirmou recibo/repetição, bloqueio de escrita por consulta, chave divergente rejeitada, ausência de conversão e preservação integral das tabelas anteriores ao exercício, exceto novos eventos de auditoria previstos.
- HTML autenticado confirmou gestão para admin, inventário para consulta e redirecionamento ao login sem sessão; cookie de perfil oposto não concede acesso. Nenhum token/JWT em HTML ou arquivos de evidência.
- Revisão do backend e revisão separada do frontend sem P1/P2 pendentes no escopo. `git diff --check` aprovado. [Logs, scripts e verificações](evidencias/).

No verificador de preservação HTTP, a primeira comparação misturava valores tipados do ORM com valores brutos SQLite (`bool`/datas). O verificador foi corrigido para usar a mesma representação antes/depois, mantendo a exigência de igualdade de todas as linhas. Não foram alterados dados para fazer a verificação passar; o recibo já gerado foi reutilizado idempotentemente.

## Pendências e limites

1. **Trava comum de consumo entre motores não implementada.** O legado e o motor novo ainda não reconhecem toda origem equivalente com referências diferentes. Unicidade da classificação não é trava financeira. Consumo integrado permanece desabilitado.
2. **Ensaio de migração financeira ainda pendente**, condicionado à decisão coexistir/substituir, mapeamento documental aprovado e dados reais autorizados. O ensaio realizado registra classificações em cópia, não converte saldos em outro motor.
3. Sem planilha da loja, não há inventário completo dos abatimentos realizados fora do RotaPay nem adaptação/importação do formato real. Desconhecidos continuam pendentes.
4. Snapshot registra estado histórico revalidado na leitura; não reserva dinheiro nem congela escritores financeiros até o commit. Alteração posterior aparece no inventário. Essa limitação impede tratar a classificação como autorização automática de consumo.
5. Sem ensaio PostgreSQL, volume operacional ou carga de desempenho. Paginação máxima 100; grafo máximo 5.000 registros, com rejeição explícita quando excede o limite, sem prévia incompleta.
6. Sem conferência visual interativa/mobile: política anterior do navegador rejeitou URL/protocolo. Bloqueio respeitado; HTTP/HTML não prova comportamento visual dos controles.

Sem acesso ao `pix.db` operacional, commit, push, deploy, envio externo ou migração operacional.

## Demo e continuidade

[Demo do legado](http://localhost:3023/legado), API `127.0.0.1:8023`. SQLite `/tmp/rotapay-legado-demo-20261002.db`, uploads `/tmp/rotapay-legado-demo-uploads`. Cenários são fictícios; cópia e processos são temporários. Frontend 3022 foi encerrado antes do build para evitar servir assets em reconstrução. Admin `demo@rotapay.local` / `[credencial demonstrativa omitida do Git]`; consulta `consulta.s11@rotapay.local` / `RotaPay-consulta-2026`.

Ver [inventário e regras](inventario-e-regras.md), [brief](brief.md) e [estado geral](../ESTADO-PROJETO.md).

Próximo proposto: **Sprint 14**, painel global e relatórios dos módulos novos, totais conciliáveis com extratos individuais, perspectiva cliente/fornecedor explícita e cobertura parcial informada. Legado segue em consulta separada até resolver a transição; não integrar saldos por inferência. Não iniciado; aguarda confirmação do usuário.
