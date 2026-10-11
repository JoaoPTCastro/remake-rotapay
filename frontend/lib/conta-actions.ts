"use server";
import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect, unstable_rethrow } from "next/navigation";
import { apiPatch, apiPost, usuarioAtual } from "./api";
import type { EstadoConta } from "./conta-types";
const texto = (f: FormData, k: string) => String(f.get(k) ?? "").trim();
async function executar(tarefa: () => Promise<unknown>, mensagem: string): Promise<EstadoConta> {
  try { await tarefa(); revalidatePath("/conta"); revalidatePath("/", "layout"); return { ok: true, mensagem }; }
  catch (erro) { unstable_rethrow(erro); const status = (erro as { status?: number })?.status; return { ok: false, mensagem: status === 403 ? "Ação não permitida. Confira sua senha e seu perfil de acesso." : status === 409 ? "O email já está cadastrado. Use outro email." : status === 413 ? "O arquivo excede o limite permitido." : status === 415 ? "Use uma imagem PNG, JPEG ou WebP válida." : status === 422 ? "Confira os campos. Sua conta e o último administrador ativo devem permanecer protegidos." : "Não foi possível salvar. Confira os dados e tente novamente." }; }
}
export async function salvarMeuPerfil(_: EstadoConta, f: FormData) { return executar(() => apiPatch("/auth/me", { nome: texto(f,"nome"), email: texto(f,"email"), senha_atual: String(f.get("senha_atual") ?? "") || undefined }), "Seu perfil foi atualizado."); }
export async function salvarEmpresa(_: EstadoConta, f: FormData) { const corpo = Object.fromEntries(["nome","documento","telefone","email","endereco"].map(k => [k,texto(f,k)])); return executar(() => apiPatch("/loja", corpo), "Os dados da empresa foram atualizados."); }
export async function criarUsuarioConta(_: EstadoConta, f: FormData) { return executar(() => apiPost("/auth/users", { nome:texto(f,"nome"),email:texto(f,"email"),senha:String(f.get("senha") ?? ""),perfil:texto(f,"perfil") }), "Usuário criado. Combine a entrega da senha inicial por um canal privado."); }
export async function editarUsuarioConta(id: number, _: EstadoConta, f: FormData) { return executar(async () => { const me=await usuarioAtual(); return apiPatch(`/auth/users/${id}`, { ...(me.id === id ? {} : {nome:texto(f,"nome"),email:texto(f,"email")}),perfil:texto(f,"perfil"),ativo:f.get("ativo") === "on",motivo:texto(f,"motivo") || undefined }); }, "Usuário atualizado."); }
export async function redefinirSenhaConta(id: number, _: EstadoConta, f: FormData) { return executar(() => apiPost(`/auth/users/${id}/password`, { senha:String(f.get("senha") ?? "") }), "Senha redefinida. As sessões anteriores deste usuário foram encerradas."); }
export async function trocarSenhaConta(_: EstadoConta, f: FormData): Promise<EstadoConta> { const resultado = await executar(() => apiPost("/auth/me/password",{ senha_atual:String(f.get("senha_atual") ?? ""),nova:String(f.get("nova") ?? "") }), "Senha alterada."); if (!resultado.ok) return resultado; const jar = await cookies(); jar.delete("token"); jar.delete("perfil"); redirect("/login"); }
export async function salvarLogoConta(_: EstadoConta, f: FormData) { const arquivo=f.get("arquivo"); if (!(arquivo instanceof File) || arquivo.size === 0 || arquivo.size > 2 * 1024 * 1024) return {ok:false,mensagem:"Selecione PNG, JPEG ou WebP de até 2 MB e 2048 pixels por lado."}; const envio=new FormData(); envio.set("arquivo",arquivo); return executar(() => apiPost("/loja/logo",envio),"Logo atualizada."); }
export async function removerLogoConta(_: EstadoConta, f: FormData) { if (f.get("confirmar") !== "on") return {ok:false,mensagem:"Confirme a remoção da logo."}; return executar(async () => { const {apiDelete} = await import("./api"); return apiDelete("/loja/logo"); },"Logo removida."); }
