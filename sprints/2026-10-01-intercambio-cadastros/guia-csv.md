# Modelos CSV do Sprint 8

Padrão adotado: UTF-8, separador `;`, cabeçalho obrigatório, até500 linhas de dados e1MB. Modelos/exportações incluem BOM para facilitar abertura em planilhas. Valores monetários têm duas casas e vírgula; datas aceitam formato ISO `AAAA-MM-DD` ou brasileiro `DD/MM/AAAA`. Baixar o modelo atual na área Intercâmbio e conferir as instruções da prévia antes de confirmar.

## Cadastros

Campos: `tipo;nome;documento;telefone;email;apelido;endereco;observacoes;prazo_dias`.

Documento obrigatório na importação: CPF com11 ou CNPJ com14 dígitos, normalizado sem pontuação. Essa exigência identifica registros para comparação; não atesta identidade nem situação fiscal. Cadastro manual existente sem documento deve ser revisado pela equipe antes de importar seu equivalente. Documento repetido/ambíguo ou dados diferentes impedem o lote; a importação não atualiza registros existentes silenciosamente. Cliente e fornecedor compartilham um cadastro com papel `ambos` quando apropriado; não importar duas fichas da mesma pessoa para separar relações financeiras.

Chaves PIX e contatos múltiplos continuam sendo mantidos pela ficha. Este modelo não muda destinos, principalidade, prioridade ou tolerância de registros antigos.

## Notas

Campos: `documento_pessoa;relacao;numero_documento;valor_original;data_emissao;modo_vencimento;prazo_dias;vencimento;descricao`.

O cadastro precisa existir, estar ativo e ter papel compatível com a relação `cliente` ou `fornecedor`. O número identifica a nota dentro do cadastro/relação. A nota criada entra integralmente aberta. Não incluir quitação, abatimento, saldo remanescente, crédito ou pagamento histórico: esses efeitos precisam de conciliação específica.

Vencimento: `prazo_cadastro` congela o prazo atual; `prazo_informado` exige prazo_dias; `data` exige vencimento; `sem_vencimento` não recebe prazo/data. Mudança relevante no cadastro após a prévia exige nova conferência.

## Conferir e confirmar

1. Baixar o modelo e preencher apenas os campos indicados.
2. Selecionar o arquivo e gerar a prévia. Nenhum cadastro/nota é criado nesta etapa.
3. Conferir novos, já existentes e erros por linha. Havendo erro, corrigir o arquivo e gerar outra prévia.
4. Confirmar explicitamente o lote válido. Alterar arquivo ou deixar a prévia expirar exige nova conferência.
5. Conferir o resultado e os IDs criados. Repetir o mesmo lote não cria uma segunda cópia.

O modelo de pagamentos é preparação de formato; não há importação financeira de pagamentos neste sprint. Exportações de consulta podem incluir IDs, estados e saldos que não fazem parte dos modelos de importação; não confundir relatório de consulta com arquivo pronto para reimportação. Campos textuais potencialmente interpretáveis como fórmulas recebem proteção na exportação.
