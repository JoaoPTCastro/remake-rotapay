export type Contato = { id: number; nome: string; telefone: string; email: string; cargo: string; principal: boolean; ativo: boolean };
export type ChavePix = { id: number; chave: string; tipo: string; titular: string; banco: string; agencia: string; conta: string; tipo_conta: string; categoria: string; validade: string | null; principal: boolean; ativo: boolean };
export type CadastroPessoa = { id: number; tipo: string; nome: string; documento: string; apelido: string; endereco: string; telefone: string; email: string; observacoes: string; prazo_dias: number; prioridade: number; tolerancia_credito: number; ativo: boolean; contatos: Contato[]; chaves_pix: ChavePix[] };
export type CadastroResultado = { ok: boolean; mensagem: string };
