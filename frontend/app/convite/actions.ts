"use server";

import { unstable_rethrow } from "next/navigation";
import { API_URL } from "../../lib/api";

export type EstadoCadastroConvite = { ok: boolean; mensagem: string };

function cadastroValido(token: string, nome: string, senha: string) {
  return token.length >= 32 && token.length <= 128 && nome.length > 0 && nome.length <= 120 && senha.length >= 8 && senha.length <= 128;
}

export async function registrarFornecedor(_: EstadoCadastroConvite, form: FormData): Promise<EstadoCadastroConvite> {
  const token = String(form.get("token") ?? "").trim();
  const nome = String(form.get("nome") ?? "").trim();
  const senha = String(form.get("senha") ?? "");
  if (!cadastroValido(token, nome, senha)) {
    return { ok: false, mensagem: "Confira o código recebido, seu nome e uma senha entre 8 e 128 caracteres." };
  }
  if (senha !== String(form.get("confirmacao") ?? "")) return { ok: false, mensagem: "As senhas precisam ser iguais." };
  try {
    const resposta = await fetch(`${API_URL}/organizacoes/convites/registrar`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, nome, senha }), cache: "no-store", redirect: "error",
      signal: AbortSignal.timeout(15_000),
    });
    if (resposta.ok) return { ok: true, mensagem: "Conta criada e convite aceito. Entre usando o email que recebeu o convite e sua nova senha." };
    const mensagens: Record<number, string> = {
      409: "Este convite não pode criar uma nova conta. Se já possui cadastro, entre e aceite em Organizações; caso contrário, solicite um novo convite.",
      410: "O convite expirou ou foi revogado. Solicite um novo código à loja.",
      422: "Confira os campos e o código do convite.",
      429: "Aguarde antes de tentar novamente.",
    };
    return { ok: false, mensagem: mensagens[resposta.status] ?? "Convite indisponível. Confira o código ou solicite um novo à loja." };
  } catch (erro) {
    unstable_rethrow(erro);
    return { ok: false, mensagem: "Não foi possível concluir o cadastro. Tente novamente mais tarde." };
  }
}
