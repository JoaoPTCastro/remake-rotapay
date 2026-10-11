import Link from "next/link";
import { unstable_rethrow } from "next/navigation";
import { apiGet, perfil } from "../../../lib/api";
import type { CadastroPessoa } from "../../../lib/cadastro-types";
import type { ExtratoNotas, Nota } from "../../../lib/notas-types";
import { moedaNota } from "../../../lib/notas-types";
import { NovaNota } from "./NotaForms";
import NotasTable from "./NotasTable";
import PreferenciasTabela from "../../../components/PreferenciasTabela";
import { carregarCatalogos, carregarPreferencia, aplicarOrdenacao } from "../../../lib/configuracoes-api";
import { filtrosAplicados, filtrosParaSalvar } from "../../../lib/tabela-filtros";
import type { Catalogos, PreferenciaTabela } from "../../../lib/configuracoes-types";
import styles from "./Notas.module.css";
type Params = { pessoa_id?: string; relacao?: string; status?: string; em_atraso?: string; offset?: string; filtrar?: string };
export default async function NotasPage({ searchParams }: { searchParams: Promise<Params> }) {
  let preferencia: PreferenciaTabela;
  try { preferencia = await carregarPreferencia("notas"); } catch (erro) { unstable_rethrow(erro); return <p role="alert">Não foi possível carregar suas preferências. Recarregue a página.</p>; }
  const filtros = filtrosAplicados("notas", await searchParams, preferencia) as Params;
  const { pessoaId, relacao, qs, offset } = parametros(filtros);
  aplicarOrdenacao(qs, preferencia);
  let catalogos: Catalogos; let pessoas: CadastroPessoa[]; let notas: Nota[]; let extrato: ExtratoNotas | null = null; let papel: string;
  try { [catalogos, pessoas, notas, papel] = await Promise.all([carregarCatalogos(true),apiGet("/pessoas") as Promise<CadastroPessoa[]>, apiGet(`/notas?${qs}`) as Promise<Nota[]>, perfil()]); if (pessoaId && relacao) extrato = await apiGet(`/pessoas/${pessoaId}/extrato-notas?relacao=${relacao}`) as ExtratoNotas; }
  catch (erro) { unstable_rethrow(erro); return <div className={styles.stack}><h1>Notas e extratos</h1><p role="alert">Não foi possível carregar as notas. Confira sua conexão e tente novamente.</p><Link href="/notas">Tentar novamente</Link></div>; }
  const pagina = (novo: number) => { const params = new URLSearchParams(qs); params.set("offset", String(novo)); return `/notas?${params}`; };
  return <Conteudo preferencia={preferencia} catalogos={catalogos} filtros={filtros} pessoaId={pessoaId} relacao={relacao} pessoas={pessoas} notas={notas} papel={papel} extrato={extrato} offset={offset} pagina={pagina} />;
}

function parametros(filtros: Params) {
const pessoaId = /^\d+$/.test(filtros.pessoa_id ?? "") ? filtros.pessoa_id : ""; const relacao = filtros.relacao === "cliente" || filtros.relacao === "fornecedor" ? filtros.relacao : "";
  const qs = new URLSearchParams({ filtrar: "1" }); if (pessoaId) qs.set("pessoa_id", pessoaId); if (relacao) qs.set("relacao", relacao); if (filtros.status) qs.set("status", filtros.status); if (filtros.em_atraso === "true") qs.set("em_atraso", "true");
  const offset = Math.max(0, Number.parseInt(filtros.offset ?? "0", 10) || 0); qs.set("offset", String(offset)); qs.set("limit", "100");
  return { pessoaId, relacao, qs, offset };
}

