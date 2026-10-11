"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { recursosAcerto, gerarPreviaAcerto, criarAcerto } from "../../../lib/acertos-actions";
import type { CadastroPessoa } from "../../../lib/cadastro-types";
import type { Nota, RelacaoNota } from "../../../lib/notas-types";
import type { Pagamento } from "../../../lib/pagamentos-types";
import type { Credito } from "../../../lib/creditos-types";
import type { AcertoItemInput, AcertoInput, PreviaAcerto, RecursosAcerto } from "../../../lib/acertos-types";
import { moedaNota } from "../../../lib/notas-types";
import styles from "./Acertos.module.css";
type Par = { id: string; tipo: "pagamento" | "credito"; credito: Credito | null; pagamento: Pagamento | null; nota: Nota | null; valor: string };
const parVazio = (id: string): Par => ({ id, tipo: "pagamento", credito: null, pagamento: null, nota: null, valor: "" });
function pessoasElegiveis(pessoas: CadastroPessoa[], relacao: RelacaoNota) { return pessoas.filter(p => p.ativo && (p.tipo === "ambos" || p.tipo === relacao || (relacao === "cliente" && p.tipo === "representante"))); }
function dadosFormulario(form: FormData, pares: Par[]): AcertoInput { return { pessoa_id: Number(form.get("pessoa_id")), relacao: String(form.get("relacao")) as RelacaoNota, data: String(form.get("data") ?? ""), referencia: String(form.get("referencia") ?? "").trim(), observacao: String(form.get("observacao") ?? "").trim(), itens: pares.map(itemFormulario) }; }
function useRecursos(pessoaId: string, relacao: RelacaoNota) {
  const [recursos, setRecursos] = useState<RecursosAcerto | null>(null); const [carregando, setCarregando] = useState(false); const [erro, setErro] = useState<string | null>(null); const bloqueio = useRef(false);
  async function carregar(pagamentosOffset = 0, notasOffset = 0, creditosOffset = 0) {
    if (!pessoaId || bloqueio.current) return;
    bloqueio.current = true; setCarregando(true); setErro(null);
    try { const res = await recursosAcerto(Number(pessoaId), relacao, { pagamentos: pagamentosOffset, notas: notasOffset, creditos: creditosOffset }); if (!res.ok) { setErro(res.mensagem); return; } setRecursos(res.dados); }
    catch { setErro("Não foi possível consultar os documentos. Tente novamente."); }
    finally { bloqueio.current = false; setCarregando(false); }
  }
  function limpar() { setRecursos(null); setErro(null); }
  return { recursos, carregando, erro, carregar, limpar };
}
function useRascunho() {
  const router = useRouter(); const [previa, setPrevia] = useState<PreviaAcerto | null>(null); const [enviando, setEnviando] = useState(false); const [mensagem, setMensagem] = useState<string | null>(null); const chave = useRef<string | null>(null); const bloqueio = useRef(false);
  async function gravar(dados: AcertoInput, token: string) {
    chave.current ??= crypto.randomUUID(); const res = await criarAcerto(dados, token, chave.current);
    if (!res.ok) { setMensagem(res.mensagem); return; }
    chave.current = null; router.push(`/acertos/${res.dados.id}`);
  }
  async function conferir(dados: AcertoInput) {
    const res = await gerarPreviaAcerto(dados);
    if (!res.ok) { setMensagem(res.mensagem); setPrevia(null); return; }
    setPrevia(res.dados);
  }
  async function enviar(form: FormData, pares: Par[], salvar: boolean) {
    if (bloqueio.current) return;
    if (salvar && (!previa || form.get("confirmacao_gravacao") !== "on")) { setMensagem("Revise a prévia e confirme a criação do rascunho."); return; }
    bloqueio.current = true; setEnviando(true); setMensagem(null); const dados = dadosFormulario(form, pares);
    try { if (salvar && previa) await gravar(dados, previa.token_previa); else await conferir(dados); }
    catch { setMensagem("A resposta não foi concluída. Confira os acertos existentes antes de iniciar outra tentativa."); }
    finally { bloqueio.current = false; setEnviando(false); }
  }
  return { previa, enviando, mensagem, enviar, invalidar: () => setPrevia(null) };
}
export default function NovoAcerto({ pessoas }: { pessoas: CadastroPessoa[] }) {
  const [relacao, setRelacao] = useState<RelacaoNota>("cliente"); const [pessoaId, setPessoaId] = useState(""); const [pares, setPares] = useState<Par[]>([parVazio("inicial")]); const contador = useRef(0); const consulta = useRecursos(pessoaId, relacao); const rascunho = useRascunho();
  function trocarTitular(novoId: string) { setPessoaId(novoId); consulta.limpar(); setPares([parVazio("inicial")]); rascunho.invalidar(); }
  function atualizar(id: string, dados: Partial<Par>) { setPares(lista => lista.map(p => p.id === id ? { ...p, ...dados } : p)); rascunho.invalidar(); }
  return <div className={styles.stack}><Link href="/acertos">← Voltar aos acertos</Link><header><h1>Criar acerto</h1><p>Associe explicitamente cada pagamento ou crédito de conta a uma nota do mesmo titular e da mesma relação.</p></header><p className={styles.notice}>A prévia e o rascunho não reservam saldo. A efetivação revalida todos os itens e conclui o lote inteiro. Sobra permanece na fonte escolhida: pagamento ou crédito de conta. Usar crédito não devolve disponibilidade ao pagamento que o originou. Nenhum dinheiro novo nem crédito adicional é criado.</p><form className={styles.box} onChange={e => { if (alterouProposta(e.target)) rascunho.invalidar(); }} onSubmit={e => { e.preventDefault(); const botao = (e.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null; void rascunho.enviar(new FormData(e.currentTarget), pares, botao?.value === "criar"); }}>
    <DadosAcerto pessoas={pessoas} relacao={relacao} pessoaId={pessoaId} consulta={consulta} enviando={rascunho.enviando} trocarTitular={trocarTitular} trocarRelacao={r => { setRelacao(r); trocarTitular(""); }} />
    {consulta.recursos && <><NavegacaoRecursos recursos={consulta.recursos} carregando={consulta.carregando || rascunho.enviando} carregar={consulta.carregar} /><div className={styles.pairs}>{pares.map((par, indice) => <LinhaPar key={par.id} par={par} indice={indice} recursos={consulta.recursos as RecursosAcerto} relacao={relacao} atualizar={dados => atualizar(par.id, dados)} remover={() => { setPares(lista => lista.filter(p => p.id !== par.id)); rascunho.invalidar(); }} podeRemover={pares.length > 1} disabled={rascunho.enviando} />)}</div><button type="button" className="secondary" disabled={pares.length >= 100 || rascunho.enviando} onClick={() => { contador.current += 1; setPares(lista => [...lista, parVazio(`par-${contador.current}`)]); rascunho.invalidar(); }}>Adicionar par fonte / nota</button></>}
    <div className={`${styles.actions} ${styles.controls}`}><button type="submit" value="previa" disabled={!consulta.recursos || consulta.carregando || rascunho.enviando}>{rascunho.enviando ? "Processando…" : "Conferir prévia"}</button></div>{rascunho.mensagem && <p role="alert" className={styles.error}>{rascunho.mensagem} <Link href="/acertos">Conferir registros existentes</Link></p>}{rascunho.previa && <div className={styles.controls}><PreviaConferencia previa={rascunho.previa} /><label className={styles.check}><input name="confirmacao_gravacao" type="checkbox" />Conferi os pares e valores da prévia e quero criar este rascunho.</label><button type="submit" value="criar" disabled={rascunho.enviando || consulta.carregando}>Criar rascunho do acerto</button></div>}
  </form></div>;
}
function opcoesSelecionadas<T extends { id: number }>(pagina: T[], selecionado: T | null): T[] { return selecionado && !pagina.some(p => p.id === selecionado.id) ? [selecionado, ...pagina] : pagina; }
function LinhaPar({ par, indice, recursos, relacao, atualizar, remover, podeRemover, disabled }: { par: Par; indice: number; recursos: RecursosAcerto; relacao: RelacaoNota; atualizar: (dados: Partial<Par>) => void; remover: () => void; podeRemover: boolean; disabled: boolean }) {
  const notas = opcoesSelecionadas(recursos.notas, par.nota);
  return <section className={styles.pair}><div className={styles.head}><h3>Par {indice + 1} · {par.tipo === "credito" ? "Crédito de conta" : "Pagamento"}</h3>{podeRemover && <button type="button" className="secondary" disabled={disabled} onClick={remover}>Remover par {indice + 1}</button>}</div><div className={`${styles.form} ${styles.pairgrid}`}><label>Tipo de fonte<select value={par.tipo} disabled={disabled} onChange={e => atualizar({ tipo: e.target.value as Par["tipo"], pagamento: null, credito: null })}><option value="pagamento">Pagamento</option><option value="credito">Crédito de conta já reconhecido</option></select></label><SelecaoFonte par={par} recursos={recursos} relacao={relacao} atualizar={atualizar} disabled={disabled} /><label>Nota<select value={par.nota?.id ?? ""} disabled={disabled} required onChange={e => atualizar({ nota: notas.find(n => n.id === Number(e.target.value)) ?? null })}><option value="">Selecione a nota</option>{notas.map(n => <option key={n.id} value={n.id}>#{n.id} · {n.numero_documento} · saldo {moedaNota(n.saldo_aberto)}</option>)}</select></label><label>Valor deste par (R$)<input type="number" step="0.01" min="0.01" value={par.valor} disabled={disabled} required onChange={e => atualizar({ valor: e.target.value })} /></label></div>{par.credito && <p className={styles.muted}>O uso deste crédito mantém o valor reconhecido separado no pagamento de origem. Origem: <Link href={`/acertos/${par.credito.acerto_id}`}>{par.credito.codigo_acerto}</Link> · <Link href={`/pagamentos/${par.credito.pagamento_id}`}>{par.credito.codigo_pagamento}</Link>.</p>}</section>;
}
function SelecaoFonte({ par, recursos, relacao, atualizar, disabled }: { par: Par; recursos: RecursosAcerto; relacao: RelacaoNota; atualizar: (dados: Partial<Par>) => void; disabled: boolean }) {
  if (par.tipo === "credito") { const creditos = opcoesSelecionadas(recursos.creditos, par.credito); return <label>Crédito de conta<select value={par.credito?.id ?? ""} disabled={disabled} required onChange={e => atualizar({ credito: creditos.find(c => c.id === Number(e.target.value)) ?? null })}><option value="">Selecione o crédito</option>{creditos.map(c => <option key={c.id} value={c.id}>{c.codigo} · disponível {moedaNota(c.saldo_disponivel)}</option>)}</select></label>; }
  const pagamentos = opcoesSelecionadas(recursos.pagamentos, par.pagamento); return <label>Pagamento<select value={par.pagamento?.id ?? ""} disabled={disabled} required onChange={e => atualizar({ pagamento: pagamentos.find(p => p.id === Number(e.target.value)) ?? null })}><option value="">Selecione o pagamento</option>{pagamentos.map(p => <option key={p.id} value={p.id}>{p.codigo} · disponível {moedaNota(p.orcamentos[relacao].saldo_disponivel)}</option>)}</select></label>;
}
function NavegacaoRecursos({ recursos: r, carregando, carregar }: { recursos: RecursosAcerto; carregando: boolean; carregar: (pag: number, notas: number, creditos: number) => Promise<void> }) {
  return <section><h2>Documentos disponíveis</h2><p className={styles.muted}>A consulta filtra fontes com saldo e notas abertas deste titular e relação. Navegue cada lista separadamente; as seleções dos pares permanecem.</p><PaginaRecurso titulo="Pagamentos" offset={r.pagamentos_offset} limit={r.limit} quantidade={r.pagamentos.length} mais={r.pagamentos_tem_mais} carregando={carregando} mudar={offset => carregar(offset, r.notas_offset, r.creditos_offset)} /><PaginaRecurso titulo="Créditos" offset={r.creditos_offset} limit={r.limit} quantidade={r.creditos.length} mais={r.creditos_tem_mais} carregando={carregando} mudar={offset => carregar(r.pagamentos_offset, r.notas_offset, offset)} /><PaginaRecurso titulo="Notas" offset={r.notas_offset} limit={r.limit} quantidade={r.notas.length} mais={r.notas_tem_mais} carregando={carregando} mudar={offset => carregar(r.pagamentos_offset, offset, r.creditos_offset)} /></section>;
}
function PaginaRecurso({ titulo, offset, limit, quantidade, mais, carregando, mudar }: { titulo: string; offset: number; limit: number; quantidade: number; mais: boolean; carregando: boolean; mudar: (offset: number) => Promise<void> }) {
  return <div className={`${styles.actions} ${styles.controls}`}><span>{titulo}: página {offset / limit + 1} · {quantidade} opções</span>{offset > 0 && <button type="button" className="secondary" disabled={carregando} onClick={() => { void mudar(Math.max(0, offset - limit)); }}>{titulo} anteriores</button>}{mais && <button type="button" className="secondary" disabled={carregando} onClick={() => { void mudar(offset + limit); }}>Próximos itens de {titulo.toLocaleLowerCase("pt-BR")}</button>}{quantidade === 0 && <span>Nenhum item elegível nesta página.</span>}</div>;
}
export function PreviaConferencia({ previa }: { previa: PreviaAcerto }) {
  return <section className={styles.stack}><h2>Prévia do acerto</h2><div className={styles.stat}><span>Total de obrigações a abater nesta relação</span><strong>{moedaNota(previa.total_aplicar)}</strong></div><p className={styles.notice}>Este total soma abatimentos de obrigações, não dinheiro novo nem saldo de caixa. Esta prévia não reserva saldo e não altera as notas. Se um recurso mudar antes da efetivação, o lote será recusado integralmente.</p><div><h3>Fontes e sobra por pagamento</h3>{previa.fontes.map(f => <p className={styles.source} key={f.pagamento_id}>{f.codigo} · disponível antes: {moedaNota(f.saldo_antes)} · aplicação: {moedaNota(f.valor_aplicar)} · sobra no pagamento: {moedaNota(f.saldo_depois)}</p>)}</div><PreviaCreditos previa={previa} /><div><h3>Notas após a aplicação prevista</h3>{previa.notas.map(n => <p className={styles.source} key={n.nota_id}>Nota #{n.nota_id} · {n.numero_documento} · saldo antes: {moedaNota(n.saldo_antes)} · aplicação: {moedaNota(n.valor_aplicar)} · saldo depois: {moedaNota(n.saldo_depois)}</p>)}</div></section>;
}

function DadosAcerto({ pessoas, relacao, pessoaId, consulta, enviando, trocarTitular, trocarRelacao }: { pessoas: CadastroPessoa[]; relacao: RelacaoNota; pessoaId: string; consulta: ReturnType<typeof useRecursos>; enviando: boolean; trocarTitular: (id: string) => void; trocarRelacao: (r: RelacaoNota) => void }) {
  return <div className={styles.form}><label>Relação<select name="relacao" value={relacao} disabled={consulta.carregando || enviando} onChange={e => { trocarRelacao(e.target.value as RelacaoNota); }}><option value="cliente">Cliente · a receber</option><option value="fornecedor">Fornecedor · a pagar</option></select></label><label>Titular<select name="pessoa_id" value={pessoaId} disabled={consulta.carregando || enviando} onChange={e => trocarTitular(e.target.value)} required><option value="">Selecione o cadastro</option>{pessoasElegiveis(pessoas, relacao).map(p => <option key={p.id} value={p.id}>{p.nome} · #{p.id}</option>)}</select></label><label>Data do acerto<input name="data" type="date" disabled={enviando} required /></label><label>Referência do acerto<input name="referencia" disabled={enviando} minLength={3} maxLength={220} required /></label><label className={styles.wide}>Observação<textarea name="observacao" disabled={enviando} minLength={3} maxLength={4000} rows={2} required /></label><div className={styles.wide}><button type="button" className="secondary" disabled={!pessoaId || consulta.carregando || enviando} onClick={() => { void consulta.carregar(); }}>{consulta.carregando ? "Consultando…" : "Consultar pagamentos, créditos e notas elegíveis"}</button>{consulta.erro && <p role="alert" className={styles.error}>{consulta.erro}</p>}</div></div>;
}

function alterouProposta(target: EventTarget) { return !(target instanceof HTMLInputElement && target.name === "confirmacao_gravacao"); }

function itemFormulario(p: Par): AcertoItemInput { const comum = { nota_id: p.nota?.id ?? 0, valor: Number(p.valor) }; return p.tipo === "credito" ? { ...comum, credito_id: p.credito?.id ?? 0 } : { ...comum, pagamento_id: p.pagamento?.id ?? 0 }; }
function PreviaCreditos({ previa }: { previa: PreviaAcerto }) {
  return <div><h3>Créditos de conta e saldo previsto</h3>{previa.creditos.length ? previa.creditos.map(c => <p className={styles.source} key={c.credito_id}><Link href={`/creditos/${c.credito_id}`}>{c.codigo}</Link> · disponível antes: {moedaNota(c.saldo_antes)} · aplicação: {moedaNota(c.valor_aplicar)} · disponível depois no crédito: {moedaNota(c.saldo_depois)}<br />Origem: <Link href={`/acertos/${c.acerto_origem_id}`}>acerto #{c.acerto_origem_id}</Link> · <Link href={`/pagamentos/${c.pagamento_origem_id}`}>pagamento #{c.pagamento_origem_id}</Link>. A disponibilidade do pagamento de origem permanece separada para o reconhecimento.</p>) : <p>Nenhum crédito utilizado nesta proposta.</p>}</div>;
}
