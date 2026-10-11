import { unstable_rethrow } from "next/navigation";
import type { PreferenciaTabela } from "../../../lib/configuracoes-types";
import { apiGet, perfil } from "../../../lib/api";
import type { CadastroPessoa } from "../../../lib/cadastro-types";
import Link from "next/link";
import AlertasCadastro, { type FiltrosAlertas } from "./AlertasCadastro";
import { carregarPreferencia } from "../../../lib/configuracoes-api";
import CadastroManager from "./CadastroManager";

export default async function Cadastro({ searchParams }: { searchParams: Promise<{ aba?: string; pessoa_id?: string } & FiltrosAlertas> }) {
  const filtros = await searchParams; let preferencia: PreferenciaTabela; let pessoas: CadastroPessoa[]; let usuarioPerfil: string; try { [preferencia, pessoas, usuarioPerfil] = await Promise.all([carregarPreferencia("cadastros"), apiGet("/pessoas") as Promise<CadastroPessoa[]>, perfil()]); } catch (erro) { unstable_rethrow(erro); return <p role="alert">Não foi possível carregar cadastros e preferências. Recarregue a página.</p>; }
  const { aba, pessoa_id } = filtros;
  const preferenciaEfetiva = preferenciaDaAba(preferencia, aba);
  return <><p><Link href="/intercambio">Importar / exportar CSV e modelos</Link></p><AlertasCadastro filtros={filtros} /><CadastroManager key={`${aba ?? "geral"}-${pessoa_id ?? "lista"}-${JSON.stringify(preferenciaEfetiva.filtros)}`} preferencia={preferenciaEfetiva} pessoas={pessoas} filtroInicial={aba === "pessoas" ? "representante" : aba === "fornecedores" ? "fornecedor" : "todos"} abaInicial={aba === "chaves" ? "financeiro" : "dados"} podeEditar={["admin", "financeiro"].includes(usuarioPerfil)} pessoaInicial={Number(pessoa_id) || null} /></>;
}

function preferenciaDaAba(preferencia: PreferenciaTabela, aba: string | undefined): PreferenciaTabela { const tipo = aba === "pessoas" ? "representante" : aba === "fornecedores" ? "fornecedor" : null; return tipo ? { ...preferencia, filtros: { ...preferencia.filtros, tipo } } : preferencia; }
