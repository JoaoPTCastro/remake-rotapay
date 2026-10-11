"use server";
import { unstable_rethrow } from "next/navigation";
import { revalidatePath } from "next/cache";
import { apiPost, perfil } from "./api";
import type { TipoImportacao, PreviaImportacao, ConfirmacaoImportacao, ResultadoIntercambio } from "./intercambio-types";
async function executar<T>(tipo: TipoImportacao, etapa: "previa" | "importar", form: FormData): Promise<ResultadoIntercambio<T>> {
  try {
    if (!["cadastros", "notas"].includes(tipo)) return { ok: false, mensagem: "Tipo de importação inválido." };
    if (!["admin", "financeiro"].includes(await perfil())) return { ok: false, mensagem: "Seu perfil permite consultar e exportar. A importação exige administrador ou financeiro." };
    const arquivo = form.get("f");
    if (!(arquivo instanceof File) || arquivo.size === 0 || arquivo.size > 1024 * 1024) return { ok: false, mensagem: "Selecione um CSV UTF-8 de até 1 MB." };
    const dados = await apiPost(`/csv/${tipo}/${etapa}`, form) as T;
    if (etapa === "importar") { revalidatePath("/cadastro"); revalidatePath("/notas"); }
    return { ok: true, dados };
  } catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: erroSeguro(erro) }; }
}
export async function previaCSV(tipo: TipoImportacao, form: FormData) { return executar<PreviaImportacao>(tipo, "previa", form); }
export async function importarCSV(tipo: TipoImportacao, form: FormData) { return executar<ConfirmacaoImportacao>(tipo, "importar", form); }

function erroSeguro(erro: unknown) { const mensagem = erro instanceof Error ? erro.message : ""; try { const corpo = JSON.parse(mensagem.slice(mensagem.indexOf(":") + 1)) as { detail?: unknown }; if (typeof corpo.detail === "string") return corpo.detail; } catch { /* API sem mensagem estruturada. */ } return "Não foi possível concluir. Confira o arquivo e atualize a prévia se houver conflito. A mesma tentativa mantém sua chave para evitar duplicação."; }
