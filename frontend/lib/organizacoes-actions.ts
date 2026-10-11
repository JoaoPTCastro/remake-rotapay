"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect, unstable_rethrow } from "next/navigation";
import { apiPost } from "./api";
import type { EstadoOrganizacao } from "./organizacoes-types";

const texto = (form: FormData, campo: string) => String(form.get(campo) ?? "").trim();
const idValido = (id: number) => Number.isSafeInteger(id) && id > 0;

async function executar(tarefa: () => Promise<EstadoOrganizacao>): Promise<EstadoOrganizacao> {
  try {
    const resultado = await tarefa();
    revalidatePath("/organizacoes", "layout");
    return resultado;
  } catch (erro) {
    unstable_rethrow(erro);
    const status = (erro as { status?: number })?.status;
    const mensagens: Record<number, string> = {
      403: "Seu acesso não permite esta ação. Para aceitar um convite, use a conta do email convidado.",
      404: "Organização ou convite indisponível para sua conta.",
      409: "Convite indisponível ou operação concorrente. Confira a validade e seus vínculos antes de tentar novamente.",
      410: "O convite expirou ou foi revogado. Solicite um novo convite à loja.",
      422: "Confira os campos informados e tente novamente.",
      429: "Aguarde antes de tentar novamente.",
    };
    return { ok: false, mensagem: mensagens[status ?? 0] ?? "Não foi possível concluir. Tente novamente mais tarde." };
  }
}

export async function criarOrganizacao(_: EstadoOrganizacao, form: FormData) {
  const nome = texto(form, "nome");
  if (nome.length < 2 || nome.length > 120) return { ok: false, mensagem: "Informe um nome entre 2 e 120 caracteres." };
  return executar(async () => {
    await apiPost("/organizacoes", { nome });
    return { ok: true, mensagem: "Organização criada. Prepare o ambiente financeiro na página da organização." };
  });
}

export async function criarConvite(organizacaoId: number, _: EstadoOrganizacao, form: FormData) {
  const nome = texto(form, "nome");
  const email = texto(form, "email");
  if (!idValido(organizacaoId) || nome.length < 2 || nome.length > 120 || email.length > 160 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return { ok: false, mensagem: "Confira o nome e o email do fornecedor." };
  }
  return executar(async () => {
    const resposta = await apiPost(`/organizacoes/${organizacaoId}/convites`, { nome, email }) as { token: string };
    return { ok: true, mensagem: "Convite criado. O código aparece somente agora. Nenhum email foi enviado.", token: resposta.token };
  });
}

export async function aceitarConvite(_: EstadoOrganizacao, form: FormData) {
  const token = texto(form, "token");
  if (token.length < 32 || token.length > 128) return { ok: false, mensagem: "Informe o código do convite recebido da loja." };
  return executar(async () => {
    await apiPost("/organizacoes/convites/aceitar", { token });
    return { ok: true, mensagem: "Convite aceito. Seu vínculo com a loja foi registrado." };
  });
}

export async function revogarConvite(organizacaoId: number, conviteId: number, _: EstadoOrganizacao, form: FormData) {
  if (!idValido(organizacaoId) || !idValido(conviteId) || form.get("confirmar") !== "on") return { ok: false, mensagem: "Confirme a revogação do convite." };
  return executar(async () => {
    await apiPost(`/organizacoes/${organizacaoId}/convites/${conviteId}/revogar`);
    return { ok: true, mensagem: "Convite revogado. O código anterior não pode mais ser usado." };
  });
}

export async function provisionarOrganizacao(organizacaoId: number, _: EstadoOrganizacao, form: FormData) {
  if (!idValido(organizacaoId) || form.get("confirmar") !== "on") return { ok: false, mensagem: "Confirme a criação do ambiente vazio desta loja." };
  return executar(async () => {
    await apiPost(`/organizacoes/${organizacaoId}/provisionar`);
    return { ok: true, mensagem: "Ambiente financeiro preparado. Agora você pode entrar nesta loja." };
  });
}

export async function selecionarOrganizacao(organizacaoId: number, _: EstadoOrganizacao, _form: FormData) {
  if (!idValido(organizacaoId)) return { ok: false, mensagem: "Organização inválida." };
  return executar(async () => {
    const resposta = await apiPost(`/organizacoes/${organizacaoId}/selecionar`) as { access_token: string; user: { perfil: string } };
    const jar = await cookies();
    jar.set("token", resposta.access_token, { httpOnly: true, path: "/", maxAge: 8 * 3600, sameSite: "lax" });
    jar.set("perfil", resposta.user.perfil, { path: "/", maxAge: 8 * 3600, sameSite: "lax" });
    revalidatePath("/", "layout");
    redirect("/");
  });
}
