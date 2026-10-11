"use server";

import { revalidatePath } from "next/cache";
import { unstable_rethrow } from "next/navigation";
import { apiPost, apiPatch } from "./api";
import type { CadastroResultado } from "./cadastro-types";

type Operacao = "pessoa" | "contato" | "chave";
type Dados = Record<string, string | number | boolean | null>;
const texto = (f: FormData, k: string) => String(f.get(k) ?? "").trim();
function dadosPessoa(form: FormData, editando: boolean): Dados {
  const dados: Dados = Object.fromEntries(["nome", "tipo", "documento", "apelido", "endereco", "observacoes"].map(k => [k, texto(form, k)]));
  for (const k of ["prazo_dias", "prioridade", "tolerancia_credito"]) dados[k] = Number(form.get(k) || (k === "prioridade" ? 2 : 0));
  if (editando) dados.ativo = form.get("ativo") === "on";
  return dados;
}
function dadosFilho(form: FormData, operacao: Operacao): Dados {
  const campos = operacao === "contato" ? ["nome", "telefone", "email", "cargo"] : ["chave", "tipo", "titular", "banco", "agencia", "conta", "tipo_conta", "categoria"];
  const dados: Dados = Object.fromEntries(campos.map(k => [k, texto(form, k)]));
  dados.principal = form.get("principal") === "on";
  dados.ativo = form.get("ativo") === "on";
  if (operacao === "chave") dados.validade = texto(form, "validade") || null;
  return dados;
}
function mensagemErro(erro: unknown): string {
  const mensagem = erro instanceof Error ? erro.message : "";
  try {
    const detalhe = JSON.parse(mensagem.slice(mensagem.indexOf(":") + 1)) as { detail?: unknown };
    if (typeof detalhe.detail === "string") return detalhe.detail;
    if (Array.isArray(detalhe.detail)) {
      const campos = detalhe.detail as { loc?: unknown[]; msg?: string }[];
      return campos.map(c => {
        const campo = c.loc?.filter(l => typeof l === "string" && l !== "body").join(" · ") ?? "Campo";
        const explicacao = c.msg?.startsWith("Value error, ") ? c.msg.slice(13) : "valor inválido; confira o preenchimento";
        return `${campo}: ${explicacao}`;
      }).join(". ") || "Confira os campos.";
    }
  } catch { /* Resposta sem JSON: apresentar mensagem segura. */ }
  return "Não foi possível salvar. Confira os campos e sua permissão; tente novamente.";
}
function caminhoFilho(operacao: Operacao, pessoaId: number, itemId: number | null): string {
  const caminho = `/pessoas/${pessoaId}/${operacao === "contato" ? "contatos" : "chaves-pix"}`;
  return itemId === null ? caminho : `${caminho}/${itemId}`;
}
export async function salvarCadastro(operacao: Operacao, pessoaId: number | null, itemId: number | null, form: FormData): Promise<CadastroResultado> {
  if (operacao !== "pessoa" && pessoaId === null) return { ok: false, mensagem: "Salve o cadastro antes de adicionar contatos ou chaves." };
  const editando = operacao === "pessoa" ? pessoaId !== null : itemId !== null;
  const caminho = operacao === "pessoa" ? (pessoaId === null ? "/pessoas" : `/pessoas/${pessoaId}`) : caminhoFilho(operacao, pessoaId as number, itemId);
  const dados = operacao === "pessoa" ? dadosPessoa(form, editando) : dadosFilho(form, operacao);
  try {
    if (editando) await apiPatch(caminho, dados);
    else await apiPost(caminho, dados);
    revalidatePath("/cadastro");
    revalidatePath("/links");
    return { ok: true, mensagem: "Dados salvos." };
  } catch (erro) {
    unstable_rethrow(erro);
    return { ok: false, mensagem: mensagemErro(erro) };
  }
}
