import Link from "next/link";
import { unstable_rethrow } from "next/navigation";
import { apiGet } from "../../../lib/api";
import type { AlertaCadastro, PaginaCadastro } from "../../../lib/cadastro-consultas-types";
import { moedaNota, dataNota } from "../../../lib/notas-types";
import styles from "../intercambio/Intercambio.module.css";
export type FiltrosAlertas = { alerta?: string; alertas_offset?: string };
const tipos = { divida_sem_chave: "Dívida aberta sem chave válida", chave_expirada: "Chave expirada", chave_a_vencer: "Chave a vencer em até 30 dias" };
export default async function AlertasCadastro({ filtros }: { filtros: FiltrosAlertas }) {
  const tipo = filtros.alerta && Object.hasOwn(tipos, filtros.alerta) ? filtros.alerta : "";
  const offset = Math.max(0, Number.parseInt(filtros.alertas_offset ?? "0", 10) || 0);
  const qs = new URLSearchParams({ limit: "50", offset: String(offset) }); if (tipo) qs.set("tipo", tipo);
  let pagina: PaginaCadastro<AlertaCadastro>;
  try { pagina = await apiGet(`/cadastros/alertas?${qs}`) as PaginaCadastro<AlertaCadastro>; }
  catch (erro) { unstable_rethrow(erro); return <section className={styles.box}><h2>Alertas de chaves</h2><p role="alert">Não foi possível consultar os alertas.</p><Link href="/cadastro#alertas">Tentar novamente</Link></section>; }
  return <section id="alertas" className={styles.box}><h2>Alertas de chaves</h2><p className={styles.notice}>São avisos de cadastro: não cancelam dívidas nem links e não trocam destinos de pagamentos existentes.</p><form method="get"><label>Tipo de alerta<select name="alerta" defaultValue={tipo}><option value="">Todos</option>{Object.entries(tipos).map(([valor, titulo]) => <option key={valor} value={valor}>{titulo}</option>)}</select></label><button>Filtrar alertas</button></form><p>{pagina.itens.length} nesta página · {pagina.total} no filtro.</p>{!pagina.itens.length && <p>Nenhum alerta corresponde ao filtro.</p>}<div className={styles.history}>{pagina.itens.map(a => <article key={a.id} className={styles.entry}><h3>{tipos[a.tipo]} · {a.pessoa_nome}</h3>{a.chave_id !== null && <p>Chave #{a.chave_id} · validade {dataNota(a.validade)}</p>}{a.dias !== null && <p>Dias até a validade: {a.dias}</p>}{a.divida_aberta !== null && <p>Saldo aberto de notas a pagar: {moedaNota(a.divida_aberta)}</p>}<div className={styles.actions}><Link href={`/cadastro?pessoa_id=${a.pessoa_id}&aba=chaves`}>Conferir cadastro #{a.pessoa_id}</Link><Link href={`/links?pessoa_id=${a.pessoa_id}`}>Consultar links deste titular</Link><ExtratoDoAlerta alerta={a} /></div></article>)}</div><Paginas pagina={pagina} tipo={tipo} /></section>;
}
function Paginas({ pagina: p, tipo }: { pagina: { offset: number; limit: number; tem_mais: boolean }; tipo: string }) { const url = (offset: number) => `/cadastro?${new URLSearchParams({ alerta: tipo, alertas_offset: String(offset) })}#alertas`; return <nav className={styles.actions} aria-label="Paginação de alertas">{p.offset > 0 && <Link href={url(Math.max(0, p.offset - p.limit))}>Alertas anteriores</Link>}<span>Página {Math.floor(p.offset / p.limit) + 1}</span>{p.tem_mais && <Link href={url(p.offset + p.limit)}>Próximos alertas</Link>}</nav>; }

function ExtratoDoAlerta({ alerta: a }: { alerta: AlertaCadastro }) { return a.relacao === "fornecedor" ? <Link href={`/extratos/${a.pessoa_id}?relacao=fornecedor`}>Extrato de fornecedor</Link> : <Link href="/extratos">Consultar extrato por relação</Link>; }
