"use server";
import { revalidatePath } from "next/cache";
import { unstable_rethrow } from "next/navigation";
import { apiPost } from "./api";
import type { ItemClassificacaoLegado, PreviaLegado, ReciboLegado, ResultadoLegado } from "./legado-types";
function falha(erro: unknown): ResultadoLegado<never> {
  unstable_rethrow(erro);
  const status = (erro as { status?: number })?.status;
  return { ok: false, mensagem: status === 409 ? "A origem ou sua classificação mudou. Atualize a página e revise novamente antes de confirmar." : status === 403 ? "Classificar exige administrador ou financeiro." : status === 422 ? "Confira a decisão, a evidência e a relação selecionada. Nada foi classificado." : "Não foi possível concluir. Atualize a lista e confira os recibos antes de repetir a operação." };
}
export async function prepararClassificacaoLegado(item: ItemClassificacaoLegado): Promise<ResultadoLegado<PreviaLegado>> {
  try { return { ok: true, dados: await apiPost("/legado/previa", { itens: [item] }) as PreviaLegado }; }
  catch (erro) { return falha(erro); }
}
export async function confirmarClassificacaoLegado(item: ItemClassificacaoLegado, hashPrevia: string, chave: string): Promise<ResultadoLegado<ReciboLegado>> {
  try {
    const dados = await apiPost("/legado/classificacoes", { itens: [item], hash_previa: hashPrevia, chave_idempotencia: chave }) as ReciboLegado;
    revalidatePath("/legado");
    return { ok: true, dados };
  } catch (erro) { return falha(erro); }
}
