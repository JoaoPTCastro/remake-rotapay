"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { acompanharAcerto, efetivarAcerto, desfazerAcerto } from "../../../lib/acertos-actions";
import type { Acerto, AcertoResultado } from "../../../lib/acertos-types";
import styles from "./Acertos.module.css";
function useOperacao() {
  const router = useRouter(); const [resultado, setResultado] = useState<AcertoResultado | null>(null); const [enviando, setEnviando] = useState(false); const bloqueio = useRef(false);
  async function enviar(formEl: HTMLFormElement, acao: (f: FormData) => Promise<AcertoResultado>) {
    if (bloqueio.current) return;
    bloqueio.current = true; setEnviando(true); const form = new FormData(formEl);
    try { const res = await acao(form); setResultado(res); if (res.ok) { formEl.reset(); router.refresh(); } }
    catch { setResultado({ ok: false, mensagem: "A resposta não foi concluída. Atualize o histórico para conferir o estado do acerto." }); }
    finally { bloqueio.current = false; setEnviando(false); }
  }
  return { resultado, enviando, enviar };
}
function Feedback({ resultado }: { resultado: AcertoResultado | null }) {
  const router = useRouter(); if (!resultado) return null;
  return <div><p role={resultado.ok ? "status" : "alert"} className={resultado.ok ? styles.ok : styles.error}>{resultado.mensagem}</p>{!resultado.ok && <p>Se o saldo ou a nota mudou depois da prévia, será necessário criar outro rascunho e obter nova confirmação externa. <button type="button" className="secondary" onClick={() => router.refresh()}>Atualizar histórico</button></p>}</div>;
}
export function AcompanhamentoAcerto({ acerto, operacao }: { acerto: Acerto; operacao: "enviar" | "confirmar" }) {
  const { resultado, enviando, enviar } = useOperacao(); const envio = operacao === "enviar";
  return <section className={styles.box}><h2>{envio ? "Registrar envio externo" : "Registrar confirmação externa"}</h2><p className={styles.notice}>{envio ? "Envie a relação pelos meios utilizados pela loja fora do RotaPay. Depois, registre aqui a referência e o contexto desse envio. O sistema não envia mensagens." : "Registre a concordância obtida fora do RotaPay após a conferência da relação. Esta é uma declaração do operador com referência externa; não comprova a identidade do titular nem verifica mensagens automaticamente."}</p><form className={styles.form} onSubmit={e => { e.preventDefault(); void enviar(e.currentTarget, f => acompanharAcerto(acerto.id, operacao, f)); }}><label>Referência {envio ? "do envio" : "da confirmação"}<input name="referencia" minLength={3} maxLength={220} required /></label><label>Observação {envio ? "do envio" : "da confirmação"}<textarea name="observacao" minLength={3} maxLength={4000} rows={2} required /></label><label className={`${styles.check} ${styles.wide}`}><input name="confirmacao_operacao" type="checkbox" required />{envio ? "Confirmo que disponibilizei esta relação ao titular fora do RotaPay." : "Confirmo que o titular conferiu e concordou com esta relação fora do RotaPay."}</label><div className={styles.wide}><button disabled={enviando}>{enviando ? "Registrando…" : envio ? "Registrar envio externo" : "Registrar confirmação externa"}</button><Feedback resultado={resultado} /></div></form></section>;
}
export function EfetivacaoAcerto({ acerto }: { acerto: Acerto }) {
  const { resultado, enviando, enviar } = useOperacao();
  return <section className={styles.box}><h2>Efetivar acerto</h2><p className={styles.notice}>A efetivação aplica todos os pares nas notas originais e consome o saldo de cada fonte, pagamento ou crédito de conta, somente nesta relação. Usar crédito mantém o pagamento de origem com o valor reconhecido separado. Qualquer divergência de saldo ou alteração desde a prévia bloqueia o lote inteiro. Sobra permanece na respectiva fonte; nenhum crédito adicional é criado.</p><form onSubmit={e => { e.preventDefault(); void enviar(e.currentTarget, f => efetivarAcerto(acerto.id, f)); }}><label className={styles.check}><input name="confirmacao" type="checkbox" required />Conferi o acerto {acerto.codigo} e confirmo a efetivação de todos os seus pares.</label><button disabled={enviando}>{enviando ? "Efetivando…" : "Efetivar acerto completo"}</button><Feedback resultado={resultado} /></form></section>;
}
export function DesfazerAcerto({ acerto, operacao }: { acerto: Acerto; operacao: "estornar" | "cancelar" }) {
  const { resultado, enviando, enviar } = useOperacao(); const estorno = operacao === "estornar";
  return <details className={styles.box}><summary>{estorno ? "Estornar acerto inteiro" : "Cancelar rascunho do acerto"}</summary><p>{estorno ? "O estorno desfaz todas as aplicações deste acerto nesta relação. O saldo usado retorna ao pagamento ou ao crédito utilizado. O pagamento que originou o reconhecimento de crédito permanece separado; a outra relação continua independente." : "O cancelamento encerra este acerto sem criar aplicações em notas."}</p><form className={styles.form} onSubmit={e => { e.preventDefault(); void enviar(e.currentTarget, f => desfazerAcerto(acerto.id, operacao, f)); }}><label>Motivo<textarea name="motivo" minLength={3} maxLength={4000} rows={2} required /></label><label>Sua senha de confirmação<input name="senha" type="password" autoComplete="current-password" required /></label><div className={styles.wide}><button disabled={enviando}>{enviando ? "Salvando…" : estorno ? "Confirmar estorno integral" : "Confirmar cancelamento"}</button><Feedback resultado={resultado} /></div></form></details>;
}
export function AcertoOperacoes({ acerto: a }: { acerto: Acerto }) {
  return <><p><Link href={`/acertos/${a.id}/conferencia`}>Abrir resumo local para conferência e impressão</Link></p>{a.relacao === "fornecedor" && a.status === "rascunho" && <AcompanhamentoAcerto acerto={a} operacao="enviar" />}{a.relacao === "fornecedor" && a.status === "enviado" && <AcompanhamentoAcerto acerto={a} operacao="confirmar" />}{podeEfetivar(a) && <EfetivacaoAcerto acerto={a} />}{a.status === "efetivado" && !temCreditoAtivo(a) && <DesfazerAcerto acerto={a} operacao="estornar" />}{podeCancelar(a) && <DesfazerAcerto acerto={a} operacao="cancelar" />}</>;
}
function podeEfetivar(a: Acerto) { return a.relacao === "fornecedor" ? a.status === "confirmado" : a.status === "rascunho"; }
function podeCancelar(a: Acerto) { return ["rascunho", "enviado", "confirmado"].includes(a.status); }

function temCreditoAtivo(a: Acerto) { return a.creditos?.some(c => c.status !== "revertido") ?? false; }
