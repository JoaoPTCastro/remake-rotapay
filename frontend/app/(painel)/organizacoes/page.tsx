import Link from "next/link";
import { unstable_rethrow } from "next/navigation";
import { apiGet, usuarioAtual } from "../../../lib/api";
import type { Organizacao } from "../../../lib/organizacoes-types";
import { AceitarConviteForm, CriarOrganizacaoForm, SelecionarOrganizacaoForm } from "./OrganizacoesForms";
import styles from "./Organizacoes.module.css";

export default async function OrganizacoesPage() {
  const me = await usuarioAtual();
  let organizacoes: Organizacao[] | null;
  try { organizacoes = await apiGet("/organizacoes") as Organizacao[]; }
  catch (erro) { unstable_rethrow(erro); organizacoes = null; }
  const podeCriar = me.perfil === "admin" && organizacoes?.some(org => org.id === 1 && org.perfil === "admin");
  return <div className={styles.stack}>
    <header><h1>Organizações e fornecedores</h1><p className="muted">Suas lojas, vínculos e convites.</p></header>
    <div className={styles.notice}>Escolha a loja antes de operar. Cada ambiente financeiro possui registros e arquivos próprios. O vínculo de fornecedor não concede acesso ao financeiro interno da loja.</div>
    <section className={styles.box}><h2>Seus vínculos</h2>{organizacoes === null ? <p role="alert" className="error">Não foi possível carregar suas organizações. Atualize a página para tentar novamente.</p> : organizacoes.length === 0 ? <p className="muted">Você ainda não possui vínculos. Se recebeu um convite de uma loja, aceite o código abaixo.</p> : <div className={styles.list}>{organizacoes.map(org => <article key={org.id} className={styles.row}><div><strong>{org.nome}</strong><p className={styles.status}>Vínculo: {org.perfil === "fornecedor" ? "Fornecedor" : org.perfil === "admin" ? "Administrador" : org.perfil} · {org.financeiro_habilitado ? "Ambiente preparado" : "Ambiente financeiro pendente"}</p></div><Link href={`/organizacoes/${org.id}`}>Consultar organização</Link>{org.perfil === "fornecedor" && <Link href={`/organizacoes/${org.id}/fornecedor`}>Abrir portal do fornecedor</Link>}{org.financeiro_habilitado && ["admin", "financeiro", "operador", "consulta"].includes(org.perfil) && <SelecionarOrganizacaoForm organizacaoId={org.id} />}</article>)}</div>}</section>
    {podeCriar && <section className={styles.box}><h2>Nova organização</h2><CriarOrganizacaoForm /></section>}
    <section className={styles.box}><h2>Aceitar convite de fornecedor</h2><p className="muted">Use o código recebido da loja. Sua conta precisa usar o email convidado.</p><AceitarConviteForm /></section>
  </div>;
}
