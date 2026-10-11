import Compartilhamentos from "../Compartilhamentos";
import {apiGet,perfil} from "../../../../lib/api";
import type {PaginaCompartilhamentos} from "../../../../lib/compartilhamentos-types";
import Link from "next/link";
import { notFound, unstable_rethrow } from "next/navigation";
import { carregarExtrato, parametrosExtrato } from "../../../../lib/extratos-api";
import type { ExtratoParams, ExtratoConsulta } from "../../../../lib/extratos-types";
import ExtratoResumo from "../ExtratoResumo";
import ExtratoFiltros from "../ExtratoFiltros";
import ExtratoTimeline from "../ExtratoTimeline";
import RecarregarExtrato from "../RecarregarExtrato";
import { ListaExtrato, TabelaNotas, TabelaPagamentos, TabelaCreditos, TabelaAcertos } from "../ExtratoListas";
import styles from "../Extratos.module.css";
export default async function ExtratoPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<ExtratoParams> }) {
  const { id } = await params; if (!/^[1-9]\d*$/.test(id)) notFound();
  const filtros = await searchParams;
  if (filtros.relacao !== "cliente" && filtros.relacao !== "fornecedor") return <div className={styles.stack}><h1>Escolha a relação da conta</h1><p>Consulte cada relação separadamente.</p><Link href={`/extratos/${id}?relacao=cliente`}>Conta de cliente</Link><Link href={`/extratos/${id}?relacao=fornecedor`}>Conta de fornecedor</Link></div>;
  const qs = parametrosExtrato(filtros, filtros.relacao);
  let consulta: ExtratoConsulta;
  try { consulta = await carregarExtrato(id, qs); }
  catch (erro) { unstable_rethrow(erro); return <div className={styles.stack}><h1>Extrato individual</h1><p role="alert">Não foi possível consultar esta conta. Confira o titular, a relação e sua conexão.</p><RecarregarExtrato /><Link href="/extratos">Selecionar titular</Link></div>; }
  const podeCompartilhar=["admin","financeiro"].includes(await perfil());
  const offsetCompartilhamentos=/^\d+$/.test(filtros.compartilhamentos_offset??"") ? Math.min(100000,Number(filtros.compartilhamentos_offset)) : 0;
  const lista=podeCompartilhar ? await apiGet(`/extratos/${id}/compartilhamentos?relacao=${consulta.resumo.relacao}&limit=100&offset=${offsetCompartilhamentos}`).catch(()=>null) as PaginaCompartilhamentos|null : null;
  return <Conteudo consulta={consulta} id={id} qs={qs} podeCompartilhar={podeCompartilhar} lista={lista} />;
}
function Conteudo({ consulta: c, id, qs,podeCompartilhar,lista }: { consulta: ExtratoConsulta; id: string; qs: URLSearchParams;podeCompartilhar:boolean;lista:PaginaCompartilhamentos|null }) {
  const e = c.resumo;
  return <div className={styles.stack}><Link href="/extratos">← Selecionar outra conta</Link><header><h1>Extrato individual · {e.pessoa.nome}</h1><p>Cadastro #{e.pessoa.id} · {e.relacao === "cliente" ? "Cliente · a receber" : "Fornecedor · a pagar"} · {e.pessoa.ativo ? "Cadastro ativo" : "Cadastro inativo"}</p><p className={styles.notice}>Consulta autenticada de notas, pagamentos, créditos e acertos cadastrados no domínio novo do RotaPay. Os registros antigos permanecem nas telas de PIX e lançamentos.</p></header><nav className={styles.nav} aria-label="Seções do extrato"><a href="#notas">Notas</a><a href="#pagamentos">Pagamentos</a><a href="#creditos">Créditos</a><a href="#acertos">Acertos</a><a href="#timeline">Histórico</a></nav><ExtratoResumo extrato={e} />{podeCompartilhar && <Compartilhamentos key={`${id}-${e.relacao}`} id={Number(id)} relacao={e.relacao} destinatario={e.pessoa.nome} lista={lista} query={qs.toString()} />}<ExtratoFiltros id={id} relacao={e.relacao} qs={qs} /><ListaExtrato titulo="Notas" secao="notas" consulta={c.notas} id={id} qs={qs} renderizar={itens => <TabelaNotas notas={itens} />} /><ListaExtrato titulo="Pagamentos" secao="pagamentos" consulta={c.pagamentos} id={id} qs={qs} renderizar={itens => <TabelaPagamentos pagamentos={itens} relacao={e.relacao} />} /><ListaExtrato titulo="Créditos de conta" secao="creditos" consulta={c.creditos} id={id} qs={qs} renderizar={itens => <TabelaCreditos creditos={itens} />} /><ListaExtrato titulo="Acertos" secao="acertos" consulta={c.acertos} id={id} qs={qs} renderizar={itens => <TabelaAcertos acertos={itens} />} /><ListaExtrato titulo="Histórico" secao="timeline" consulta={c.timeline} id={id} qs={qs} renderizar={itens => <ExtratoTimeline eventos={itens} />} /></div>;
}
