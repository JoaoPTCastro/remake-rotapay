"use server";
import { revalidatePath } from "next/cache";
import { unstable_rethrow } from "next/navigation";
import { apiGet, apiPost } from "./api";
import type { RelacaoNota } from "./notas-types";
import type { Acerto, AcertoInput, AcertoResultado, PreviaAcerto, RecursosAcerto } from "./acertos-types";
const texto = (f: FormData, k: string) => String(f.get(k) ?? "").trim();
function erroSeguro(erro: unknown): string {
  const mensagem = erro instanceof Error ? erro.message : "";
  try { const detalhe = JSON.parse(mensagem.slice(mensagem.indexOf(":") + 1)) as { detail?: unknown }; if (typeof detalhe.detail === "string") return detalhe.detail; }
  catch { /* Nunca exibir dados enviados, segredos ou stack trace. */ }
  return "Não foi possível concluir. Confira os campos, sua permissão e tente novamente.";
}
async function executar<T>(caminho: string, dados: unknown): Promise<AcertoResultado<T>> {
  try { const registro = await apiPost(caminho, dados) as T; revalidatePath("/acertos"); revalidatePath("/pagamentos"); revalidatePath("/notas"); revalidatePath("/creditos"); return { ok: true, dados: registro, mensagem: "Registro salvo." }; }
  catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: erroSeguro(erro) }; }
}
export async function gerarPreviaAcerto(dados: AcertoInput): Promise<AcertoResultado<PreviaAcerto>> { return executar<PreviaAcerto>("/acertos/previa", dados); }
export async function criarAcerto(dados: AcertoInput, token: string, chave: string): Promise<AcertoResultado> { return executar<Acerto>("/acertos", { ...dados, token_previa: token, chave_idempotencia: chave }); }
export async function recursosAcerto(pessoaId: number, relacao: RelacaoNota, offsets: { pagamentos: number; notas: number; creditos: number } = { pagamentos: 0, notas: 0, creditos: 0 }): Promise<AcertoResultado<RecursosAcerto>> {
  if (relacao !== "cliente" && relacao !== "fornecedor") return { ok: false, mensagem: "Relação inválida." };
  const qs = new URLSearchParams({ pessoa_id: String(pessoaId), relacao, pagamentos_offset: String(Math.max(0, offsets.pagamentos)), notas_offset: String(Math.max(0, offsets.notas)), creditos_offset: String(Math.max(0, offsets.creditos)), limit: "50" });
  try { const dados = await apiGet(`/acertos/recursos?${qs}`) as RecursosAcerto; return { ok: true, dados, mensagem: "Recursos consultados." }; }
  catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: erroSeguro(erro) }; }
}
export async function acompanharAcerto(id: number, operacao: "enviar" | "confirmar", form: FormData): Promise<AcertoResultado> {
  if (form.get("confirmacao_operacao") !== "on") return { ok: false, mensagem: "Confirme que a ação ocorreu fora do RotaPay." };
  const campos = operacao === "enviar" ? { referencia_envio: texto(form, "referencia"), observacao_envio: texto(form, "observacao") } : { referencia_confirmacao: texto(form, "referencia"), observacao_confirmacao: texto(form, "observacao") };
  return executar(`/acertos/${id}/${operacao}`, campos);
}
export async function efetivarAcerto(id: number, form: FormData): Promise<AcertoResultado> {
  if (form.get("confirmacao") !== "on") return { ok: false, mensagem: "Confirme a efetivação das aplicações deste acerto." };
  return executar(`/acertos/${id}/efetivar`, { confirmacao: true });
}
export async function desfazerAcerto(id: number, operacao: "estornar" | "cancelar", form: FormData): Promise<AcertoResultado> { return executar(`/acertos/${id}/${operacao}`, { senha: String(form.get("senha") ?? ""), motivo: texto(form, "motivo") }); }
