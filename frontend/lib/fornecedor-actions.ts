"use server";

import { revalidatePath } from "next/cache";
import { unstable_rethrow } from "next/navigation";
import { apiPatch, apiPost, apiPut } from "./api";
import type { EstadoOrganizacao } from "./organizacoes-types";

const texto = (form: FormData, campo: string) => String(form.get(campo) ?? "").trim();
const valido = (id: number) => Number.isSafeInteger(id) && id > 0;
async function executar(org: number, tarefa: () => Promise<unknown>, mensagem: string): Promise<EstadoOrganizacao> {
  if (!valido(org)) return { ok: false, mensagem: "Loja inválida." };
  try {
    await tarefa();
    revalidatePath(`/organizacoes/${org}`, "layout");
    return { ok: true, mensagem };
  } catch (erro) {
    unstable_rethrow(erro);
    const status = (erro as { status?: number }).status;
    const mensagens: Record<number, string> = {
      403: "Seu vínculo não permite esta ação. Confira seu acesso com a loja.",
      404: "Cadastro ou pagamento indisponível para sua conta nesta loja.",
      409: "A alteração conflita com o estado atual. Atualize a página e confira o cadastro, os administradores ativos ou a declaração existente.",
      422: "Confira os campos. Chaves temporárias exigem validade e uma chave principal precisa estar ativa.",
      429: "Aguarde antes de tentar novamente.",
    };
    return { ok: false, mensagem: mensagens[status ?? 0] ?? "Não foi possível concluir. Tente novamente mais tarde." };
  }
}
export async function vincularCadastro(org: number, usuario: number, _: EstadoOrganizacao, form: FormData) {
  const pessoa = Number(form.get("pessoa_id"));
  if (!valido(usuario) || !valido(pessoa) || form.get("confirmar") !== "on") return { ok: false, mensagem: "Escolha o cadastro e confirme o vínculo." };
  return executar(org, () => apiPut(`/organizacoes/${org}/fornecedores/${usuario}/cadastro`, { pessoa_id: pessoa }), "Fornecedor vinculado ao cadastro desta loja.");
}
export async function atualizarMembro(org: number, usuario: number, _: EstadoOrganizacao, form: FormData) {
  const perfil = texto(form, "perfil");
  if (!valido(usuario) || !["admin", "financeiro", "operador", "consulta", "fornecedor"].includes(perfil) || form.get("confirmar") !== "on") return { ok: false, mensagem: "Confira o perfil e confirme a alteração do vínculo." };
  return executar(org, () => apiPatch(`/organizacoes/${org}/membros/${usuario}`, { perfil, ativo: form.get("ativo") === "on" }), "Vínculo atualizado somente nesta loja.");
}
export async function salvarChave(org: number, chaveId: number | null, _: EstadoOrganizacao, form: FormData) {
  const campos = ["chave", "tipo", "titular", "banco", "agencia", "conta", "tipo_conta", "categoria"];
  const corpo = { ...Object.fromEntries(campos.map(campo => [campo, texto(form, campo)])), validade: texto(form, "validade") || null, principal: form.get("principal") === "on", ativo: form.get("ativo") === "on" };
  if (!texto(form, "chave") || (chaveId !== null && !valido(chaveId))) return { ok: false, mensagem: "Informe uma chave PIX válida." };
  const caminho = `/organizacoes/${org}/portal-fornecedor/chaves-pix`;
  return executar(org, () => chaveId === null ? apiPost(caminho, corpo) : apiPatch(`${caminho}/${chaveId}`, corpo), "Chave PIX atualizada nesta loja.");
}
export async function confirmarRecebimento(org: number, pagamento: number, _: EstadoOrganizacao, form: FormData) {
  if (!valido(pagamento) || texto(form, "referencia").length < 3 || texto(form, "referencia").length > 220 || texto(form, "observacao").length > 1000 || form.get("confirmar") !== "on") return { ok: false, mensagem: "Informe uma referência entre 3 e 220 caracteres e confirme que recebeu este pagamento." };
  return executar(org, () => apiPost(`/organizacoes/${org}/portal-fornecedor/pagamentos/${pagamento}/confirmar-recebimento`, { referencia: texto(form, "referencia"), observacao: texto(form, "observacao") }), "Declaração de recebimento registrada. Ela não representa confirmação bancária nem aplica abatimento automaticamente.");
}

export async function adicionarMembro(org: number, _: EstadoOrganizacao, form: FormData) {
  const email = texto(form, "email");
  const perfil = texto(form, "perfil");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 160 || !["admin", "financeiro", "operador", "consulta"].includes(perfil)) return { ok: false, mensagem: "Informe o email da conta existente e seu perfil nesta loja." };
  return executar(org, () => apiPost(`/organizacoes/${org}/membros`, { email, perfil }), "Membro adicionado à equipe desta loja.");
}
