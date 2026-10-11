# Relatório do Sprint 11 — Administração, perfil e permissões

Data: 02/10/2026. Autorização: “pode começar”, seguida de “continue”. Estado: **concluído localmente; conferência visual manual confirmada pelo usuário**. Ambiente local, sem publicação.

## Entregas

- Conta separada em Meu perfil, Empresa, Senha, Usuários, Permissões e Auditoria. Formulários com envio, sucesso e erro seguro, sem devolver senhas ou payloads de erro ao usuário.
- Perfil pessoal editável em nome/email para os quatro perfis. Alterar email exige senha atual; campos de acesso enviados ao endpoint pessoal são rejeitados. A gestão administrativa não permite contornar a confirmação para alterar o próprio email ou senha; esses casos são direcionados ao fluxo pessoal.
- Gestão existente de usuários ampliada com nome/email, busca por ID/nome/email, filtro por perfil e motivo opcional para facilitar a auditoria. Convites não são enviados; criação local mantém senha inicial explícita. Autodesativação e remoção do último administrador ativo são bloqueadas.
- Correção de falha preexistente de concorrência: dois administradores podiam se rebaixar ao mesmo tempo, deixando zero admins. A administração agora serializa as alterações no banco até commit/rollback e relê o papel do ator. SQLite foi testado com duas requisições simultâneas; PostgreSQL possui caminho com lock de tabela, ainda sem ensaio nesse banco.
- Dados da empresa validados com limites e campos permitidos. Consultar a empresa deixou de criar registros. Operador/consulta recebem campos somente para leitura; admin/financeiro mantêm a edição já existente.
- Logo da empresa privada PNG/JPEG/WebP estática: até 2 MB, 2048 pixels por lado e 4 milhões de pixels. Conteúdo decodificado e convertido em PNG sem metadados; escrita atômica; autenticação, isolamento de diretório e respostas no-store/nosniff. Remover/substituir mantém arquivos anteriores privados no disco por exclusão lógica; não há política de expurgo definida.
- Matriz de acesso derivada das dependências efetivas das rotas FastAPI. Na demonstração: 132 ações autenticadas para admin e 63 ações permitidas para consulta. Admin consulta a matriz dos quatro perfis; demais perfis veem apenas as próprias ações. Não foram criadas permissões personalizadas nem ampliados os acessos existentes. Condições de senha, titularidade, status financeiro e último admin continuam aplicadas em cada operação.
- A interface consulta o perfil corrente em `/auth/me`, em vez de usar o cookie de perfil como fonte de acesso visual. Alterações de papel passam a aparecer com os dados do servidor.
- Auditoria com autor, horário UTC explícito, labels em português, horário de Brasília e antes/depois filtrados por campos permitidos. Detalhes administrativos de usuários/empresa ficam restritos ao admin; exportação existente continua sem senhas, hashes, tokens ou objetos livres. O nome exibido é o nome atual do autor associado ao ID, sem inventar um nome histórico congelado.

## Validação

- **358 testes passaram em 107,43 s**, com Python **3.14.0** e SQLite isolado. São 35 testes adicionais em relação ao Sprint 10: 34 administrativos e uma integração MVP. Um aviso preexistente Starlette/httpx.
- Lint principal: 0 erros/0 avisos. Lint tipado: 0 erros e 200 avisos preexistentes. TypeScript e build Next.js 16.3.8 aprovados após os últimos ajustes.
- Testes cobrem perfil próprio sem escalada, email/senha atual, conflito e rollback, papel corrente no token, proteção do último admin inclusive concorrência, bypass dos endpoints administrativos, inventário real de rotas, logo privado/limites/metadados/symlink/remoção, auditoria filtrada e exportações sem segredos.
- Migração aditiva `loja.logo_arquivo` aplicada duas vezes na cópia do Sprint 10. Os registros anteriores de 34 tabelas permaneceram iguais após a migração. Após os exercícios, somente users/loja puderam ter mudanças administrativas previstas; registros financeiros anteriores continuaram iguais.
- Demonstração API real confirmou: consulta sem acesso à gestão de usuários e escrita de empresa (403), tentativa de escalada pessoal rejeitada (422), token refletindo papel corrente, logo sem autenticação bloqueada, remoção retornando 404 e metadados da imagem removidos. Não foram salvos tokens em evidências.
- Revisão independente de backend/frontend não encontrou outro P1/P2 concreto antes da correção final. O controlador conferiu a correção final e a suíte passou. PostgreSQL não foi executado.
- Inspeção inicial da página Conta confirmou seções, matriz e auditoria renderizadas. **O teste interativo final e a conferência responsiva não foram concluídos:** ao retomar a ligação com `http://localhost:3021/conta`, o navegador rejeitou a ação por política de URL/protocolo. A recusa foi respeitada; não houve tentativa de contorno por outro navegador ou CDP. Nenhuma evidência de screenshot final foi produzida. O usuário confirmou a conferência manual em “ta certo, pode seguir para o sprint 12”; o sprint foi encerrado com essa confirmação, sem alegar repetição automatizada.

## Pendências e limites

Roteiro de conferência manual: [conferencia-visual.md](conferencia-visual.md). A demonstração frontend foi reconfirmada em execução na porta 3021 na retomada; isso não comprova comportamento visual.

- Conferência visual manual confirmada pelo usuário no encerramento. As evidências automatizadas continuam limitadas ao que foi efetivamente executado.
- Permissões personalizadas dependem da matriz aprovada pela loja. O inventário atual documenta os controles vigentes.
- CPF, telefone pessoal, nascimento e foto de usuários aguardam definição de necessidade e acesso; não houve ampliação dessa coleta.
- Canal e política de convites ainda indefinidos; nenhum convite enviado.
- Retenção/expurgo de logos anteriores e ensaio PostgreSQL permanecem pendentes.

## Continuidade

Demo temporária: http://localhost:3021/conta, API http://127.0.0.1:8021. Banco e uploads sintéticos em `/tmp/rotapay-administracao-demo-20261002.db` e `/tmp/rotapay-administracao-demo-uploads`. Login admin: `demo@rotapay.local` / `[credencial demonstrativa omitida do Git]`. Login consulta: `consulta.s11@rotapay.local` / `RotaPay-consulta-2026`. Processos temporários devem ser verificados ao retomar; não representam publicação.

Próximo proposto: Sprint 12 — extrato compartilhado com escopo, validade, revogação e isolamento entre titulares. Autorizado pelo usuário após confirmação manual do Sprint 11. Escopo: próprio cliente/fornecedor, valores e situações das notas/pagamentos, 7 dias, sem anexos ou dados bancários. Banco operacional `pix.db`, commit, push, deploy e transmissão externa não foram realizados.

## Fontes técnicas

A validação de imagens usa Pillow 12.3.0 fixado no requirements: [notas oficiais da versão](https://pillow.readthedocs.io/en/stable/releasenotes/12.3.0.html) e [orientações oficiais de segurança](https://pillow.readthedocs.io/en/stable/handbook/security.html). As permissões e regras de domínio foram verificadas no código local e no documento de continuidade.
