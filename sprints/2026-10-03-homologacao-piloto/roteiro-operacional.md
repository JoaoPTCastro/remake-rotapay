# RotaPay — roteiro do piloto manual

Versão local homologada: Sprint17, stack atual Python3.14/SQLite + Next.js. Este roteiro não confirma aceite da loja nem autoriza ativação operacional. Checkto e OCR ficam fora deste piloto manual. Comprovante, declaração do fornecedor e confirmação bancária são registros diferentes.

## Preparar a loja

O administrador prepara o ambiente vazio da loja em Organizações. Confere clientes/fornecedores e notas, sem importar o histórico real enquanto os saldos não forem conciliados. Convida o fornecedor pelo email da conta; após o aceite, associa a identidade ao cadastro financeiro correto desta loja. Confere nome, documentos e relação comercial antes de confirmar: a associação atual é imutável pela interface.

Se associou a conta ao cadastro errado, desative o vínculo daquela loja e registre o incidente. Não tente corrigir mudando números no banco nem reaproveite outra conta. O fluxo formal de correção precisa ser definido antes de liberar esse caso em operação. Identidade e senha do fornecedor permanecem pessoais; desativar uma loja não desativa a conta nem as outras relações.

Adicione membros internos existentes pelo email exato e conceda somente o papel necessário. Admin administra vínculos; financeiro opera pagamentos/acertos; operador/consulta têm as restrições exibidas no sistema. O fluxo deste sprint não cria novas contas internas. Na loja original, perfil interno e perfil legado da conta devem coincidir; nas demais, o papel é por vínculo. A loja mantém pelo menos um administrador ativo.

## Cobrar e registrar o trajeto correto

Confirme o cadastro do fornecedor, chave, titular/recebedor indicado, validade e valor antes de compartilhar o link. O fornecedor comercial pode indicar outro recebedor bancário; isso não prova titularidade nem integração bancária. Chaves são por cadastro/loja. Ao alterar ou desativar uma chave, revise os links anteriores: destinos fixados não são trocados silenciosamente e um link pode ficar indisponível.

**Cliente paga ao fornecedor:** registre um pagamento cliente→fornecedor com cliente, fornecedor e referência do evento. Esse mesmo pagamento possui orçamento próprio em cada relação; abater a venda do cliente não abate automaticamente a compra da loja perante o fornecedor. Não crie outra entrada no caixa da loja para esse valor.

**Cliente paga à loja:** registre a entrada cliente→loja. Um repasse posterior ao fornecedor é outro evento, ligado à entrada de origem e limitado ao valor disponível para repassar. Aplicação documental na nota do cliente e limite financeiro de repasse são controles distintos. O repasse tem orçamento próprio perante o fornecedor; não registre novamente a entrada do cliente.

Comprovantes permanecem privados. Consulte os anexos autorizados; não use imagem nem ausência de contestação como confirmação bancária. Novas lojas não herdam as credenciais globais Checkto. A cobrança bancária dessas lojas permanece indisponível nesta versão; o piloto manual exige chave/registro/conferência externa autorizados pela loja.

## Fornecedor e abatimento

O fornecedor entra em Organizações e abre seu portal na loja correta. Consulta somente suas notas, recebimentos, valores aplicados/disponíveis e chaves. Declara recebimento após conferência externa, com referência que permita localizar essa conferência. A declaração registra autoria, data e valor; não confirma banco, cria crédito ou aplica abatimento.

A loja escolhe a nota e o valor de abatimento. Na relação fornecedor, registra também a concordância exigida pelo fluxo de aplicação/acerto. Receber um pagamento e concordar com sua destinação a uma nota são atos distintos; a declaração não substitui automaticamente a confirmação do acerto. Abatimento e estorno alteram o saldo da nota/orçamento; a declaração do recebimento permanece válida quando o valor pago continua o mesmo.

A sobra permanece disponível no pagamento. Crédito de conta exige lançamento explícito, com origem, relação, referência e conferência. Um acerto misto combina pagamentos e créditos somente após prévia válida; não consome duas vezes a mesma fonte. Confira pessoa, relação, notas e valores antes de efetivar.

## Corrigir e estornar

Use estorno com motivo e sua senha para desfazer uma aplicação ou acerto. Confira os dois lados após concluir: nota e fonte recuperam seus saldos; a outra relação continua independente. Não exclua registros nem lance pagamento fictício para compensar um erro.

Se o pagamento foi cancelado, o histórico da declaração permanece sinalizado; não vale como recebimento atual. Se o valor registrado divergir do declarado, preserve a referência e encaminhe a divergência ao responsável. Não cancele um pagamento real apenas para corrigir texto de uma declaração. A edição/contestação formal da declaração não faz parte do portal atual: registre a ocorrência e suspenda seu uso como aceite até resolução.

## Compartilhar e fechar o dia

Um extrato compartilhado é somente leitura, por destinatário/relação, com validade inicial de 7 dias e revogação. Não dá acesso a anexos, dados bancários ou outras pessoas/lojas. Confira a loja e o destinatário antes de enviar por canal autorizado; o sistema deste sprint não envia mensagens automaticamente.

No fechamento, compare notas abertas/quitadas, pagamentos, repasses, sobras, créditos e estornos com o controle da loja. Registre qualquer diferença antes de aceitar a operação. Guarde a referência da conferência e faça o backup offline definido em [recuperacao.md](recuperacao.md). Não atribua ao valor disponível a interpretação de saldo bancário.

## Incidente

Suspenda as escritas se houver suspeita de saldo incoerente, arquivo ausente ou acesso indevido. Preserve a versão e os registros. Revogue o vínculo/link afetado quando aplicável; não altere contas compartilhadas de outras lojas. O responsável técnico verifica o backup e prepara uma recuperação em diretório novo. A troca do ambiente em uso exige aprovação específica e conferência dos saldos/arquivos antes da retomada.
