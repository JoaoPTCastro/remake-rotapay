# Sprint 8 — intercâmbio, alertas e links

Implementação e validação local realizadas em01/10/2026; fechamento documental em02/10/2026. Autorização: usuário confirmou “ok, pode seguir” após proposta do Sprint8. Sprint9 aguarda confirmação.

## Entregas

- Área Intercâmbio: modelos CSV de cadastros/notas e formato preparatório de pagamentos; importação de cadastros e novas notas abertas, com prévia sem escrita, erros por linha e confirmação explícita. Arquivo inválido bloqueia o lote inteiro. CSV UTF-8, separador`;`, máximo1MB/500linhas.
- Confirmação HMAC de15minutos vinculada ao usuário, tipo, conteúdo e snapshot relevante. Alterar arquivo/cadastro exige nova prévia para lote novo. Recibo persistente por conteúdo e chaves de tentativa impede repetição; mutex compartilhado com cadastro manual serializa verificação/gravação. Importação atômica, sem commits por linha.
- Documentos CPF/CNPJ normalizados obrigatórios na importação. Duplicidades e dados divergentes não sobrescrevem registros. Cadastros históricos ambíguos permanecem preservados; alterar outros dados mantendo seu documento é permitido. Não há validação de identidade fiscal.
- Exportações filtradas de cadastros e notas: BOM, proteção contra fórmulas, valores monetários com duas casas/vírgula inclusive valores inteiros. IDs e prazos continuam inteiros. Limite10mil explícito; nomes de arquivo identificam filtros estruturados. Importação admin/financeiro; consulta/exportação nos quatro perfis existentes.
- Alertas de dívida aberta de fornecedor sem chave disponível, chave temporária expirada e validade em até30dias. Avisos não cancelam obrigações nem trocam destinos.
- Consulta privada dos links por titular, com filtros/paginação e evidência interna de uso. Destino fixado permanece visível; mudar chave principal não redireciona link antigo. Acesso pela ficha, alertas e titular do pagamento; nenhum vínculo com um pagamento específico é presumido.

## Validação final

**275 testes aprovados em50,89s**, após a correção final do CSV monetário.31 regressões adicionais ao Sprint7:21CSV,9alertas/links e1integração MVP. Cobertura inclui prévia sem writes, atomicidade, arquivos/linhas inválidos, permissões, token alterado/expirado, snapshot obsoleto, documentos ambíguos, repetição persistente com outra chave, concorrência de arquivos diferentes com mesmo documento, filtros, formatos e destinos preservados. Um aviso preexistente Starlette/httpx.

Lint principal: zero erros/avisos. Lint tipado: zero erros/200avisos preexistentes. TypeScript e build aprovados. Revisão independente somente leitura: sem P1/P2 pendentes; última correção de formato também revisada/testada.

Navegação na demo:

1. Lote inválido com uma linha válida e outra inválida: prévia indica erro e confirmação bloqueada; nenhum cadastro criado.
2. Dois cadastros sintéticos criados pela interface; duas notas novas confirmadas: clienteR$500/vencimento08/10/2026 e fornecedorR$300/vencimento15/10/2026.
3. Repetição do lote de cadastros: recibo anterior devolvido, sem duplicação. Nova prévia das notas indica duas já existentes.
4. Modelo CSV baixado pelo proxy autenticado. Exportação filtrada titular3/cliente contém somente sua nota, com500,00/0,00/500,00 e IDs/prazo inteiros.
5. Três tipos de alertas apresentados no cadastro. Link sintético sem valor fixo manteve chave original após troca da principal; nenhum gateway acionado. Filtro sem uso navegado.
6. Mobile390px: largura disponível/rolagem375px, sem transbordamento do documento em Intercâmbio e links; viewport restaurado.

Comparação de23tabelas: registros anteriores da demo conservaram contagens e hashes integrais. Foram acrescentados somente os novos cadastros/notas e chaves/link sintéticos de validação; pagamentos, créditos, acertos e histórico anterior preservados. Banco operacional intocado.

## Evidências e ambiente

[Guia CSV](guia-csv.md), [API](evidencias/api-demo.json), [alertas/links](evidencias/alertas-links-demo.json), [registros anteriores](evidencias/registros-anteriores.json), [comparação posterior](evidencias/registros-depois.json), [exportação filtrada](evidencias/export-notas-filtrado-ui.csv), [interface](evidencias/intercambio-desktop.png), [alertas](evidencias/alertas-desktop.png), [mobile](evidencias/intercambio-mobile.png). Arquivos de aceite contêm exclusivamente dados sintéticos.

Demo registrada: http://localhost:3018/intercambio, API127.0.0.1:8018, SQLite `/tmp/rotapay-intercambio-demo-20261001.db`. Temporários/processos podem expirar; verificar ao retomar. Backup ignorado em `backups-locais/2026-10-01-intercambio-cadastros/`.

Backend: `app/routers/intercambio.py`, `cadastros_consulta.py`, `app/importacao_identidade.py`, modelos dos recibos/chaves, registro de rotas e proteção nos cadastros manuais. Frontend: Intercâmbio, proxy de download, alertas, consulta de links e integrações. Testes de CSV/alertas/links e MVP. Alterações anteriores preservadas.

## Limites e pendências

Modelos próprios adotados; adaptação a eventual formato da loja continua pendente. Vocabulário cliente/intermediador/representante não alterado. Importação não atualiza silenciosamente registros, não importa chaves múltiplas, pagamentos/saldos históricos, quitações ou créditos. Pagamentos têm apenas modelo preparatório; integração financeira do legado permanece no Sprint13. Links nunca usados permanecem preservados; não foi adotada política automática de exclusão/reativação.

PostgreSQL não executado; testes em SQLite/Python3.11, projeto declara3.14. Duas tabelas novas de recibos/chaves foram criadas somente em bases isoladas. Nenhuma migração operacional, publicação, commit ou push.

Próximo proposto: **Sprint9 — catálogos financeiros e preferências de tabelas**, preservando condições dos documentos antigos. Regras novas de compra/devolução e classificações financeiras exigem definição da loja; não presumir efeitos. Aguardar confirmação do usuário antes de começar.
