# Sprint 18 — preparação da ativação

Autorização: “vamos seguir”. Escopo autorizado: preparação local. Migração operacional e publicação continuam pendentes de autorização específica.

## Versão candidata

Usar o checkout homologado no Sprint 17 como base. Antes da publicação, registrar a revisão final do código, dependências, imagem construída e identificador de versão; não promover apenas pelo nome da branch. Há alterações locais anteriores sem commit. O candidato ainda não é uma imagem homologada: Docker não disponível neste Mac. A imagem atual usa Python 3.12, enquanto a suíte local foi validada em 3.14; validar a imagem e dependências antes da promoção, sem presumir compatibilidade.

## Persistência corrigida

Central `/data/pix.db`; lojas `/data/ambientes/organizacao-N.sqlite3`; anexos `/data/uploads`. Tudo no volume existente `pixdata`, sem renomeá-lo. O script de backup acompanha a imagem. Instâncias anteriores podem ter bancos de lojas em `/srv/ambientes-locais`, fora do volume: inventariar e preservar esses arquivos antes de recriar qualquer container. Não mover automaticamente sem verificar o cadastro central e os caminhos dos anexos. PostgreSQL exige homologação própria; o procedimento presente é para SQLite.

## Condições para ativar

- [ ] Loja aprova o roteiro e o checklist do Sprint 17, inclusive celular e comparação com controle real.
- [x] Hospedagem: VPS existente, confirmada pelo usuário.
- [ ] Confirmar endereço/acesso, domínio e responsáveis. Ver [homologação na VPS](vps-existente.md).
- [ ] Definir política operacional para associação errada, declaração incorreta e onboarding interno.
- [ ] Inventariar bancos/lojas/anexos e reconciliar totais por cliente e fornecedor; classificar os dados antes da importação.
- [ ] Definir janela, duração máxima da indisponibilidade e critérios de retorno.
- [ ] Construir a imagem candidata e testar nela autenticação, isolamento, links, portal, anexos e backup/restauração.
- [ ] Guardar backup fora do servidor com acesso restrito e testar sua recuperação.
- [ ] Aprovação específica para publicação e migração operacional.

## Sequência na janela aprovada

1. Registrar versão anterior, configuração, inventário e totais de controle. Preservar imagem anterior.
2. Interromper API e demais escritores, incluindo integrações e tarefas agendadas. Bloquear novas escritas durante a migração.
3. Criar pacote com `backup_rotapay.py criar`, informando caminhos explícitos de central, ambientes, uploads e destino novo, com `--operacao-parada`. Verificar com `verificar --pacote`. Não incluir segredos no pacote.
4. Ensaiar `restaurar` em destino novo com `--operacao-parada`. Conferir integridade, quantidade de bancos e arquivos, saldos e referências. A ferramenta não detecta processos escritores; a parada precisa ser garantida pelo operador.
5. Aplicar somente migração previamente ensaiada numa cópia; reconciliar totais e registrar divergências. Nenhuma importação financeira automática está autorizada agora.
6. Subir versão candidata apontando para o conjunto aprovado. Validar login, seleção de loja, fornecedor, link de cliente e downloads autorizados; conferir que outra loja não acessa os mesmos IDs.
7. Obter aceite dos responsáveis e abrir o piloto acompanhado. Registrar primeira operação e monitorar erros e divergências.

## Retorno

Falha de isolamento, perda de arquivo, divergência financeira ou impossibilidade de acesso impedem liberar o piloto. Parar escritores, preservar separadamente o estado da tentativa e restaurar o pacote anterior em destino novo. Trocar em conjunto bancos/anexos e imagem/configuração compatíveis. Não retornar apenas a imagem se o esquema mudou. Se houve operações novas, reconciliá-las antes de qualquer retorno: restaurar o ponto antigo pode descartá-las. Conferir os mesmos totais e acessos antes de reabrir.

## Limites atuais

Nenhum servidor, domínio ou dado operacional foi acessado. Checkto por organização permanece pendente. Aceite real, migração financeira, teste da imagem, implantação e acompanhamento do piloto ainda não foram executados. A preparação não encerra o Sprint 18 operacional.


Atualização posterior: homologação técnica do candidato executada na VPS em ambiente separado. As limitações anteriores de Docker local permanecem históricas; build remoto e 545 testes na imagem agora aprovados. Ver [relatório de homologação](homologacao-vps.md). Ativação operacional e aceite real continuam pendentes.
