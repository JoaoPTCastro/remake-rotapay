export type ChaveFornecedor = {
  id: number; chave: string; tipo: "cpf" | "cnpj" | "email" | "telefone" | "aleatoria";
  titular: string; banco: string; agencia: string; conta: string; tipo_conta: string;
  categoria: "fixa" | "temporaria"; validade: string | null; principal: boolean; ativo: boolean;
};
export type PortalFornecedor = {
  organizacao_id: number; organizacao_nome: string; fornecedor: { id: number; nome: string };
  pagamentos: { id: number; codigo: string; tipo: string; forma: string; valor: number; data: string; cancelado: boolean; orcamento: { elegivel: number; aplicado: number; destinado_credito: number; saldo_disponivel: number; status: string }; recebimento: { id: number; referencia: string; observacao: string; created_at: string; valor_declarado: number; situacao: "declarado" | "divergente" | "cancelado" } | null }[];
  notas: { id: number; numero_documento: string; valor_original: number; saldo: number; vencimento: string | null; situacao: "aberta" | "quitada" | "cancelada" }[];
  chaves_pix: ChaveFornecedor[]; resumo: { total_recebimentos: number; total_declarado: number; saldo_notas: number; saldo_disponivel: number; total_aplicado: number };
};

export type FornecedoresLoja = { fornecedores: { user_id: number; nome: string; email: string; ativo: boolean; pessoa_id: number | null }[]; cadastros: { id: number; nome: string }[] };
