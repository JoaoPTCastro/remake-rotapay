# RotaPay — relatório da primeira entrega

Data: 01/10/2026. Situação: código implementado e validado localmente; sem commit, push ou publicação. Esta entrega cobre a base de cadastros e chaves do plano revisado após os sete áudios. O planejamento completo ainda não está concluído.

## Implementado

- Cadastro unificado com papéis cliente, fornecedor ou ambos, pesquisa e filtros por papel e situação. Compatibilidade mantida com as rotas existentes de representantes e fornecedores; o papel ambos participa dos dois fluxos.
- Ficha com dados cadastrais, contatos e informações financeiras. Criação, edição e desativação sem apagar histórico.
- Múltiplos contatos por pessoa, com cargo/responsabilidade, situação e contato principal único. A interface permite acesso ao WhatsApp sem envio automático.
- Múltiplas chaves PIX por pessoa, com titular, tipo, dados bancários, situação, principalidade e modalidade fixa ou temporária. Chave temporária exige validade; chaves inativas ou vencidas não ficam disponíveis para copiar.
- Permissões: administrador e financeiro podem alterar; usuários de consulta podem visualizar. A API também aplica as restrições, independentemente da interface.
- Proteção dos vínculos históricos: mudança de papel que eliminaria uma relação financeira existente é rejeitada. Desativação preserva os registros relacionados.
- Links de pagamento passam a guardar o destino selecionado na criação. Alterar a chave principal não redireciona um link já compartilhado. Se a chave daquele link for modificada, desativada ou expirar, o link fica indisponível, sem trocar silenciosamente de destino.
- Migração incremental e idempotente de cadastros legados e vínculos das chaves. Sincronização dos campos antigos para os fluxos existentes.
- Interface em PT-BR, estilos próprios da ficha e formulários com mensagens de erro e confirmação.

## Validações realizadas

| Verificação | Resultado |
|---|---|
| Suíte completa do backend | 99 testes aprovados; 26 novos testes de cadastros, migração e links |
| Lint do frontend | Aprovado, sem erros |
| Análise tipada do lint | Sem erros; 200 avisos em arquivos legados |
| TypeScript (`tsc --noEmit`) | Aprovado |
| Build de produção do frontend | Aprovado |
| Navegação real no navegador | Login, cadastro com ambos os papéis, contato principal e chave principal criados com dados demonstrativos |
| Revisão técnica | Correções incorporadas; sem achados acionáveis na revisão final |

Os testes cobrem autorização, titularidade dos contatos/chaves, principalidade única, proteção de histórico, validade, migração repetida, estabilidade do destino dos links e ausência de adoção silenciosa de uma chave futura.

Foi executada a migração duas vezes em uma cópia do SQLite. A comparação integral das linhas confirmou que os **908 pagamentos/movimentações, 18 lançamentos e 274 conciliações** permaneceram iguais; a tabela de estornos continuou vazia. Os nove cadastros foram preservados e cinco chaves foram migradas. Não havia telefone/e-mail preenchido para gerar contatos nessa cópia.

Os testes usaram banco isolado. A navegação usou outro banco demonstrativo. O banco operacional não foi migrado nesta entrega. Os servidores temporários de validação foram encerrados.

## Preservado nesta etapa

O motor financeiro existente, os saldos, as conciliações e a forma atual de registrar pagamentos não foram substituídos. As mudanças anteriores de marca RotaPay foram preservadas e não são contabilizadas como parte desta entrega.

Backup local de fontes e SQLite: `backups-locais/2026-10-01-cadastros-chaves/`, excluído do Git. A captura da interface contém somente dados demonstrativos: [ver captura](evidencias/cadastro-demonstrativo.jpg).

## Pendências do planejamento

1. **Concluir cadastros:** importação com prévia e validação, exportação, alertas adicionais de validade e confirmação do vocabulário cliente/intermediador/representante.
2. **Obrigações e extratos:** notas de venda e compra com anexos, vencimentos, valor original preservado, saldo parcial e histórico de abatimentos na própria nota; catálogos de formas, operações e prazos.
3. **Pagamentos por relação:** um pagamento real com aplicações e estados independentes no lado cliente e no lado fornecedor; pagamento em dinheiro e repasse documentado; classificação das conciliações antigas pela evidência disponível.
4. **Acertos e créditos:** seleção em lote, prévia, confirmação do fornecedor, abatimento parcial, crédito residual rastreável, reutilização e estorno por relação. O mesmo saldo não poderá aparecer simultaneamente como valor disponível do PIX e crédito adicional.
5. **Interface e acesso:** preferências de tabela, dashboard individual, compartilhamento com escopo, perfil/empresa e revisão de permissões.
6. **Piloto:** cenário completo dos dois lados, comparação com o controle atual e validação operacional da loja. OCR real exige definição de provedor.

Próxima prioridade técnica: obrigações e extratos, preparando o modelo dos dois lados antes de alterar a conciliação operacional. As regras ainda abertas no documento dos áudios — gateway desabilitado, ordem automática dos créditos, tolerância, contestação do fornecedor e compartilhamento — continuam explicitamente pendentes.

## Limites e ativação

- A migração foi validada em SQLite; não houve execução em PostgreSQL nem integração real com gateway nesta etapa.
- Para links legados, só é possível fixar o destino conhecido no momento da migração. Não há informação para reconstruir chaves históricas anteriores. Link sem destino conhecido permanece bloqueado em vez de assumir uma chave adicionada depois.
- A interface foi exercitada em navegador desktop; não houve homologação operacional da loja nem validação completa em dispositivos móveis.
- O código está no repositório local. A aplicação operacional precisa ser reiniciada com esta versão para ativar a mudança; na inicialização da API ocorre a migração incremental. Antes disso, manter um backup atualizado e revisar os links legados.
- Nenhuma cobrança, mensagem externa, deploy, commit ou push foi realizado.
