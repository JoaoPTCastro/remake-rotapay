# Checklist de aceite do piloto

Estado: preparação técnica local aprovada; aceite da loja e operação real pendentes. Não publicar nem migrar dados operacionais por inferência da aprovação de um sprint.

## Conferido localmente com dados sintéticos

- [x] Cliente paga ao fornecedor: notas e orçamentos independentes, abatimento parcial e sobra sem crédito automático.
- [x] Cliente paga à loja e repasse documentado ao fornecedor: fonte de origem, limites e aplicações por relação.
- [x] Fornecedor declara recebimento; declaração não lança dinheiro nem abate nota e permanece válida após abatimento/estorno.
- [x] Crédito explícito, prévia, acerto misto e estorno preservam fontes/saldos e a outra loja.
- [x] Consulta não escreve; fornecedor não acessa o financeiro interno ou anexos da loja.
- [x] Revogação local, compartilhamento por relação/loja, arquivos e identidades protegidos; concorrência/último administrador cobertos pela suíte completa.
- [x] Backup de controle, todas as lojas prontas e uploads verificado; recuperação em destino novo ensaiada.
- [x] Três bancos, sete arquivos, declarações e saldos recuperados; logo/anexos ativos acessíveis; arquivo inativo permanece bloqueado.
- [x] Adulteração, caminhos indevidos, symlinks, origem perdida e destino existente testados.
- [x] Python3.14/SQLite e stack atual conferidos. PostgreSQL e carga não homologados.

## A loja precisa conferir antes do piloto real

- [ ] Indicar o responsável pelo aceite e os usuários/papéis de cada loja.
- [ ] Conferir cadastros, fornecedores convidados e associações corretas. Não abrir operação com associação equivocada; fluxo de correção é pendência do produto.
- [ ] Comparar notas, pagamentos, repasses, sobras, créditos e estornos com a planilha/controle atual, em recorte autorizado e reconciliado.
- [ ] Resolver ou aceitar explicitamente cada divergência; registrar valores esperados/obtidos e referência da conferência.
- [ ] Confirmar que piloto será manual, sem integração bancária/OCR/WhatsApp automático nesta etapa; conferir recebedores por canal apropriado.
- [ ] Definir tratamento de declaração incorreta/contestação e quem suspende sua utilização como aceite. Portal atual mantém declaração imutável.
- [ ] Definir procedimento para novas contas internas. Administração por vínculo usa conta existente; onboarding de funcionário novo não foi implementado neste sprint.
- [ ] Conferir usabilidade desktop/celular e fluxos visuais com a loja; verificação HTTP não substitui esse aceite.
- [ ] Escolher ambiente de implantação e banco. Se PostgreSQL for escolhido, homologar estratégia de bancos/organizações, arquivos e concorrência antes de implantar.
- [ ] Definir frequência/retenção do backup, guarda protegida, responsável, perda tolerável e janela de recuperação; ferramenta não agenda nem criptografa pacotes.
- [ ] Aprovar versão, janela, backup atualizado e plano de volta antes de qualquer migração ou publicação.

## Registro de aceite — ainda não preenchido

Responsável da loja: pendente.
Data: pendente.
Recorte/versionamento dos dados conferidos: pendente.
Versão autorizada: pendente.
Divergências aceitas: pendente.
Ambiente autorizado: pendente.
Autorização de migração/publicação: não concedida.

## Próximo passo

Preparar o Sprint18 com ambiente, dados reconciliados, janela e plano de recuperação. Executar migração/ativação/publicação apenas após as autorizações correspondentes. Checkto por organização, OCR, políticas configuráveis e extensão externa de créditos/acertos permanecem no backlog; não os declarar entregues por este aceite local.
