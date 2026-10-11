"use server";
import { revalidatePath } from "next/cache";
import { unstable_rethrow } from "next/navigation";
import { apiGet, apiPost } from "./api";
import type { CreditoOrigem, CreditoNotas, CreditoResultado, CreditoConsulta } from "./creditos-types";
const texto = (f: FormData, k: string) => String(f.get(k) ?? "").trim();
function erroSeguro(erro: unknown): string {
  const mensagem = erro instanceof Error ? erro.message : "";
  try { const detalhe = JSON.parse(mensagem.slice(mensagem.indexOf(":") + 1)) as { detail?: unknown }; if (typeof detalhe.detail === "string") return detalhe.detail; }
  catch { /* Mensagens seguras sem expor corpo da requisição nem stack trace. */ }
  return "Não foi possível concluir. Confira os campos, sua permissão e tente novamente.";
}
function confirmacaoFornecedor(form: FormData) { return { fornecedor_confirmou: form.get("fornecedor_confirmou") === "on", referencia_confirmacao: texto(form, "referencia_confirmacao") || null }; }
async function executar(caminho: string, dados: unknown): Promise<CreditoResultado> {
  try { const registro = await apiPost(caminho, dados) as { id?: number }; for (const rota of ["/creditos", "/pagamentos", "/acertos", "/notas"]) revalidatePath(rota); return { ok: true, mensagem: "Registro salvo.", id: registro.id }; }
  catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: erroSeguro(erro) }; }
}
export async function reconhecerCredito(acertoId: number, chave: string, form: FormData): Promise<CreditoResultado> {
  if (form.get("confirmacao") !== "on") return { ok: false, mensagem: "Confirme o reconhecimento explícito deste crédito de conta." };
  return executar("/creditos", { acerto_id: acertoId, pagamento_id: Number(form.get("pagamento_id")), valor: Number(form.get("valor")), data: texto(form, "data"), referencia: texto(form, "referencia"), observacao: texto(form, "observacao"), chave_idempotencia: chave, confirmacao: true, ...confirmacaoFornecedor(form) });
}
export async function aplicarCredito(creditoId: number, chave: string, form: FormData): Promise<CreditoResultado> {
  if (form.get("confirmacao") !== "on") return { ok: false, mensagem: "Confirme a aplicação na nota selecionada." };
  return executar(`/creditos/${creditoId}/aplicacoes`, { nota_id: Number(form.get("nota_id")), valor: Number(form.get("valor")), data: texto(form, "data"), referencia: texto(form, "referencia"), observacao: texto(form, "observacao"), chave_idempotencia: chave, ...confirmacaoFornecedor(form) });
}
export async function desfazerCredito(creditoId: number, aplicacaoId: number | null, form: FormData): Promise<CreditoResultado> { return executar(aplicacaoId === null ? `/creditos/${creditoId}/reverter` : `/creditos/${creditoId}/aplicacoes/${aplicacaoId}/estornar`, { senha: String(form.get("senha") ?? ""), motivo: texto(form, "motivo") }); }
export async function consultarOrigemCredito(acertoId: number, offset = 0): Promise<CreditoConsulta<CreditoOrigem>> {
  try { return { ok: true, dados: await apiGet(`/creditos/recursos-origem?acerto_id=${acertoId}&offset=${Math.max(0, offset)}&limit=50`) as CreditoOrigem }; }
  catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: erroSeguro(erro) }; }
}
export async function consultarNotasCredito(creditoId: number, offset = 0): Promise<CreditoConsulta<CreditoNotas>> {
  try { return { ok: true, dados: await apiGet(`/creditos/${creditoId}/notas-elegiveis?offset=${Math.max(0, offset)}&limit=50`) as CreditoNotas }; }
  catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: erroSeguro(erro) }; }
}
