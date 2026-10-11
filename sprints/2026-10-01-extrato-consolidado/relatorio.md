# Sprint 7 — extrato individual consolidado

Concluído e validado localmente em 01/10/2026. Autorização: usuário pediu retomar de onde paramos, com Sprint 7 como próximo escopo registrado. Sprint 8 aguarda nova confirmação.

## Entrega

Consulta individual autenticada por cadastro e relação, reunindo notas, pagamentos, créditos e acertos do domínio novo. Cliente e fornecedor permanecem separados. Totais globais calculados em um único statement SQL: original/abatido/aberto/vencido nas notas, aplicações e disponibilidade dos pagamentos, créditos reconhecidos/utilizados/disponíveis e contagem de acertos por situação. Crédito reconhecido desconta sua origem; disponível para aplicar não abate automaticamente a dívida nem representa caixa/receita.

Cinco listas com filtros e paginação SQL independente: notas, pagamentos, créditos, acertos e histórico. Filtros das listas não alteram os totais globais da conta. Histórico inclui criação, aplicação, cancelamento, estorno, reconhecimento/reversão e etapas de acerto, com links aos documentos. Abatimentos representam aplicações uma vez; eventos de acerto são informativos, sem novo valor financeiro. Horários exibidos em São Paulo; período da timeline convertido de calendário local para UTC. Listas de documentos usam data da operação.

Acesso pelo menu, ficha de cadastro e tela de notas. Leitura nos quatro perfis existentes, inclusive histórico de cadastro inativo; anônimo bloqueado. Cache privado sem armazenamento. Nenhuma nova escrita financeira, entidade ou migração neste sprint.

## Validação

- Suíte canônica: **244 passed em 41,42 s**, um aviso preexistente Starlette/httpx. 17 cenários de extrato e nova integração MVP, cobrindo relações, totais, filtros antes da paginação, histórico, permissões, calendário e ausência de mutações.
- Lint principal: zero erros/avisos. Lint tipado: zero erros e 200 avisos preexistentes. TypeScript e build aprovados.
- Revisão final independente somente leitura de backend/frontend/CSS: sem P1/P2 pendentes.
- API da demo: quatro combinações titular/relação e vinte listas verificadas. Cliente #1: original1500, abatido1000, aberto500, pagamento200, crédito100, disponível300. Fornecedor #2: original1500, abatido1200, aberto300, pagamento60, crédito40, disponível100. Relações opostas vazias, sem dados de outro titular.
- Navegação: seleção de cliente/fornecedor, filtro Quitado com uma nota e totais preservados, período sem registros com listas vazias e totais preservados, acesso à nota #4 pela origem e acesso ao extrato pela ficha do cadastro.
- Responsividade: cartões/formulários e navegação móveis conferidos; largura de rolagem do documento igual à largura disponível nas verificações móvel/desktop (312 e1054 pixels efetivos, respectivamente). Capturas abaixo.
- **19 tabelas financeiras da demo conservaram contagem e SHA256 integral dos registros** após API/navegação. Evidências antes/depois salvas; login só registra auditoria de autenticação, fora desse conjunto financeiro.

## Evidências e ambiente

[Respostas API sintéticas](evidencias/api-demo.json), [estado financeiro antes](evidencias/financeiro-antes.json), [depois](evidencias/financeiro-depois.json), [desktop](evidencias/extrato-desktop.png), [mobile](evidencias/extrato-mobile.png), [roteiro](evidencias/roteiro-validacao.md).

Demo: http://localhost:3017/extratos. API127.0.0.1:8017, SQLite temporário `/tmp/rotapay-extrato-demo-20261001.db`, cópia da demo sintética do Sprint6. Processos/arquivos temporários podem expirar. Backup local anterior em `backups-locais/2026-10-01-extrato-consolidado/`.

Arquivos: novo `app/routers/extratos.py` e registro em `app/main.py`; área `frontend/app/(painel)/extratos/`, helpers/types e integrações menu/cadastro/notas; testes `tests/test_extratos.py` e MVP. Alterações anteriores dos outros sprints preservadas.

## Limites e próximo passo

Dados financeiros antigos continuam nas telas anteriores. Não há integração automática do legado nem extrato público/compartilhamento. PostgreSQL não executado; validação em SQLite/Python3.11, enquanto projeto declara3.14. Banco operacional não migrado, nenhuma publicação, commit ou push.

Proposta Sprint8: completar cadastros, alertas de chaves, manutenção dos links e importação/exportação com prévia, erros por linha, confirmação e proteção contra duplicidades. Formatos/amostras e vocabulário devem ser definidos antes das partes dependentes; importação financeira consumível de legado permanece no Sprint13. **Não iniciado; aguardar confirmação do usuário.**
