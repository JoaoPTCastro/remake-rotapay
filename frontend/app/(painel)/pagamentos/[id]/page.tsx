import Link from "next/link";
import { notFound, unstable_rethrow } from "next/navigation";
import { apiGet, perfil } from "../../../../lib/api";
import type { Pagamento, AplicacaoPagamento, OrcamentoPagamento } from "../../../../lib/pagamentos-types";
import { tipoPagamento, podeEditarPagamento } from "../../../../lib/pagamentos-types";
import { notasElegiveis } from "../../../../lib/pagamento-notas";
import { moedaNota, dataNota } from "../../../../lib/notas-types";
import { AplicacaoForm, ReversaoPagamento, AnexoPagamentoForm, RemoverAnexoPagamento, type NotasDisponiveis } from "../PagamentoForms";
import ComprovanteViewer from "../ComprovanteViewer";
import RastreabilidadePagamento, { horarioRastreavel } from "../RastreabilidadePagamento";
import AtualizarPagamentos from "../AtualizarPagamentos";
import styles from "../Pagamentos.module.css";
async function notasDoPagamento(p: Pagamento): Promise<NotasDisponiveis> {
  const [cliente, fornecedor] = await Promise.all([notasElegiveis(p.cliente_id, "cliente"), notasElegiveis(p.fornecedor_id, "fornecedor")]);
  return { cliente: cliente.notas, fornecedor: fornecedor.notas, maisCliente: cliente.mais, maisFornecedor: fornecedor.mais };
}
export default async function PagamentoPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; if (!/^\d+$/.test(id)) notFound();
  let pagamento: Pagamento; let papel: string; let notas: NotasDisponiveis | null = null;
  try { [pagamento, papel] = await Promise.all([apiGet(`/pagamentos/${id}`) as Promise<Pagamento>, perfil()]); if (podeEditarPagamento(papel) && !pagamento.cancelado) notas = await notasDoPagamento(pagamento); }
  catch (erro) { unstable_rethrow(erro); if (erro instanceof Error && "status" in erro && erro.status === 404) notFound(); return <section><h1>Pagamento</h1><p role="alert">Não foi possível carregar este pagamento.</p><Link href={`/pagamentos/${id}`}>Tentar novamente</Link></section>; }
  return <Detalhe pagamento={pagamento} editar={podeEditarPagamento(papel)} notas={notas} />;
}
function Detalhe({ pagamento: p, editar, notas }: { pagamento: Pagamento; editar: boolean; notas: NotasDisponiveis | null }) {
  return <div className={styles.stack}><Link href="/pagamentos">← Voltar aos pagamentos</Link><header><h1>{p.codigo}</h1><AtualizarPagamentos /><p>{tipoPagamento(p.tipo)} · {p.forma} · {dataNota(p.data)}</p></header><section className={styles.box}><h2>Pagamento registrado</h2><div className={styles.stat}><span>Valor único do evento</span><strong>{moedaNota(p.valor)}</strong></div><Metadados pagamento={p} /><LinksTitulares pagamento={p} />{editar && !p.cancelado && <ReversaoPagamento pagamentoId={p.id} />}</section><RastreabilidadePagamento pagamento={p} /><section><h2>Saldos por relação</h2><p className={styles.notice}>Os dois saldos controlam obrigações diferentes. Não some os valores como caixa e não os interprete como confirmação do fornecedor.</p><div className={styles.budgets}><Orcamento titulo="Cliente · a receber" titular={p.cliente_nome} orcamento={p.orcamentos.cliente} /><Orcamento titulo="Fornecedor · a pagar" titular={p.fornecedor_nome} orcamento={p.orcamentos.fornecedor} /></div></section><AplicacoesDisponiveis pagamento={p} notas={notas} editar={editar} /><Repasses pagamento={p} editar={editar} /><Historico pagamento={p} editar={editar} /><Anexos pagamento={p} editar={editar} /></div>;
}
function AplicacoesDisponiveis({ pagamento: p, notas, editar }: { pagamento: Pagamento; notas: NotasDisponiveis | null; editar: boolean }) {
  if (!editar || p.cancelado || !notas) return null;
  if (p.orcamentos.cliente.saldo_disponivel <= 0 && p.orcamentos.fornecedor.saldo_disponivel <= 0) return <p className={styles.box}>Este pagamento não possui saldo disponível para novas aplicações.</p>;
  return <AplicacaoForm pagamento={p} notas={notas} />;
}
function Metadados({ pagamento: p }: { pagamento: Pagamento }) { return <div className={styles.metadata}><p>Situação: <strong>{p.cancelado ? "Cancelado" : "Registrado"}</strong></p>{p.motivo_cancelamento && <p>Motivo do cancelamento: {p.motivo_cancelamento}</p>}<p>Cliente: {p.cliente_nome ?? "Não vinculado"} · Fornecedor: {p.fornecedor_nome ?? "Não vinculado"}</p><p>Referência externa: {p.referencia_externa}</p><p>{p.observacao}</p><p>Forma registrada: {p.forma_nome_snapshot || "Sem catálogo"} · Operação registrada: {p.operacao_nome_snapshot || "Sem catálogo"}</p>{p.pagamento_origem_id && <p>Recebimento de origem: <Link href={`/pagamentos/${p.pagamento_origem_id}`}>#{p.pagamento_origem_id}</Link></p>}</div>; }
function Orcamento({ titulo, titular, orcamento: o }: { titulo: string; titular: string | null; orcamento: OrcamentoPagamento }) { return <section className={styles.box}><h3>{titulo}</h3><p>{titular ?? "Sem titular para esta relação"}</p><div className={styles.stats}>{[["Elegível", o.elegivel], ["Aplicado em notas", o.aplicado], ["Destinado a créditos de conta", o.destinado_credito], ["Disponível para aplicação", o.saldo_disponivel]].map(([label, valor]) => <div className={styles.stat} key={label}><span>{label}</span><strong>{moedaNota(Number(valor))}</strong></div>)}</div><p>Situação desta relação: {statusOrcamento(o.status)}</p></section>; }
function Repasses({ pagamento: p, editar }: { pagamento: Pagamento; editar: boolean }) {
  if (p.tipo !== "cliente_loja") return null;
  return <section className={styles.box}><h2>Repasses vinculados</h2><p>Valor repassado registrado: {moedaNota(p.valor_repassado)} · saldo para repasse: {moedaNota(p.saldo_para_repasse)}</p><p className={styles.muted}>Repasse registra a saída ao fornecedor vinculada a este recebimento. Não reaplica o valor na conta do cliente.</p>{editar && !p.cancelado && p.saldo_para_repasse > 0 && <Link className="btn" href={`/pagamentos?origem=${p.id}`}>Registrar repasse deste recebimento</Link>}{p.repasses?.length ? <ul>{p.repasses.map(r => <li key={r.id}><Link href={`/pagamentos/${r.id}`}>{r.codigo}</Link> · {moedaNota(r.valor)} · {dataNota(r.data)} · {r.cancelado ? "Cancelado" : "Registrado"}</li>)}</ul> : <p>Nenhum repasse registrado.</p>}</section>;
}
function Historico({ pagamento: p, editar }: { pagamento: Pagamento; editar: boolean }) { return <section id="historico" className={styles.box}><h2>Histórico de aplicações em notas</h2>{p.aplicacoes?.length ? <div className={styles.history}>{p.aplicacoes.map(a => <Aplicacao key={a.id} aplicacao={a} editar={editar && !p.cancelado} />)}</div> : <p>Nenhuma aplicação registrada.</p>}</section>; }
function Aplicacao({ aplicacao: a, editar }: { aplicacao: AplicacaoPagamento; editar: boolean }) { return <article className={styles.entry}><h3>Aplicação #{a.id} · {moedaNota(a.valor)}</h3><p><Link href={`/notas/${a.nota_id}`}>Nota #{a.nota_id} · {a.numero_documento}</Link> · {a.relacao === "cliente" ? "Cliente" : "Fornecedor"} · {dataNota(a.data)}</p><p>Referência: {a.referencia}</p><p>{a.observacao}</p>{a.relacao === "fornecedor" && <p>Concordância externa do fornecedor: {a.fornecedor_confirmou ? "Registrada" : "Não registrada"} · referência: {a.referencia_confirmacao ?? "—"}</p>}<p>Situação: {a.estornada ? "Estornada" : "Aplicada"}</p>{a.estorno && <p>Motivo do estorno: {a.estorno.motivo}</p>}<AcaoAplicacao aplicacao={a} editar={editar} /></article>; }
function Anexos({ pagamento: p, editar }: { pagamento: Pagamento; editar: boolean }) { const anexos = p.anexos?.filter(a => a.ativo) ?? []; return <section className={styles.box}><h2>Anexos do pagamento</h2>{anexos.length ? <ul>{anexos.map(a => <li key={a.id}><p>{a.nome_original} · anexado em {horarioRastreavel(a.created_at)}</p><ComprovanteViewer pagamentoId={p.id} anexoId={a.id} nome={a.nome_original} /><a href={`/api/pagamentos/anexo?pagamento=${p.id}&anexo=${a.id}`}>Baixar original</a>{editar && !p.cancelado && <RemoverAnexoPagamento pagamentoId={p.id} anexoId={a.id} />}</li>)}</ul> : <p>Nenhum anexo disponível.</p>}{editar && !p.cancelado && <AnexoPagamentoForm pagamentoId={p.id} />}</section>; }

function statusOrcamento(status: string) { const nomes: Record<string, string> = { inelegivel: "Não elegível", disponivel: "Disponível", parcial: "Parcialmente aplicado", utilizado: "Totalmente aplicado", cancelado: "Cancelado" }; return nomes[status] ?? status; }

function AcaoAplicacao({ aplicacao: a, editar }: { aplicacao: AplicacaoPagamento; editar: boolean }) {
  if (a.acerto_id) return <p><Link href={`/acertos/${a.acerto_id}`}>Ver acerto #{a.acerto_id}</Link>. As aplicações deste lote só podem ser estornadas pelo acerto inteiro.</p>;
  return editar && !a.estornada ? <ReversaoPagamento pagamentoId={a.pagamento_id} aplicacaoId={a.id} /> : null;
}

function LinksTitulares({ pagamento: p }: { pagamento: Pagamento }) { return <div className={styles.actions}>{p.cliente_id && <Link href={`/links?pessoa_id=${p.cliente_id}`}>Consultar links do cliente / representante</Link>}{p.fornecedor_id && <Link href={`/links?pessoa_id=${p.fornecedor_id}`}>Consultar links do fornecedor</Link>}<p className={styles.muted}>Consulta por titular, sem afirmar vínculo entre este pagamento e um link.</p></div>; }
