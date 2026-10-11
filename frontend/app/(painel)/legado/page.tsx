import Link from "next/link";
import { apiGet, perfil } from "../../../lib/api";
import { unstable_rethrow } from "next/navigation";
import ResumoValores from "./ResumoValores";
import { FONTES_LEGADO, NOMES_FONTES, NOMES_DECISOES, type FonteLegado, type InventarioLegado, type PaginaRecibosLegado } from "../../../lib/legado-types";
import ClassificarItem from "./ClassificarItem";
import styles from "./Legado.module.css";

function indisponivel(erro: unknown): null { unstable_rethrow(erro); return null; }
function AvisoOrigem({ atual }: { atual?: boolean }) { return atual === false ? <p className="error">A origem mudou depois da classificação. Os valores abaixo são atuais; o recibo preserva os valores históricos.</p> : null; }
function offsetValido(value?: string) { const n = Number(value ?? 0); return Number.isInteger(n) && n >= 0 && n <= 100000 ? n : 0; }
function url(fonte: FonteLegado, offset: number, recibosOffset: number) { return `/legado?${new URLSearchParams({ fonte, offset: String(offset), recibos_offset: String(recibosOffset) })}`; }
function horario(value: string) { const data = new Date(value); return Number.isNaN(data.getTime()) ? "Data indisponível" : new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short", timeZone: "America/Sao_Paulo" }).format(data); }
export default async function Legado({ searchParams }: { searchParams: Promise<{ fonte?: string; offset?: string; recibos_offset?: string }> }) {
  const params = await searchParams;
  const fonte = FONTES_LEGADO.find(f => f === params.fonte) ?? "movimentacao";
  const offset = offsetValido(params.offset), recibosOffset = offsetValido(params.recibos_offset);
  const podeClassificar = ["admin", "financeiro"].includes(await perfil());
  const [inventario, recibos] = await Promise.all([
    apiGet(`/legado/inventario?fonte=${fonte}&limit=25&offset=${offset}`).catch(indisponivel) as Promise<InventarioLegado | null>,
    podeClassificar ? apiGet(`/legado/classificacoes?limit=25&offset=${recibosOffset}`).catch(indisponivel) as Promise<PaginaRecibosLegado | null> : Promise.resolve(null),
  ]);
  return <div className={styles.stack}><header><h1>Legado e classificação</h1><p>Inventário dos registros antigos e classificação por evidência, com origem preservada.</p></header>
    <div className={styles.notice}><strong>Classificação não é migração.</strong><p>Conversão e consumo integrado estão bloqueados. Este fluxo não cria notas, pagamentos, créditos, quitação ou saldo consumível. As decisões pendentes da loja precisam ser resolvidas antes de qualquer integração financeira.</p></div>
    <form method="get" className={styles.filters}><label>Fonte do inventário<select name="fonte" defaultValue={fonte}>{FONTES_LEGADO.map(f => <option key={f} value={f}>{NOMES_FONTES[f]}</option>)}</select></label><button>Consultar fonte</button></form>
    {!podeClassificar && <p className="muted">Seu perfil permite consultar o inventário. Classificar e consultar recibos exige administrador ou financeiro.</p>}
    <Inventario inventario={inventario} fonte={fonte} recibosOffset={recibosOffset} podeClassificar={podeClassificar} />
    {podeClassificar && <section className={styles.stack} aria-label="Recibos de classificação"><h2>Recibos e histórico</h2>{!recibos ? <p role="alert" className="error">Não foi possível consultar os recibos. Confira o histórico antes de repetir uma confirmação.</p> : <><p>{recibos.total} recibo(s). Horários em Brasília.</p>{recibos.itens.length === 0 && <p>Nenhum recibo nesta página.</p>}{recibos.itens.map(recibo => <details key={recibo.id} className={styles.record}><summary>Recibo #{recibo.id} · {horario(recibo.created_at)}</summary><p>Autor: usuário #{recibo.created_by} · {recibo.itens.length} origem(ns).</p><p>Somente classificação, sem impacto financeiro.</p>{recibo.itens.map(item => <div key={`${item.fonte}:${item.fonte_id}`}><p>{NOMES_FONTES[item.fonte]} #{item.fonte_id} · {NOMES_DECISOES[item.decisao]}</p><p>Evidência: {item.evidencia}</p>{item.pessoa_id && <p>Cadastro #{item.pessoa_id} · {item.relacao === "cliente" ? "Cliente" : "Fornecedor"}</p>}</div>)}</details>)}<nav className={styles.pagination} aria-label="Páginas dos recibos">{recibos.offset > 0 && <Link href={url(fonte,offset,Math.max(0,recibos.offset-recibos.limit))}>Recibos anteriores</Link>}{recibos.tem_mais && recibos.offset + recibos.limit <= 100000 && <Link href={url(fonte,offset,recibos.offset+recibos.limit)}>Próximos recibos</Link>}</nav></>}</section>}
  </div>;
}

function Inventario({ inventario, fonte, recibosOffset, podeClassificar }: { inventario: InventarioLegado | null; fonte: FonteLegado; recibosOffset: number; podeClassificar: boolean }) {
  return !inventario ? <p role="alert" className="error">Não foi possível carregar o inventário. Atualize a página para tentar novamente.</p> : <><h2>{NOMES_FONTES[fonte]}</h2><p>{inventario.total} registro(s). Exibindo {inventario.itens.length} a partir da posição {inventario.offset + 1}.</p>{inventario.itens.length === 0 && <p>Nenhum registro nesta página.</p>}{inventario.itens.map(item => <details key={`${item.fonte}:${item.fonte_id}:${item.snapshot_hash}:${item.classificacao?.id ?? "livre"}`} className={styles.record}><summary>{item.codigo || `Origem #${item.fonte_id}`} · {item.classificacao ? NOMES_DECISOES[item.classificacao.decisao] : "Sem classificação"}</summary><div className={styles.facts}><p>Origem preservada: #{item.fonte_id}</p><p>Estado: {item.status || "Não informado"}</p><p>Data: {item.data || "Não informada"}</p></div><AvisoOrigem atual={item.classificacao?.snapshot_atual} /><ResumoValores valores={item.valores} /><p>Vínculos documentados: {Object.entries(item.vinculos).filter(([,v]) => v !== null).map(([k,v]) => `${k.replaceAll("_", " ")}: ${typeof v === "number" ? "#" : ""}${v}`).join(" · ") || "Nenhum"}</p><p>Pendências: {item.pendencias.length ? item.pendencias.map(p => p.replaceAll("_", " ")).join(" · ") : "Nenhuma apontada no inventário; a conferência por evidência continua necessária."}</p>{podeClassificar ? <ClassificarItem origem={item} /> : item.classificacao && <p>Recibo #{item.classificacao.lote_id} · classificação #{item.classificacao.id}.</p>}</details>)}<nav className={styles.pagination} aria-label="Páginas do inventário">{inventario.offset > 0 && <Link href={url(fonte, Math.max(0,inventario.offset-inventario.limit),recibosOffset)}>Registros anteriores</Link>}{inventario.tem_mais && inventario.offset + inventario.limit <= 100000 && <Link href={url(fonte,inventario.offset+inventario.limit,recibosOffset)}>Próximos registros</Link>}</nav></>;
}
