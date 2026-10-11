# Relatório — preparação local do Sprint 18

03/10/2026. Autorizado por “vamos seguir”. Preparação local concluída; Sprint 18 operacional permanece aberto.

## Entregas

Corrigidos Dockerfile.api e docker-compose.prod.yml para manter os bancos das lojas em `/data/ambientes`, no mesmo volume persistente da central e dos anexos. Incluído o script de backup na imagem da API. Atualizado o procedimento histórico de VPS, retirando a recomendação de compactar o volume durante operação. Entregue plano com requisitos de ativação, inventário de instalações anteriores, reconciliação, janela, ensaio e retorno preservando as operações posteriores ao backup.

## Verificação

22 testes de backup aprovados em 0,28 s, Python 3.14. Revisão textual das alterações de persistência e inclusão do script; conferência de caminhos contra app/ambientes.py e backup_rotapay.py. A suíte completa de 545 testes pertence ao Sprint 17 e não foi repetida. Nenhuma lógica de aplicação ou tela foi alterada. Docker não está disponível neste ambiente: build, resolução do Compose e funcionamento da imagem não foram verificados. Divergência Python 3.12 na imagem versus 3.14 local registrada como requisito de homologação, sem alteração especulativa da versão.

## Pendências

Aceite real da loja, ambiente/domínio/responsáveis, dados reconciliados, políticas de correção/onboarding, validação da imagem, janela e aprovação específica de implantação. Não houve conexão com VPS, alteração de dados operacionais, seed, publicação, commit ou push. Demos existentes preservadas.

## Próximo passo

Concluir os requisitos do plano e homologar a imagem no ambiente escolhido antes de propor a janela operacional. Não iniciar outro sprint automaticamente.

## Complemento — VPS existente escolhida

Hospedagem confirmada pelo usuário. Entregues override de portas locais/Caddy do host, exclusão de segredos/dados do contexto Docker e roteiro de inventário/ensaio separado. IP e configuração antigos são referências ainda não verificadas. Não há alias SSH da VPS configurado no Mac; acesso atual precisa ser informado. Nenhuma conexão remota ou build foi realizada; configuração Docker permanece pendente de validação pelo Compose.


Atualização: acesso anterior confirmado e inventário remoto somente leitura concluído. Ver [inventário da VPS](inventario-vps.md). Não há mais bloqueio de acesso SSH; homologação da imagem e ativação continuam pendentes.


Atualização posterior: homologação técnica do candidato executada na VPS em ambiente separado. As limitações anteriores de Docker local permanecem históricas; build remoto e 545 testes na imagem agora aprovados. Ver [relatório de homologação](homologacao-vps.md). Ativação operacional e aceite real continuam pendentes.