function Conteudo({ preferencia, catalogos, filtros, pessoaId, relacao, pessoas, notas, papel, extrato, offset, pagina }: { preferencia: PreferenciaTabela; catalogos: Catalogos; filtros: Params; pessoaId: string | undefined; relacao: string; pessoas: CadastroPessoa[]; notas: Nota[]; papel: string; extrato: ExtratoNotas | null; offset: number; pagina: (n:number)=>string }) {
  return <div className={styles.stack}><header><h1>Notas e extratos</h1><p><Link href="/intercambio">Importar / exportar notas em CSV</Link></p><p className={styles.muted}>Notas cadastradas no RotaPay. Vendas de clientes e compras de fornecedores mantêm saldos separados.</p></header><p className={styles.notice}>Os valores abaixo pertencem às notas e não representam saldo em caixa. Os lançamentos antigos continuam disponíveis em <Link href="/lancamentos">Lançamentos</Link>.</p>
    <form className={`${styles.box} ${styles.form}`} method="get"><input type="hidden" name="filtrar" value="1" /><label>Titular<select name="pessoa_id" defaultValue={pessoaId}><option value="">Todos os cadastros</option>{pessoas.map(p => <option key={p.id} value={p.id}>{p.nome}{!p.ativo ? " (inativo)" : ""}</option>)}</select></label><label>Relação<select name="relacao" defaultValue={relacao}><option value="">Vendas e compras</option><option value="cliente">Cliente · a receber</option><option value="fornecedor">Fornecedor · a pagar</option></select></label><label>Situação<select name="status" defaultValue={filtros.status ?? ""}><option value="">Todas</option><option value="aberto">Aberta</option><option value="parcial">Parcial</option><option value="quitado">Quitada</option><option value="cancelado">Cancelada</option></select></label><label className={styles.check}><input name="em_atraso" type="checkbox" value="true" defaultChecked={filtros.em_atraso === "true"} />Somente em atraso</label><div className={`${styles.wide} ${styles.actions}`}><button>Filtrar notas</button><Link href="/notas?filtrar=1">Limpar filtros</Link></div></form>
    {extrato && <section className={styles.box}><h2>Extrato · {extrato.pessoa_nome}</h2><p><Link href={`/extratos/${extrato.pessoa_id}?relacao=${extrato.relacao}`}>Ver extrato consolidado desta relação</Link></p><p>{relacao === "cliente" ? "Vendas ao cliente · valores a receber" : "Compras do fornecedor · valores a pagar"}. Totais de todas as notas desta relação, sem aplicar os filtros de situação ou atraso.</p><div className={styles.stats}>{[["Valor original", extrato.resumo.valor_original], ["Abatido registrado", extrato.resumo.valor_abatido], [relacao === "cliente" ? "Saldo a receber" : "Saldo a pagar", extrato.resumo.saldo_aberto], ["Saldo vencido", extrato.resumo.saldo_vencido]].map(([titulo, valor]) => <div className={styles.stat} key={titulo}><span>{titulo}</span><strong>{moedaNota(Number(valor))}</strong></div>)}</div></section>}
    {!extrato && <p className={styles.muted}>Selecione um titular e uma relação para consultar o extrato completo com totais separados.</p>}
    {(papel === "admin" || papel === "financeiro") && <NovaNota pessoas={pessoas} catalogos={catalogos} />}<section><div className={styles.head}><h2>Notas cadastradas no RotaPay</h2><span>{notas.length} nesta página</span></div><PreferenciasTabela key={JSON.stringify(preferencia)} tela="notas" preferencia={preferencia} filtros={filtrosParaSalvar("notas", filtros)} /><p className={styles.muted}>Ordenação aplicada a todos os resultados antes da paginação.</p><NotasTable notas={notas} preferencia={preferencia} /><nav className={`${styles.actions} ${styles.controls}`} aria-label="Páginas das notas">{offset > 0 && <Link href={pagina(Math.max(0, offset - 100))}>Página anterior</Link>}{notas.length === 100 && <Link href={pagina(offset + 100)}>Próxima página</Link>}</nav></section>
  </div>;
}
