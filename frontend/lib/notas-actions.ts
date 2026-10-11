"use server";
import { revalidatePath } from "next/cache";
import { unstable_rethrow } from "next/navigation";
import { apiPost, apiDelete } from "./api";
import type { NotaResultado } from "./notas-types";
const texto = (f: FormData, k: string) => String(f.get(k) ?? "").trim();
function erroSeguro(erro: unknown): string {
  const mensagem = erro instanceof Error ? erro.message : "";
  try {
    const dados = JSON.parse(mensagem.slice(mensagem.indexOf(":") + 1)) as { detail?: unknown };
    if (typeof dados.detail === "string") return dados.detail;
  } catch { /* Mensagem segura para falhas não estruturadas. */ }
  return "Não foi possível salvar. Confira os campos e sua permissão e tente novamente.";
}
export async function salvarNota(form: FormData): Promise<NotaResultado> {
  const modo = texto(form, "modo_vencimento");
  const dados = { condicao_id: Number(form.get("condicao_id")) || null, operacao_id: Number(form.get("operacao_id")) || null, pessoa_id: Number(form.get("pessoa_id")), relacao: texto(form, "relacao"), numero_documento: texto(form, "numero_documento"), valor_original: Number(form.get("valor_original")), data_emissao: texto(form, "data_emissao"), descricao: texto(form, "descricao"), modo_vencimento: modo, ...(modo === "data" ? { vencimento: texto(form, "vencimento") } : {}), ...(modo === "prazo_informado" ? { prazo_dias: Number(form.get("prazo_dias")) } : {}) };
  try {
    const nota = await apiPost("/notas", dados) as { id: number };
    revalidatePath("/notas");
    return { ok: true, mensagem: "Nota cadastrada.", id: nota.id };
  } catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: erroSeguro(erro) }; }
}
export async function registrarAbatimento(notaId: number, chave: string, form: FormData): Promise<NotaResultado> {
  if (form.get("confirmacao") !== "on" || !texto(form, "referencia")) return { ok: false, mensagem: "Informe a referência e confirme que o acerto ocorreu fora do RotaPay." };
  return executar(`/notas/${notaId}/abatimentos`, { valor: Number(form.get("valor")), data: texto(form, "data"), referencia: texto(form, "referencia"), observacao: texto(form, "observacao"), chave_idempotencia: chave });
}
export async function cancelarOuEstornar(notaId: number, abatimentoId: number | null, form: FormData): Promise<NotaResultado> {
  return executar(abatimentoId === null ? `/notas/${notaId}/cancelar` : `/notas/${notaId}/abatimentos/${abatimentoId}/estornar`, { senha: String(form.get("senha") ?? ""), motivo: texto(form, "motivo") });
}
export async function anexarNota(notaId: number, form: FormData): Promise<NotaResultado> {
  const arquivo = form.get("f");
  if (!(arquivo instanceof File) || !arquivo.size || arquivo.size > 10 * 1024 * 1024) return { ok: false, mensagem: "Selecione um arquivo de até 10 MB." };
  return executar(`/notas/${notaId}/anexos`, form);
}
async function executar(caminho: string, dados: unknown): Promise<NotaResultado> {
  try { await apiPost(caminho, dados); revalidatePath("/notas"); return { ok: true, mensagem: "Registro salvo." }; }
  catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: erroSeguro(erro) }; }
}

export async function removerAnexo(notaId: number, anexoId: number): Promise<NotaResultado> {
  try { await apiDelete(`/notas/${notaId}/anexos/${anexoId}`); revalidatePath("/notas"); return { ok: true, mensagem: "Anexo removido." }; }
  catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: erroSeguro(erro) }; }
}
