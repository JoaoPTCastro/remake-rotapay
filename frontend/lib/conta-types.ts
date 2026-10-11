export type EstadoConta = { ok?: boolean; mensagem?: string };
export type Loja = { id?: number; nome: string; documento: string; telefone: string; email: string; endereco: string; tem_logo?: boolean; logo_url?: string | null };
export type Usuario = { id: number; nome: string; email: string; perfil: string; ativo: boolean };
