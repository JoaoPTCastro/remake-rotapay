"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { criarPagamento, aplicarPagamento, reverterPagamento, anexarPagamento, removerAnexoPagamento, listarNotasAplicacao } from "../../../lib/pagamentos-actions";
import type { CadastroPessoa } from "../../../lib/cadastro-types";
import type { Nota, RelacaoNota } from "../../../lib/notas-types";
import { moedaNota } from "../../../lib/notas-types";
import type { Pagamento, PagamentoResultado, TipoPagamento, PaginaNotasPagamento } from "../../../lib/pagamentos-types";
import type { Catalogos } from "../../../lib/configuracoes-types";
import { OperacaoSelecao } from "../../../components/CatalogoSelecao";
import RastreabilidadeCampos from "./RastreabilidadeCampos";
import styles from "./Pagamentos.module.css";
type Acao = (form: FormData) => Promise<PagamentoResultado>;
function useEnvio() {
  const router = useRouter(); const [enviando, setEnviando] = useState(false); const [resultado, setResultado] = useState<PagamentoResultado | null>(null); const bloqueio = useRef(false); const chave = useRef<string | null>(null);
  async function enviar(form: FormData, acao: (f: FormData, k: string) => Promise<PagamentoResultado>, abrirCriado = false, limpar?: () => void) {
    if (bloqueio.current) return;
    bloqueio.current = true; chave.current ??= crypto.randomUUID(); setEnviando(true);
    try { const res = await acao(form, chave.current); setResultado(res); if (res.ok) { chave.current = null; limpar?.(); if (abrirCriado && res.id) router.push(`/pagamentos/${res.id}`); else router.refresh(); } }
    catch { setResultado({ ok: false, mensagem: "A resposta não foi concluída. Confira o histórico antes de iniciar outro registro; esta tentativa conserva sua identificação." }); }
    finally { bloqueio.current = false; setEnviando(false); }
  }
  return { enviando, resultado, enviar };
}
function Feedback({ resultado, pagamentoId }: { resultado: PagamentoResultado | null; pagamentoId?: number }) {
  const router = useRouter();
  if (!resultado) return null;
  return <div><p role={resultado.ok ? "status" : "alert"} className={resultado.ok ? styles.ok : styles.error}>{resultado.mensagem}</p>{!resultado.ok && <p className={styles.muted}>Se houve falha depois do envio, <Link href={pagamentoId ? `/pagamentos/${pagamentoId}#historico` : "/pagamentos"}>confira os registros</Link> antes de repetir. A mesma tentativa conserva sua identificação para evitar duplicação. <button type="button" className="secondary" onClick={() => router.refresh()}>Atualizar histórico</button></p>}</div>;
}
function titulares(pessoas: CadastroPessoa[], relacao: RelacaoNota) { return pessoas.filter(p => p.ativo && (p.tipo === "ambos" || p.tipo === relacao || (relacao === "cliente" && p.tipo === "representante"))); }
export function NovoPagamento({ pessoas, origem, catalogos }: { pessoas: CadastroPessoa[]; origem: Pagamento | null; catalogos: Catalogos }) {
  const { enviando, resultado, enviar } = useEnvio(); const [tipo, setTipo] = useState<TipoPagamento>(origem ? "repasse_fornecedor" : "cliente_loja"); const [forma, setForma] = useState("PIX");
  return <details className={styles.box} open={Boolean(origem)}><summary>{origem ? "Registrar repasse ao fornecedor" : "Registrar novo pagamento"}</summary>{origem && <p className={styles.notice}>Origem: <Link href={`/pagamentos/${origem.id}`}>{origem.codigo}</Link> · saldo para repasse {moedaNota(origem.saldo_para_repasse)}. O repasse constitui um evento vinculado ao recebimento original; não gera outro abatimento do cliente.</p>}<form className={styles.form} onSubmit={e => { e.preventDefault(); void enviar(new FormData(e.currentTarget), (f, k) => criarPagamento(k, f), true); }}>
    <label>Tipo<select name="tipo" value={tipo} disabled={Boolean(origem)} onChange={e => { const t = e.target.value as TipoPagamento; setTipo(t); if (t === "cliente_fornecedor") setForma("PIX"); }}><option value="cliente_loja">Cliente → loja</option><option value="cliente_fornecedor">Cliente → fornecedor (PIX)</option>{origem && <option value="repasse_fornecedor">Repasse ao fornecedor</option>}</select></label>{origem && <><input type="hidden" name="tipo" value="repasse_fornecedor" /><input type="hidden" name="pagamento_origem_id" value={origem.id} /></>}
    <OperacaoSelecao itens={catalogos.operacoes} documento="pagamentos" /><label>Forma do catálogo (opcional)<select name="forma_id" key={forma} defaultValue=""><option value="">Sem forma do catálogo</option>{catalogos.formas.filter(c => c.forma_base === forma).map(c => <option key={c.id} value={c.id}>{c.nome} · {c.forma_base}</option>)}</select></label><label>Forma<select name="forma" value={forma} onChange={e => setForma(e.target.value)}><option value="PIX">PIX</option><option value="dinheiro" disabled={tipo === "cliente_fornecedor"}>Dinheiro</option></select></label>
    {tipo !== "repasse_fornecedor" && <TitularSelect pessoas={titulares(pessoas, "cliente")} relacao="cliente" />}{tipo !== "cliente_loja" && <TitularSelect pessoas={titulares(pessoas, "fornecedor")} relacao="fornecedor" />}
    <RastreabilidadeCampos /><label>Valor do pagamento (R$)<input name="valor" type="number" step="0.01" min="0.01" max={origem?.saldo_para_repasse} required /></label><label>Data do pagamento<input name="data" type="date" min={origem?.data} required /></label><label className={styles.wide}>Referência externa única<input name="referencia_externa" minLength={3} maxLength={180} required placeholder="Identificador bancário ou número do recibo" /></label><label className={styles.wide}>Observação<textarea name="observacao" minLength={3} maxLength={2000} required rows={2} /></label>
    <p className={`${styles.notice} ${styles.wide}`}>Este registro documenta um pagamento. Não consulta banco ou gateway, não confirma aceite do fornecedor e não importa automaticamente os PIX antigos. A aplicação em cada nota será feita separadamente.</p><label className={`${styles.check} ${styles.wide}`}><input type="checkbox" name="declaracao_novo_pagamento" required />Confirmo que este é um novo evento, que não duplica um PIX antigo, um pagamento já registrado ou um abatimento externo do mesmo acerto.</label><div className={styles.wide}><button disabled={enviando}>{enviando ? "Registrando…" : "Registrar pagamento"}</button><Feedback resultado={resultado} /></div>
  </form></details>;
}
function TitularSelect({ pessoas, relacao }: { pessoas: CadastroPessoa[]; relacao: RelacaoNota }) { return <label>{relacao === "cliente" ? "Cliente" : "Fornecedor"}<select name={`${relacao}_id`} defaultValue="" required><option value="">Selecione o cadastro</option>{pessoas.map(p => <option key={p.id} value={p.id}>{p.nome} · #{p.id}</option>)}</select></label>; }
export type NotasDisponiveis = { cliente: Nota[]; fornecedor: Nota[]; maisCliente: boolean; maisFornecedor: boolean };
export function AplicacaoForm({ pagamento, notas }: { pagamento: Pagamento; notas: NotasDisponiveis }) {
  const { enviando, resultado, enviar } = useEnvio(); const [relacao, setRelacao] = useState<RelacaoNota>(pagamento.orcamentos.cliente.saldo_disponivel > 0 ? "cliente" : "fornecedor"); const [notaId, setNotaId] = useState(""); const { pagina, carregando, erro, navegar } = useNotasAplicacao(pagamento.id, notas); const atual = pagina(relacao); const saldo = pagamento.orcamentos[relacao].saldo_disponivel; const nota = atual.notas.find(n => String(n.id) === notaId); const limite = Math.min(saldo, nota?.saldo_aberto ?? saldo);
  return <section className={styles.box}><h2>Aplicar pagamento em uma nota</h2><p className={styles.notice}>A aplicação reduz somente a nota e o saldo disponível da relação escolhida. Os saldos de cliente e fornecedor são independentes; não devem ser somados como dinheiro em caixa. A confirmação do fornecedor deve ser obtida fora do RotaPay e documentada antes de aplicar na compra. O registro não consulta o banco.</p><form className={styles.form} onSubmit={e => { e.preventDefault(); const formEl = e.currentTarget; void enviar(new FormData(formEl), (f, k) => aplicarPagamento(pagamento.id, k, f), false, () => { formEl.reset(); setNotaId(""); void navegar(relacao, atual.offset); }); }}>
    <label>Relação<select name="relacao" value={relacao} disabled={carregando} onChange={e => { setRelacao(e.target.value as RelacaoNota); setNotaId(""); }}><option value="cliente" disabled={pagamento.orcamentos.cliente.saldo_disponivel <= 0}>Cliente · a receber</option><option value="fornecedor" disabled={pagamento.orcamentos.fornecedor.saldo_disponivel <= 0}>Fornecedor · a pagar</option></select></label><label>Nota do titular<select name="nota_id" value={notaId} onChange={e => setNotaId(e.target.value)} required><option value="">Selecione a nota</option>{atual.notas.map(n => <option key={n.id} value={n.id}>#{n.id} · {n.numero_documento} · saldo {moedaNota(n.saldo_aberto)}</option>)}</select></label><label>Valor a aplicar (R$)<input name="valor" type="number" step="0.01" min="0.01" max={limite} required /></label><label>Data da aplicação<input name="data" type="date" min={dataMinimaAplicacao(pagamento.data, nota)} required /></label><label className={styles.wide}>Referência da aplicação<input name="referencia" minLength={3} maxLength={200} required /></label><label className={styles.wide}>Observação<textarea name="observacao" minLength={3} maxLength={2000} required rows={2} /></label>{relacao === "fornecedor" && <ConfirmacaoFornecedor />}<label className={`${styles.check} ${styles.wide}`}><input name="confirmacao" type="checkbox" required />Confirmo o titular, a relação, a nota e o valor desta aplicação.</label><div className={styles.wide}><button disabled={enviando || carregando || !notaId || limite <= 0}>{enviando ? "Aplicando…" : "Aplicar valor à nota"}</button><Feedback resultado={resultado} pagamentoId={pagamento.id} /></div>
  </form><PaginacaoNotas pagina={atual} carregando={carregando} erro={erro} ir={async offset => { if (await navegar(relacao, offset)) setNotaId(""); }} /><NotasLimitadas relacao={relacao} pagamento={pagamento} /></section>;
}
function NotasLimitadas({ relacao, pagamento }: { relacao: RelacaoNota; pagamento: Pagamento }) {
  const pessoaId = relacao === "cliente" ? pagamento.cliente_id : pagamento.fornecedor_id;
  return <p className={styles.muted}>A seleção mostra apenas notas abertas ou parciais do titular, com até 50 de cada situação por página. Use a navegação para acessar todos os documentos elegíveis. <Link href={`/notas?pessoa_id=${pessoaId}&relacao=${relacao}`}>Consultar notas e extrato</Link></p>;
}
function useNotasAplicacao(pagamentoId: number, iniciais: NotasDisponiveis) {
  const [paginas, setPaginas] = useState<Partial<Record<RelacaoNota, PaginaNotasPagamento>>>({}); const [carregando, setCarregando] = useState(false); const [erro, setErro] = useState<string | null>(null); const bloqueio = useRef(false);
  function pagina(relacao: RelacaoNota): PaginaNotasPagamento { return paginas[relacao] ?? { notas: iniciais[relacao], offset: 0, mais: relacao === "cliente" ? iniciais.maisCliente : iniciais.maisFornecedor }; }
  async function navegar(relacao: RelacaoNota, offset: number) {
    if (bloqueio.current) return false;
    bloqueio.current = true; setCarregando(true); setErro(null);
    try { const res = await listarNotasAplicacao(pagamentoId, relacao, offset); if (!res.ok) { setErro(res.mensagem); return false; } setPaginas(atual => ({ ...atual, [relacao]: res.pagina })); return true; }
    catch { setErro("Não foi possível carregar esta página. Tente novamente."); return false; }
    finally { bloqueio.current = false; setCarregando(false); }
  }
  return { pagina, carregando, erro, navegar };
}
function PaginacaoNotas({ pagina, carregando, erro, ir }: { pagina: PaginaNotasPagamento; carregando: boolean; erro: string | null; ir: (offset: number) => Promise<void> }) {
  return <div><nav className={styles.actions} aria-label="Páginas das notas elegíveis">{pagina.offset > 0 && <button type="button" className="secondary" disabled={carregando} onClick={() => { void ir(Math.max(0, pagina.offset - 50)); }}>Notas anteriores</button>}<span>Página {pagina.offset / 50 + 1} · {pagina.notas.length} notas elegíveis</span>{pagina.mais && <button type="button" className="secondary" disabled={carregando} onClick={() => { void ir(pagina.offset + 50); }}>Próximas notas</button>}</nav>{carregando && <p role="status">Carregando notas…</p>}{erro && <p role="alert" className={styles.error}>{erro}</p>}</div>;
}
export function ReversaoPagamento({ pagamentoId, aplicacaoId }: { pagamentoId: number; aplicacaoId?: number }) {
  const { enviando, resultado, enviar } = useEnvio();
  return <details><summary>{aplicacaoId ? "Estornar aplicação" : "Cancelar pagamento"}</summary><form className={styles.form} onSubmit={e => { e.preventDefault(); const formEl = e.currentTarget; void enviar(new FormData(formEl), f => reverterPagamento(pagamentoId, aplicacaoId ?? null, f), false, () => formEl.reset()); }}><label>Motivo<textarea name="motivo" minLength={3} maxLength={2000} required rows={2} /></label><label>Sua senha de confirmação<input name="senha" type="password" autoComplete="current-password" required /></label><div className={styles.wide}><button disabled={enviando}>{enviando ? "Salvando…" : aplicacaoId ? "Confirmar estorno" : "Confirmar cancelamento"}</button><Feedback resultado={resultado} pagamentoId={pagamentoId} /></div></form></details>;
}
export function AnexoPagamentoForm({ pagamentoId }: { pagamentoId: number }) {
  const { enviando, resultado, enviar } = useEnvio();
  const acao: Acao = form => { const arquivo = form.get("f"); if (!(arquivo instanceof File) || !arquivo.size || arquivo.size > 10 * 1024 * 1024) return Promise.resolve({ ok: false, mensagem: "Selecione um arquivo de até 10 MB." }); return anexarPagamento(pagamentoId, form); };
  return <form className={styles.form} onSubmit={e => { e.preventDefault(); const formEl = e.currentTarget; void enviar(new FormData(formEl), acao, false, () => formEl.reset()); }}><label>Arquivo (PDF, PNG, JPEG ou WebP · até 10 MB)<input name="f" type="file" accept="application/pdf,image/png,image/jpeg,image/webp" required /></label><div><button disabled={enviando}>{enviando ? "Enviando…" : "Anexar arquivo"}</button><Feedback resultado={resultado} pagamentoId={pagamentoId} /></div></form>;
}
export function RemoverAnexoPagamento({ pagamentoId, anexoId }: { pagamentoId: number; anexoId: number }) {
  const { enviando, resultado, enviar } = useEnvio();
  return <details><summary>Ocultar este anexo</summary><form onSubmit={e => { e.preventDefault(); void enviar(new FormData(e.currentTarget), () => removerAnexoPagamento(pagamentoId, anexoId)); }}><p>O anexo será ocultado por desativação lógica e deixará de estar disponível para visualizar e baixar. O pagamento, seus saldos e histórico serão preservados. Esta ação não cancela nem confirma pagamento no banco.</p><label className={styles.check}><input type="checkbox" required />Confirmo a ocultação deste anexo.</label><button disabled={enviando}>{enviando ? "Ocultando…" : "Ocultar anexo"}</button><Feedback resultado={resultado} pagamentoId={pagamentoId} /></form></details>;
}

function ConfirmacaoFornecedor() { return <><label className={styles.wide}>Referência da confirmação obtida fora do RotaPay<input name="referencia_confirmacao" minLength={3} maxLength={200} required placeholder="Identificador da mensagem, recibo ou documento de concordância" /></label><label className={`${styles.check} ${styles.wide}`}><input type="checkbox" name="fornecedor_confirmou" required />Fornecedor já conferiu e concordou com este abatimento.</label></>; }

function dataMinimaAplicacao(dataPagamento: string, nota: Nota | undefined) { return nota && nota.data_emissao > dataPagamento ? nota.data_emissao : dataPagamento; }
