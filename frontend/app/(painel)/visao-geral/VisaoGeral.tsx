import Link from "next/link";
import { unstable_rethrow } from "next/navigation";
import { apiGet } from "../../../lib/api";
import { brl } from "../../../lib/format";
import { consultaVisaoGlobal, filtrosVisaoGlobal } from "../../../lib/visao-geral-types";
import type { FiltrosVisaoGlobal, NotaFilaGlobal, PaginaGlobal, ParamsVisaoGlobal, PosicaoGlobal, ResumoVisaoGlobal } from "../../../lib/visao-geral-types";
import ResumoGlobal from "./Resumo";
import styles from "./VisaoGeral.module.css";

async function carregar<T>(url: string): Promise<T | null> {
  try { return await apiGet(url) as T; }
  catch (erro) { unstable_rethrow(erro); return null; }
}
function Paginacao({ pagina, filtros, secao, base }: { pagina: PaginaGlobal<unknown>; filtros: FiltrosVisaoGlobal; secao: "posicoes" | "fila"; base: string }) {
  const url = (offset: number) => {
    const qs = consultaVisaoGlobal(filtros);
    qs.set("posicoes_offset", String(filtros.posicoes_offset)); qs.set("fila_offset", String(filtros.fila_offset));
    qs.set(`${secao}_offset`, String(offset)); return `${base}?${qs}#${secao}`;
  };
  return <nav aria-label={`Paginação de ${secao}`} className={styles.actions}><span>{pagina.total_filtrado} registro(s) · início {pagina.offset + (pagina.itens.length ? 1 : 0)}</span>{pagina.offset > 0 && <Link href={url(Math.max(0,pagina.offset-pagina.limit))}>Anterior</Link>}{pagina.tem_mais && pagina.offset + pagina.limit <= 100000 && <Link href={url(pagina.offset+pagina.limit)}>Próxima</Link>}</nav>;
}
function Filtros({ filtros, base }: { filtros: FiltrosVisaoGlobal; base: string }) {
  return <form action={base} className={styles.filters}><label>Relação<select name="relacao" defaultValue={filtros.relacao}><option value="cliente">Cliente</option><option value="fornecedor">Fornecedor</option></select></label><label>Nome do titular<input name="q" maxLength={120} defaultValue={filtros.q} /></label><label>ID do titular<input name="pessoa_id" type="number" min={1} step={1} defaultValue={filtros.pessoa_id} /></label><button className="btn" type="submit">Filtrar listas</button><Link href={base}>Limpar</Link></form>;
}
function Posicoes({ pagina }: { pagina: PaginaGlobal<PosicaoGlobal> | null }) {
  if (!pagina) return <p role="alert">Não foi possível carregar as posições.</p>;
  return <div className="tablewrap"><table className={styles.table}><thead><tr><th>Titular</th><th>Notas abertas</th><th>Vencido</th><th>Pagamento disponível</th><th>Crédito disponível</th><th>Total para abater</th><th>Consulta</th></tr></thead><tbody>{pagina.itens.length === 0 && <tr><td colSpan={7}>Nenhuma posição para estes filtros.</td></tr>}{pagina.itens.map(({pessoa,relacao,totais_globais:t}) => <tr key={pessoa.id}><td data-label="Titular">{pessoa.nome} · #{pessoa.id}{!pessoa.ativo && <span className="badge"> Inativo</span>}</td><td data-label="Notas abertas">{brl(t.notas.saldo_aberto)}</td><td data-label="Vencido">{brl(t.notas.saldo_vencido)}</td><td data-label="Pagamento disponível">{brl(t.pagamentos.saldo_disponivel)}</td><td data-label="Crédito disponível">{brl(t.creditos.saldo_disponivel)}</td><td data-label="Total para abater">{brl(t.disponibilidade_total_para_abater)}</td><td><Link href={`/extratos/${pessoa.id}?relacao=${relacao}`}>Extrato</Link></td></tr>)}</tbody></table></div>;
}
function Fila({ pagina }: { pagina: PaginaGlobal<NotaFilaGlobal> | null }) {
  if (!pagina) return <p role="alert">Não foi possível carregar as notas abertas.</p>;
  return <div className="tablewrap"><table className={styles.table}><thead><tr><th>Documento</th><th>Titular</th><th>Emissão</th><th>Vencimento</th><th>Saldo aberto</th><th>Situação</th></tr></thead><tbody>{pagina.itens.length === 0 && <tr><td colSpan={6}>Nenhuma nota aberta para estes filtros.</td></tr>}{pagina.itens.map(n => <tr key={n.id}><td><Link href={`/notas/${n.id}`}>{n.numero_documento}</Link></td><td><Link href={`/extratos/${n.pessoa_id}?relacao=${n.relacao}`}>{n.pessoa_nome}</Link></td><td>{n.data_emissao}</td><td>{n.vencimento ?? "Sem vencimento"}</td><td>{brl(n.saldo_aberto)}</td><td>{n.em_atraso ? "Vencida" : "Aberta"}</td></tr>)}</tbody></table></div>;
}
export default async function VisaoGeral({ params, base = "/" }: { params: ParamsVisaoGlobal; base?: string }) {
  const filtros = filtrosVisaoGlobal(params);
  if (!filtros) return <section><h1>Visão geral</h1><p role="alert">Filtros inválidos. Use uma relação válida, nome de até 120 caracteres e paginação de 0 a 100.000.</p><Link href={base}>Limpar filtros</Link></section>;
  const qs = consultaVisaoGlobal(filtros);
  const [resumo,posicoes,fila] = await Promise.all([carregar<ResumoVisaoGlobal>("/visao-geral/resumo"),carregar<PaginaGlobal<PosicaoGlobal>>(`/visao-geral/posicoes?${qs}&limit=50&offset=${filtros.posicoes_offset}`),carregar<PaginaGlobal<NotaFilaGlobal>>(`/visao-geral/fila?${qs}&limit=50&offset=${filtros.fila_offset}`)]);
  return <div className={styles.stack}><header><h1>Visão geral · módulos novos</h1><p>Notas, pagamentos, créditos e acertos. Cliente e fornecedor mantêm contas independentes.</p><Link href="/?escopo=legado">Consultar painel legado separado</Link></header><p className={styles.notice}>Cobertura parcial: legado não integrado. Esta tela não representa saldo bancário, receita ou operação consolidada de várias lojas. Pagamento disponibiliza recurso para abatimento; crédito exige reconhecimento explícito.</p><ResumoGlobal resumo={resumo} /><section className={styles.box}><h2>Filtros das listas</h2><Filtros filtros={filtros} base={base} /></section><section id="posicoes" className={styles.box}><h2>Posições · {filtros.relacao === "cliente" ? "clientes" : "fornecedores"}</h2><p className={styles.actions}><a className="btn-secondary" href={`/api/visao-geral/export?${qs}`}>Exportar posições filtradas em CSV</a><span>Até 10.000 contas. A exportação inclui todas as páginas dos filtros.</span></p><Posicoes pagina={posicoes} />{posicoes && <Paginacao pagina={posicoes} filtros={filtros} secao="posicoes" base={base} />}</section><section id="fila" className={styles.box}><h2>Notas abertas · consulta</h2><p className="muted">Ordem por vencimento, emissão e documento interno. Sem rodízio, prioridade comercial ou programação automática.</p><Fila pagina={fila} />{fila && <Paginacao pagina={fila} filtros={filtros} secao="fila" base={base} />}</section></div>;
}
