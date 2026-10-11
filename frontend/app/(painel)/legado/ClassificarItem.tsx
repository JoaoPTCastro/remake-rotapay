"use client";
import { useRef, useState } from "react";
import { prepararClassificacaoLegado, confirmarClassificacaoLegado } from "../../../lib/legado-actions";
import { NOMES_DECISOES, type DecisaoLegado, type ItemClassificacaoLegado, type ItemInventarioLegado, type PreviaLegado, type ReciboLegado } from "../../../lib/legado-types";
import ResumoValores from "./ResumoValores";
import styles from "./Legado.module.css";

type Revisao = { dados: PreviaLegado; item: ItemClassificacaoLegado; chave: string };
export default function ClassificarItem({ origem }: { origem: ItemInventarioLegado }) {
  const [decisao, setDecisao] = useState<DecisaoLegado>("pendente");
  const [evidencia, setEvidencia] = useState("");
  const [par, setPar] = useState("");
  const [previa, setPrevia] = useState<Revisao | null>(null);
  const [confirmado, setConfirmado] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [mensagem, setMensagem] = useState("");
  const [recibo, setRecibo] = useState<ReciboLegado | null>(null);
  const revisao = useRef(0);
  const enviando = useRef(false);
  function invalidar() { revisao.current += 1; setPrevia(null); setConfirmado(false); setMensagem(""); }
  function itemAtual(): ItemClassificacaoLegado {
    const escolhido = origem.relacoes_conhecidas.find(p => `${p.pessoa_id}:${p.relacao}` === par);
    return { fonte: origem.fonte, fonte_id: origem.fonte_id, snapshot_hash: origem.snapshot_hash,
      decisao, evidencia: evidencia.trim(), ...(escolhido ? escolhido : {}) };
  }
  async function preparar() {
    if (enviando.current) return;
    enviando.current = true; setOcupado(true); setMensagem(""); setPrevia(null); setConfirmado(false);
    const versao = revisao.current;
    const item = itemAtual();
    try {
      const resultado = await prepararClassificacaoLegado(item);
      if (versao !== revisao.current) return;
      if (!resultado.ok) { setMensagem(resultado.mensagem); return; }
      if (!resultado.dados.hash_previa || resultado.dados.conversao_habilitada !== false || resultado.dados.impacto_financeiro !== "nenhum") { setMensagem("A prévia não confirma o bloqueio financeiro. Atualize a página."); return; }
      setPrevia({ dados: resultado.dados, item, chave: crypto.randomUUID() });
    } finally { enviando.current = false; setOcupado(false); }
  }
  async function confirmar() {
    if (!previa || !confirmado || enviando.current) return;
    enviando.current = true; setOcupado(true); setMensagem("");
    try {
      const resultado = await confirmarClassificacaoLegado(previa.item, previa.dados.hash_previa, previa.chave);
      if (!resultado.ok) { setMensagem(resultado.mensagem); return; }
      setRecibo(resultado.dados); setPrevia(null); setConfirmado(false);
    } finally { enviando.current = false; setOcupado(false); }
  }
  if (origem.classificacao || recibo) return <ClassificacaoRegistrada origem={origem} recibo={recibo} />;
  return <form className={styles.form} onSubmit={e => { e.preventDefault(); void preparar(); }}>
    <label>Decisão<select value={decisao} disabled={ocupado} onChange={e => { invalidar(); setDecisao(e.target.value as DecisaoLegado); }}>{Object.entries(NOMES_DECISOES).map(([v,n]) => <option key={v} value={v}>{n}</option>)}</select></label>
    <label>Evidência da classificação<textarea value={evidencia} required minLength={3} maxLength={500} disabled={ocupado} onChange={e => { invalidar(); setEvidencia(e.target.value); }} placeholder="Descreva a evidência consultada e as dúvidas que permanecem." /></label>
    <label>Cadastro e relação documentados (opcional)<select value={par} disabled={ocupado} onChange={e => { invalidar(); setPar(e.target.value); }}><option value="">Sem associação adicional</option>{origem.relacoes_conhecidas.map(p => <option key={`${p.pessoa_id}:${p.relacao}`} value={`${p.pessoa_id}:${p.relacao}`}>Cadastro #{p.pessoa_id} · {p.relacao === "cliente" ? "Cliente" : "Fornecedor"}</option>)}</select></label>
    <p className="muted">Escolha apenas uma relação já documentada. Não conhecer a origem mantém a decisão pendente; uma projeção não comprova obrigação nem quitação.</p>
    <button disabled={ocupado}>{ocupado ? "Processando…" : "Revisar classificação"}</button>
    {mensagem && <p role="alert" className="error">{mensagem}</p>}
    {previa && <RevisarPrevia previa={previa} confirmado={confirmado} ocupado={ocupado} setConfirmado={setConfirmado} confirmar={confirmar} />}
  </form>;
}

function ClassificacaoRegistrada({ origem, recibo }: { origem: ItemInventarioLegado; recibo: ReciboLegado | null }) {
  const decisao = origem.classificacao?.decisao ?? recibo?.itens[0]?.decisao ?? "pendente";
  const id = origem.classificacao?.lote_id ?? recibo?.id;
  return <div role="status"><p>Classificação registrada: {NOMES_DECISOES[decisao]}. Recibo #{id}. Esta origem não pode ser classificada novamente.</p><p className="muted">O recibo é histórico e imutável. Classificar como pendente não resolve pendências nem permite reclassificação neste fluxo.</p>{origem.classificacao?.snapshot_atual === false && <p className="error">A origem mudou depois da classificação. O recibo mantém os dados históricos; ele não valida os valores atuais.</p>}</div>;
}
function RevisarPrevia({ previa, confirmado, ocupado, setConfirmado, confirmar }: { previa: Revisao; confirmado: boolean; ocupado: boolean; setConfirmado: (v: boolean) => void; confirmar: () => Promise<void> }) {
  const normalizado = previa.dados.itens[0];
  return <div className={styles.preview}><h3>Prévia — sem impacto financeiro</h3><p>Origem #{previa.item.fonte_id} · {NOMES_DECISOES[previa.item.decisao]}</p><p>Evidência: {previa.item.evidencia}</p><p>{previa.item.pessoa_id ? `Cadastro #${previa.item.pessoa_id} · ${previa.item.relacao === "cliente" ? "Cliente" : "Fornecedor"}` : "Nenhuma associação adicional selecionada."}</p>{normalizado && <ResumoValores valores={normalizado.valores} />}<p>Esta confirmação registra a classificação e preserva a origem. Não cria notas, pagamentos, créditos ou saldo utilizável. O recibo é imutável; pendências continuam exigindo investigação.</p>{normalizado?.pendencias?.length ? <p>Pendências: {normalizado.pendencias.map(p => p.replaceAll("_", " ")).join(" · ")}</p> : null}<label className={styles.check}><input type="checkbox" checked={confirmado} disabled={ocupado} onChange={e => setConfirmado(e.target.checked)} />Revisei esta origem, estes valores, esta evidência e esta decisão. Confirmo somente a classificação.</label><button type="button" disabled={!confirmado || ocupado} onClick={() => { void confirmar(); }}>{ocupado ? "Confirmando…" : "Confirmar classificação"}</button></div>;
}
