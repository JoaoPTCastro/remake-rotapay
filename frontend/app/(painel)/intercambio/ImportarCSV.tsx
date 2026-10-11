"use client";
import { useState } from "react";
import { previaCSV, importarCSV } from "../../../lib/intercambio-actions";
import type { TipoImportacao, PreviaImportacao, ConfirmacaoImportacao } from "../../../lib/intercambio-types";
import DadosPrevia from "./DadosPrevia";
import styles from "./Intercambio.module.css";
export default function ImportarCSV() {
  const [tipo, setTipo] = useState<TipoImportacao>("cadastros");
  const [texto, setTexto] = useState(""); const [previa, setPrevia] = useState<PreviaImportacao | null>(null);
  const [resultado, setResultado] = useState<ConfirmacaoImportacao | null>(null);
  const [chave, setChave] = useState(""); const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState(""); const [confirmado, setConfirmado] = useState(false);
  function invalidar() { setPrevia(null); setConfirmado(false); setResultado(null); setChave(""); setErro(""); }
  async function ler(arquivo: File | undefined) {
    invalidar(); setTexto(""); if (!arquivo) return;
    if (arquivo.size > 1024 * 1024) { setErro("O arquivo deve ter até 1 MB."); return; }
    setOcupado(true);
    try { setTexto(new TextDecoder("utf-8", { fatal: true }).decode(await arquivo.arrayBuffer())); }
    catch { setErro("Arquivo inválido: salve o CSV com codificação UTF-8."); }
    finally { setOcupado(false); }
  }
  async function executar(etapa: "previa" | "importar") {
    if (ocupado) return;
    const arquivo = new File([texto], `${tipo}.csv`, { type: "text/csv" });
    if (!texto.trim() || arquivo.size > 1024 * 1024) { setErro("Informe um CSV de até 1 MB."); return; }
    setOcupado(true); setErro("");
    const form = new FormData(); form.set("f", arquivo);
    try {
      if (etapa === "previa") await preparar(form);
      else await confirmar(form);
    } catch { setErro("A conexão foi interrompida. Confira o resultado no cadastro/notas antes de iniciar outra tentativa. Você pode repetir esta confirmação com a mesma chave."); }
    finally { setOcupado(false); }
  }
  async function preparar(form: FormData) { const r = await previaCSV(tipo, form); if (!r.ok) { setErro(r.mensagem); return; } setPrevia(r.dados); setChave(crypto.randomUUID()); setConfirmado(false); setResultado(null); }
  async function confirmar(form: FormData) { if (!previa?.pode_importar || !confirmado || !chave) return; form.set("token_previa", previa.token_previa); form.set("chave_idempotencia", chave); form.set("confirmacao", "true"); const r = await importarCSV(tipo, form); if (!r.ok) { setErro(r.mensagem); return; } setResultado(r.dados); }
  return <section className={styles.box}><h2>Importar novos registros</h2><p>CSV UTF-8 separado por ponto e vírgula, até 1 MB e 500 linhas de dados. Use o modelo abaixo. A prévia não grava; o lote só é confirmado integralmente quando todas as linhas são válidas.</p><fieldset className={styles.importacao} disabled={ocupado || resultado !== null}><label>Tipo<select value={tipo} onChange={e => { setTipo(e.target.value as TipoImportacao); invalidar(); }}><option value="cadastros">Cadastros</option><option value="notas">Novas notas abertas</option></select></label><label>Arquivo CSV<input type="file" accept=".csv,text/csv" onChange={e => { void ler(e.target.files?.[0]); }} /></label><label>Conteúdo CSV<textarea rows={10} value={texto} onChange={e => { setTexto(e.target.value); invalidar(); }} /></label><button type="button" onClick={() => { void executar("previa"); }}>Conferir prévia</button></fieldset>{ocupado && <p role="status">Processando arquivo…</p>}{erro && <p role="alert" className={styles.error}>{erro}</p>}{previa && <Previa previa={previa} />}{previa && !resultado && <><label><input type="checkbox" checked={confirmado} disabled={ocupado || !previa.pode_importar} onChange={e => setConfirmado(e.target.checked)} /> Conferi todas as linhas e autorizo criar os registros novos deste lote.</label><button disabled={ocupado || !previa.pode_importar || !confirmado} onClick={() => { void executar("importar"); }}>Confirmar importação</button><p className={styles.scope}>Alterar o conteúdo exige outra prévia. Após uma falha de confirmação, confira os registros antes de preparar outro lote.</p></>}{resultado && <div role="status"><h3>Importação #{resultado.importacao_id} concluída{resultado.repetida ? " · tentativa já processada" : ""}</h3><p>{resultado.ids_criados.length} criados · {resultado.ids_ignorados.length} já existentes e preservados.</p><button onClick={() => { invalidar(); setTexto(""); }}>Preparar outro lote</button></div>}</section>;
}
function Previa({ previa: p }: { previa: PreviaImportacao }) { return <section><h3>Prévia · {p.resumo.total} linhas</h3><p>{p.resumo.novos} novos · {p.resumo.ignorados} ignorados · {p.resumo.erros} com erro.</p>{!p.pode_importar && <p role="alert">Corrija os erros e gere outra prévia. Nenhuma linha foi importada.</p>}<div className={styles.table}><table><thead><tr><th>Linha</th><th>Situação</th><th>Dados conferidos</th><th>Erros</th></tr></thead><tbody>{p.linhas.map(l => <tr key={l.linha}><td data-label="Linha">{l.linha}</td><td data-label="Situação">{l.status === "novo" ? "Novo" : l.status === "ignorado" ? "Já existente · preservado" : "Erro"}</td><td data-label="Dados conferidos"><DadosPrevia dados={l.dados} /></td><td data-label="Erros">{l.erros.join(" · ") || "—"}</td></tr>)}</tbody></table></div></section>; }
