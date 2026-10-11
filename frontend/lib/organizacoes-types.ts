export type EstadoOrganizacao = { ok: boolean; mensagem: string; token?: string };
export type Organizacao = { id: number; nome: string; perfil: string; ativo: boolean; financeiro_habilitado: boolean };
export type ConviteFornecedor = { id: number; email: string; nome: string; expires_at: string; accepted_at: string | null; revoked_at: string | null };
export type MembroOrganizacao = { user_id: number; nome: string; email: string; perfil: string; ativo: boolean };
