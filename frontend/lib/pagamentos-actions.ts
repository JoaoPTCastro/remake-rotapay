"use server";
import { revalidatePath } from "next/cache";
import { unstable_rethrow } from "next/navigation";
import { apiGet, apiPost, apiDelete } from "./api";
import type { Pagamento, PagamentoResultado, NotasConsultaResultado } from "./pagamentos-types";
import { notasElegiveis } from "./pagamento-notas";
import type { RelacaoNota } from "./notas-types";
const texto = (f: FormData, k: string) => String(f.get(k) ?? "").trim();
const idOpcional = (f: FormData, k: string) => texto(f, k) ? Number(f.get(k)) : null;
function erroSeguro(erro: unknown): string {
  const mensagem = erro instanceof Error ? erro.message : "";
  try { const detalhe = JSON.parse(mensagem.slice(mensagem.indexOf(":") + 1)) as { detail?: unknown }; if (typeof detalhe.detail === "string") return detalhe.detail; }
  catch { /* Não expor mensagens internas nem os dados enviados. */ }
  return "Não foi possível registrar. Confira os campos, sua permissão e tente novamente.";
}
async function executar(caminho: string, dados: unknown): Promise<PagamentoResultado> {
  try { const registro = await apiPost(caminho, dados) as { id?: number }; revalidatePath("/pagamentos"); revalidatePath("/notas"); return { ok: true, mensagem: "Registro salvo.", id: registro.id }; }
  catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: erroSeguro(erro) }; }
}
export async function criarPagamento(chave: string, form: FormData): Promise<PagamentoResultado> {
  if (form.get("declaracao_novo_pagamento") !== "on") return { ok: false, mensagem: "Confirme que está registrando um novo evento de pagamento." };
  return executar("/pagamentos", { ...metadadosPagamento(form), forma_id: idOpcional(form, "forma_id"), operacao_id: idOpcional(form, "operacao_id"), tipo: texto(form, "tipo"), forma: texto(form, "forma"), valor: Number(form.get("valor")), data: texto(form, "data"), cliente_id: idOpcional(form, "cliente_id"), fornecedor_id: idOpcional(form, "fornecedor_id"), pagamento_origem_id: idOpcional(form, "pagamento_origem_id"), referencia_externa: texto(form, "referencia_externa"), observacao: texto(form, "observacao"), chave_idempotencia: chave, declaracao_novo_pagamento: true });
}
export async function aplicarPagamento(pagamentoId: number, chave: string, form: FormData): Promise<PagamentoResultado> {
  if (form.get("confirmacao") !== "on") return { ok: false, mensagem: "Confirme a aplicação na nota selecionada." };
  if (texto(form, "relacao") === "fornecedor" && (form.get("fornecedor_confirmou") !== "on" || texto(form, "referencia_confirmacao").length < 3)) return { ok: false, mensagem: "Registre a conferência e concordância do fornecedor e sua referência de confirmação." };
  return executar(`/pagamentos/${pagamentoId}/aplicacoes`, { nota_id: Number(form.get("nota_id")), relacao: texto(form, "relacao"), valor: Number(form.get("valor")), data: texto(form, "data"), referencia: texto(form, "referencia"), observacao: texto(form, "observacao"), chave_idempotencia: chave, fornecedor_confirmou: form.get("fornecedor_confirmou") === "on", referencia_confirmacao: texto(form, "referencia_confirmacao") || null });
}
export async function reverterPagamento(pagamentoId: number, aplicacaoId: number | null, form: FormData): Promise<PagamentoResultado> {
  return executar(aplicacaoId === null ? `/pagamentos/${pagamentoId}/cancelar` : `/pagamentos/${pagamentoId}/aplicacoes/${aplicacaoId}/estornar`, { senha: String(form.get("senha") ?? ""), motivo: texto(form, "motivo") });
}
export async function anexarPagamento(pagamentoId: number, form: FormData): Promise<PagamentoResultado> {
  const arquivo = form.get("f");
  if (!(arquivo instanceof File) || !arquivo.size || arquivo.size > 10 * 1024 * 1024) return { ok: false, mensagem: "Selecione um arquivo de até 10 MB." };
  return executar(`/pagamentos/${pagamentoId}/anexos`, form);
}
export async function removerAnexoPagamento(pagamentoId: number, anexoId: number): Promise<PagamentoResultado> {
  try { await apiDelete(`/pagamentos/${pagamentoId}/anexos/${anexoId}`); revalidatePath("/pagamentos"); return { ok: true, mensagem: "Anexo removido." }; }
  catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: erroSeguro(erro) }; }
}

export async function listarNotasAplicacao(pagamentoId: number, relacao: RelacaoNota, offset: number): Promise<NotasConsultaResultado> {
  if (relacao !== "cliente" && relacao !== "fornecedor") return { ok: false, mensagem: "Relação inválida." };
  const inicio = Number.isSafeInteger(offset) && offset >= 0 ? offset : 0;
  try {
    const pagamento = await apiGet(`/pagamentos/${pagamentoId}`) as Pagamento;
    const pessoaId = relacao === "cliente" ? pagamento.cliente_id : pagamento.fornecedor_id;
    const pagina = await notasElegiveis(pessoaId, relacao, inicio);
    return { ok: true, pagina };
  } catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: "Não foi possível carregar as notas. Tente novamente." }; }
}

function metadadosPagamento(form: FormData) { const dataHora = texto(form, "data_hora_transacao"); const fuso = texto(form, "fuso_transacao"); return { data_hora_transacao: dataHora ? `${dataHora}${fuso}` : null, remetente: texto(form, "remetente") || null, favorecido: texto(form, "favorecido") || null, intermediador: texto(form, "intermediador") || null }; }
