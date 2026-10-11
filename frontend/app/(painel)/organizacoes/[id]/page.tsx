import Link from "next/link";
import { notFound, unstable_rethrow } from "next/navigation";
import { apiGet } from "../../../../lib/api";
import type { ConviteFornecedor, MembroOrganizacao, Organizacao } from "../../../../lib/organizacoes-types";
import { CriarConviteForm, RevogarConviteForm, SelecionarOrganizacaoForm, ProvisionarOrganizacaoForm } from "../OrganizacoesForms";
import styles from "../Organizacoes.module.css";
import { MembroForm, VincularCadastroForm, AdicionarMembroForm } from "../FornecedorForms";
import type { FornecedoresLoja } from "../../../../lib/fornecedor-types";

// A API armazena UTC e pode serializar sem o indicador de fuso.
const instanteUtc = (valor: string) => new Date(/(?:Z|[+-]\d{2}:?\d{2})$/i.test(valor) ? valor : `${valor}Z`);
function situacao(convite: ConviteFornecedor) {
  if (convite.accepted_at) return "Aceito";
  if (convite.revoked_at) return "Revogado";
  return instanteUtc(convite.expires_at).getTime() <= Date.now() ? "Expirado" : "Pendente";
}
const nomePerfil = (perfil: string) => ({ fornecedor: "Fornecedor", admin: "Administrador" }[perfil] ?? perfil);
const data = (valor: string) => instanteUtc(valor).toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" });

export default async function OrganizacaoPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[1-9]\d*$/.test(id) || !Number.isSafeInteger(Number(id))) notFound();
  let org: Organizacao;
  try { org = await apiGet(`/organizacoes/${id}`) as Organizacao; }
  catch (erro) { unstable_rethrow(erro); return <div className={styles.box}><h1>Organização indisponível</h1><p role="alert">Seu acesso pode não permitir consultar esta organização. Nenhum dado foi carregado.</p><Link href="/organizacoes">Voltar aos seus vínculos</Link></div>; }
  let membros: MembroOrganizacao[] | null = null;
  let convites: ConviteFornecedor[] | null = null;
  let fornecedores: FornecedoresLoja | null = null;
  if (org.perfil === "admin") {
    const resultados = await Promise.allSettled([apiGet(`/organizacoes/${id}/membros`), apiGet(`/organizacoes/${id}/convites`), apiGet(`/organizacoes/${id}/fornecedores`)]);
    for (const resultado of resultados) if (resultado.status === "rejected") unstable_rethrow(resultado.reason);
    membros = resultados[0].status === "fulfilled" ? resultados[0].value as MembroOrganizacao[] : null;
    convites = resultados[1].status === "fulfilled" ? resultados[1].value as ConviteFornecedor[] : null;
    fornecedores = resultados[2].status === "fulfilled" ? resultados[2].value as FornecedoresLoja : null;
  }
  return <div className={styles.stack}>
    <header><Link href="/organizacoes">← Seus vínculos</Link><h1>{org.nome}</h1><p className="muted">Seu vínculo: {nomePerfil(org.perfil)}.</p></header>
    <div className={styles.notice}>O vínculo de fornecedor identifica sua relação com a loja e não libera acesso ao financeiro interno. Entrar em outra loja troca o ambiente da sua sessão.</div>
    <AmbienteFinanceiro org={org} />
    {org.perfil === "admin" ? <>
      <section className={styles.box}><h2>Convidar fornecedor</h2><p className="muted">O convite vale por 7 dias e vincula a identidade do fornecedor a esta loja.</p><CriarConviteForm organizacaoId={org.id} /></section>
      <ConvitesLista convites={convites} organizacaoId={org.id} />
      <FornecedoresLista dados={fornecedores} organizacaoId={org.id} /><section className={styles.box}><h2>Adicionar membro da equipe</h2>{org.id === 1 && <p className={styles.notice}>Na loja original, o perfil precisa coincidir com o cadastro da conta. Nas demais lojas, o perfil é definido por vínculo.</p>}<p className="muted">Use o email exato de uma conta existente. Acesso e perfil são definidos somente nesta loja; senha e identidade da conta permanecem pessoais.</p><AdicionarMembroForm org={org.id} /></section><MembrosLista membros={membros} organizacaoId={org.id} />
    </> : <section className={styles.box}><h2>Vínculo registrado</h2><VinculoRegistrado org={org} /></section>}
  </div>;
}

