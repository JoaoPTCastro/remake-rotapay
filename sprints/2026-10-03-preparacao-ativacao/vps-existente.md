# Homologação na VPS existente

Decisão do usuário: usar a VPS existente. Isto define hospedagem; não autoriza publicação nem migração.

## Referência histórica

Hostinger, IP registrado `2.24.108.54`, checkout `/srv/pix`, Caddy do host encaminhando para `127.0.0.1:3000`. Informações ainda não verificadas no servidor atual. O override citado no documento antigo agora existe no checkout: `docker-compose.ip.yml`. Ele expõe API e painel somente em loopback e deixa o Caddy do Compose fora do perfil padrão. Não ativar `https-compose` no cenário de Caddy do host sem revisar conflito de portas.

## Inventário remoto necessário — leitura apenas

Conferir usuário e acesso SSH, identidade do servidor, espaço livre, versões Docker/Compose, serviços ativos e portas. Identificar o projeto Compose e volume reais (não presumir nome pelo diretório), imagens anteriores, mounts, bancos central e de todas as lojas, anexos, tarefas escritoras e backup externo. Ler configuração do proxy/domínio sem divulgar segredos. Não executar `up`, `build`, `pull`, reinício, seed ou migração durante o inventário.

## Preparação local

Override mantém o volume original `pixdata` e os caminhos persistentes do plano. `.dockerignore` exclui segredos, bancos, uploads, backups e dependências locais do contexto de build. O frontend recebe API_URL da imagem, sem copiar arquivos locais de ambiente. Validar configuração combinada no servidor antes de construir. Se não houver domínio/HTTPS, não abrir piloto com dados reais; definir domínio e proxy primeiro.

## Ensaio separado da operação

Após inventário, definir projeto Compose de homologação, portas livres e volume próprio, usando dados sintéticos. Não reutilizar o nome do projeto nem o volume operacional. Construir candidato nesse ambiente e repetir autenticação, isolamento, portal, links, anexos e recuperação. Somente depois apresentar resultado e plano concreto de publicação para aprovação. O override entregue descreve a operação existente; não usá-lo sem adaptação de portas/projeto para homologação paralela.

## Situação

Sem acesso SSH identificado neste Mac. Nenhuma conexão ou alteração remota realizada. Docker local indisponível; Compose e build ainda não executados. Próxima dependência: confirmar endereço atual e usuário/alias SSH disponível, sem enviar senha pelo chat.


Atualização: acesso anterior confirmado e inventário remoto somente leitura concluído. Ver [inventário da VPS](inventario-vps.md). Não há mais bloqueio de acesso SSH; homologação da imagem e ativação continuam pendentes.


Atualização posterior: homologação técnica do candidato executada na VPS em ambiente separado. As limitações anteriores de Docker local permanecem históricas; build remoto e 545 testes na imagem agora aprovados. Ver [relatório de homologação](homologacao-vps.md). Ativação operacional e aceite real continuam pendentes.
