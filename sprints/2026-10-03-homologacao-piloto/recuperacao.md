# Backup e recuperação — SQLite do MVP

A ferramenta `scripts/backup_rotapay.py` cria e verifica um pacote privado com banco central, todos os bancos de lojas registrados como prontos e diretório de uploads. Restaura somente em diretório novo. Não faz publicação, troca de configuração operacional, backup PostgreSQL, agendamento, criptografia ou guarda externa automática.

## Condições para criar

Interrompa a API, jobs, integrações e qualquer escritor desses bancos. Confira a parada antes de usar `--operacao-parada`: essa opção é uma declaração do operador, não um detector de processos. Cópias SQLite individuais consistentes não garantem consistência entre bancos e arquivos quando a operação continua escrevendo.

Use caminhos explícitos e a mesma pasta de trabalho da API para localizar referências relativas do legado. No macOS, `/tmp` é um link simbólico; use seu caminho real `/private/tmp`. A ferramenta rejeita links simbólicos, caminhos indevidos, bancos prontos ausentes, referências de anexos/logos ausentes e arquivos de configuração/bancos dentro de uploads. Não coleta `.env`, credenciais Checkto, chaves de assinatura JWT ou configurações do serviço.

O pacote contém dados privados e hashes de senha. Guarde fora do Git e de diretórios publicados, com acesso restrito e proteção externa escolhida pelo responsável. Permissões locais: diretórios 0700 e arquivos 0600. SHA-256 detecta alteração em relação ao manifesto; não substitui assinatura/autenticidade nem proteção contra alguém que possa reescrever o pacote inteiro. Registre o hash do manifesto em registro separado protegido.

## Ensaio deste sprint — apenas dados sintéticos

Executar na raiz do RotaPay, usando o Python do ambiente de validação. Estes caminhos são descartáveis e não apontam para `pix.db`.

```sh
python scripts/backup_rotapay.py criar --central /private/tmp/rotapay-s17-origem/central.sqlite3 --ambientes /private/tmp/rotapay-s17-origem/tenants --uploads /private/tmp/rotapay-s17-origem/uploads --destino /private/tmp/NOVO-backup --operacao-parada
python scripts/backup_rotapay.py verificar --pacote /private/tmp/NOVO-backup
python scripts/backup_rotapay.py restaurar --pacote /private/tmp/NOVO-backup --destino /private/tmp/NOVA-recuperacao --operacao-parada
```

Destinos precisam ser novos. Nunca substitua as entradas pelo banco operacional sem autorização correspondente. Se falhar, a ferramenta remove somente o diretório parcial que acabou de criar; não apaga origem nem sobrescreve destino existente.

## Conferência da recuperação

Antes de iniciar a API, confira o manifesto, SHA-256, integridade SQLite e referências. O pacote se verifica sem precisar dos arquivos originais. Na cópia restaurada, somente `arquivo_path` de comprovantes/anexos é reendereçado ao novo uploads; valores, vínculos, autoria, declarações e histórico são preservados. Logos mantêm seus nomes e diretório por loja. Arquivo inativo continua guardado no pacote e indisponível pela API.

Abra a cópia com `DATABASE_URL`, `TENANT_DATABASE_DIR` e `UPLOAD_DIR` do diretório recuperado, sem copiar credenciais bancárias para o ensaio. Confirme login, seleção, notas/saldos, fornecedor, pagamentos, anexos, logos e links autorizados. A API grava auditoria e pode sincronizar referências técnicas de membros; após iniciar escritas, o hash do banco em uso naturalmente deixa de coincidir com o manifesto original. O pacote de backup deve permanecer fechado e imutável; verificar o banco ativo contra aquele manifesto não é teste válido de integridade do backup.

A troca operacional exige: versão identificada, cópia atual da origem, operador responsável, janela aprovada, saldos conferidos, usuários orientados e forma de voltar ao ambiente anterior. Este sprint apenas ensaiou a cópia recuperada, sem mudar configuração real ou migrar a primeira loja.

## Rotina proposta para o piloto

Fazer backup com a operação parada antes de importação/migração ou mudança relevante e no fechamento acordado com a loja; testar restauração em ambiente separado periodicamente. Definir responsável, frequência, retenção, armazenamento protegido e perda máxima aceitável com a loja. Não existe rotina agendada neste sprint nem promessa de prazo de recuperação/SLA. Recuperar um backup perde as escritas posteriores a ele; comparar esses registros antes de retomar.

Evidências deste ensaio em `evidencias/recuperacao.json`: três bancos, sete arquivos, saldos/declarações e downloads pela aplicação restaurada. Pacote sintético em `/private/tmp/rotapay-s17-backup`; demo em diretório separado. Não guardar dados reais nas evidências versionáveis.