function ConvitesLista({ convites, organizacaoId }: { convites: ConviteFornecedor[] | null; organizacaoId: number }) {
  return <section className={styles.box}><h2>Convites</h2>{convites === null ? <p role="alert" className="error">Não foi possível carregar os convites.</p> : !convites.length ? <p className="muted">Nenhum convite criado nesta organização.</p> : <div className={styles.list}>{convites.map(convite => <article key={convite.id}><h3>{convite.nome}</h3><p>{convite.email} · {situacao(convite)} · Validade: {data(convite.expires_at)}</p>{situacao(convite) === "Pendente" && <RevogarConviteForm organizacaoId={organizacaoId} conviteId={convite.id} />}</article>)}</div>}</section>;
}

function MembrosLista({ membros, organizacaoId }: { membros: MembroOrganizacao[] | null; organizacaoId: number }) {
  return <section className={styles.box}><h2>Membros</h2>{membros === null ? <p role="alert" className="error">Não foi possível carregar os membros.</p> : <div className={styles.list}>{membros.map(membro => <article key={membro.user_id}><strong>{membro.nome}</strong><p className={styles.status}>{membro.email} · {membro.perfil} · {membro.ativo ? "Ativo" : "Inativo"}</p><MembroForm org={organizacaoId} membro={membro} /></article>)}</div>}</section>;
}

function AmbienteFinanceiro({ org }: { org: Organizacao }) {
  if (!["admin", "financeiro", "operador", "consulta"].includes(org.perfil)) return null;
  return <section className={styles.box}><h2>Ambiente financeiro</h2>{org.financeiro_habilitado ? <SelecionarOrganizacaoForm organizacaoId={org.id} /> : org.perfil === "admin" ? <ProvisionarOrganizacaoForm organizacaoId={org.id} /> : <p className="muted">O administrador precisa preparar este ambiente antes do acesso.</p>}</section>;
}

function FornecedoresLista({ dados, organizacaoId }: { dados: FornecedoresLoja | null; organizacaoId: number }) {
  return <section className={styles.box}><h2>Cadastros dos fornecedores convidados</h2><p className="muted">Vincule cada conta aceita ao cadastro correto desta loja para liberar o portal.</p>{dados === null ? <p role="alert">Não foi possível carregar os cadastros. Prepare o ambiente financeiro e tente novamente.</p> : !dados.fornecedores.length ? <p>Nenhum fornecedor aceitou o convite nesta loja.</p> : <div className={styles.list}>{dados.fornecedores.map(fornecedor => <article key={fornecedor.user_id} className={styles.payment}><h3>{fornecedor.nome}</h3><p>{fornecedor.email} · {fornecedor.ativo ? "Ativo" : "Inativo"}</p>{fornecedor.pessoa_id ? <p>Cadastro vinculado: #{fornecedor.pessoa_id}</p> : fornecedor.ativo ? <VincularCadastroForm org={organizacaoId} usuario={fornecedor.user_id} pessoas={dados.cadastros} /> : <p>Reative o vínculo antes de associar o cadastro.</p>}</article>)}</div>}</section>;
}

function VinculoRegistrado({ org }: { org: Organizacao }) {
  return <><p className="muted">Este vínculo identifica sua relação com a loja.</p>{org.perfil === "fornecedor" && <><p>Consulte seus pagamentos, administre suas chaves e declare recebimentos no portal desta loja.</p><Link href={`/organizacoes/${org.id}/fornecedor`}>Abrir portal do fornecedor</Link></>}</>;
}
