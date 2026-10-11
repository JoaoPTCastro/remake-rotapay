"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { apiPost, apiPatch } from "./api";

export async function createMovimentacao(form: FormData) {
  const mov = await apiPost("/movimentacoes", {
    data_pix: String(form.get("data_pix")),
    valor: Number(form.get("valor")),
    remetente: String(form.get("remetente") ?? ""),
    representante_id: form.get("representante_id") ? Number(form.get("representante_id")) : null,
    destinatario: String(form.get("destinatario") ?? ""),
    fornecedor_id: form.get("fornecedor_id") ? Number(form.get("fornecedor_id")) : null,
    observacao: String(form.get("observacao") ?? ""),
    autor: String(form.get("autor") ?? ""),
    forma_pagamento: String(form.get("forma_pagamento") || "PIX"),
    natureza: String(form.get("natureza") || "DESPESA"),
  });
  revalidatePath("/controle");
  redirect(`/movimentacoes/${(mov as { id: number }).id}`);
}

export async function cancelarMovimentacao(id: number, form: FormData) {
  await apiPost(`/movimentacoes/${id}/cancelar`, { senha: String(form.get("senha") ?? "") });
  revalidatePath("/movimentacoes");
  revalidatePath("/controle");
  revalidatePath("/");
}

export async function createConciliacao(form: FormData) {
  await apiPost("/conciliacoes", {
    movimentacao_id: Number(form.get("movimentacao_id")),
    alvo_tipo: String(form.get("alvo_tipo")),
    alvo_id: Number(form.get("alvo_id")),
    valor: Number(form.get("valor")),
  });
  revalidatePath("/conciliacoes");
  revalidatePath("/");
}

export async function estornarConciliacao(id: number, form: FormData) {
  await apiPost(`/conciliacoes/${id}/estornar`, {
    motivo: String(form.get("motivo") ?? ""),
    senha: String(form.get("senha") ?? ""),
  });
  revalidatePath("/conciliacoes");
  revalidatePath("/");
}

export async function createProjecao(form: FormData) {
  await apiPost("/projecoes", {
    representante_id: Number(form.get("representante_id")),
    fornecedor_id: Number(form.get("fornecedor_id")),
    valor_projetado: Number(form.get("valor_projetado")),
    data_prevista: String(form.get("data_prevista") || "") || null,
    observacao: String(form.get("observacao") ?? ""),
  });
  revalidatePath("/projecoes");
  revalidatePath("/conciliacoes");
}

export async function aplicarProjecoes() {
  await apiPost("/projecoes/automaticas?aplicar=true");
  revalidatePath("/projecoes");
}

export async function createLancamento(form: FormData) {
  await apiPost("/lancamentos", {
    tipo: String(form.get("tipo")),
    natureza: String(form.get("natureza") ?? ""),
    valor: Number(form.get("valor")),
    data: String(form.get("data")),
    representante_id: form.get("representante_id") ? Number(form.get("representante_id")) : null,
    fornecedor_id: form.get("fornecedor_id") ? Number(form.get("fornecedor_id")) : null,
    descricao: String(form.get("descricao") ?? ""),
  });
  revalidatePath("/lancamentos");
  revalidatePath("/conciliacoes");
}

export async function createLink(form: FormData) {
  const vf = String(form.get("valor_fixo") ?? "");
  await apiPost("/links", {
    representante_id: Number(form.get("representante_id")),
    fornecedor_id: Number(form.get("fornecedor_id")),
    valor_fixo: vf ? Number(vf) : null,
  });
  revalidatePath("/links");
}

export async function revokeLink(id: number) {
  await apiPost(`/links/${id}/revogar`);
  revalidatePath("/links");
}

export async function cobrarLink(id: number) {
  await apiPost(`/links/${id}/cobrar`);
  revalidatePath("/links");
}

const txt = (form: FormData, k: string) => String(form.get(k) ?? "");
const num = (form: FormData, k: string) => Number(form.get(k) || 0);

export async function etapaComprovante(mid: number, cid: number, etapa: string) {
  await apiPatch(`/movimentacoes/comprovantes/${cid}`, { etapa });
  revalidatePath(`/movimentacoes/${mid}`);
}

export async function createPessoa(form: FormData) {
  const tipo = String(form.get("tipo"));
  await apiPost(tipo === "fornecedor" ? "/fornecedores" : "/representantes", {
    tipo,
    nome: String(form.get("nome")),
    documento: txt(form, "documento"),
    telefone: txt(form, "telefone"),
    email: txt(form, "email"),
    apelido: txt(form, "apelido"),
    endereco: txt(form, "endereco"),
    chave_pix: txt(form, "chave_pix"),
    banco: txt(form, "banco"),
    conta: txt(form, "conta"),
    titular_chave: txt(form, "titular_chave"),
    prazo_dias: num(form, "prazo_dias"),
    tolerancia_credito: num(form, "tolerancia_credito"),
    prioridade: Number(form.get("prioridade") || 2),
  });
  revalidatePath("/pessoas");
  revalidatePath("/cadastro");
}

export async function createUsuario(form: FormData) {
  await apiPost("/auth/users", {
    nome: String(form.get("nome")),
    email: String(form.get("email")),
    senha: String(form.get("senha")),
    perfil: String(form.get("perfil") || "operador"),
  });
  revalidatePath("/conta");
}

export async function updateUsuario(id: number, form: FormData) {
  await apiPatch(`/auth/users/${id}`, {
    perfil: String(form.get("perfil")),
    ativo: form.get("ativo") === "on",
  });
  revalidatePath("/conta");
}

export async function resetUsuarioSenha(id: number, form: FormData) {
  await apiPost(`/auth/users/${id}/password`, { senha: String(form.get("senha") ?? "") });
  revalidatePath("/conta");
}

export async function trocarMinhaSenha(form: FormData) {
  await apiPost("/auth/me/password", {
    senha_atual: String(form.get("senha_atual") ?? ""),
    nova: String(form.get("nova") ?? ""),
  });
  (await cookies()).delete("token");
  (await cookies()).delete("perfil");
  redirect("/login");
}

export async function salvarLoja(form: FormData) {
  const corpo: Record<string, string> = {};
  for (const k of ["nome", "documento", "telefone", "email", "endereco"]) {
    const v = String(form.get(k) ?? "").trim();
    if (v) corpo[k] = v;
  }
  await apiPatch("/loja", corpo);
  revalidatePath("/conta");
  revalidatePath("/");
}
