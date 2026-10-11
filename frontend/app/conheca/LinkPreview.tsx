"use client";
import { useState } from "react";
import { ArrowRight, Smartphone, Link2 } from "lucide-react";
import s from "./SalesPage.module.css";
import d from "./LinkPreview.module.css";
const currency = (amount: string) => Number(amount).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
export default function LinkPreview() {
  const [mode, setMode] = useState<"fixo" | "aberto">("fixo");
  const [fixed, setFixed] = useState("500");
  const [entered, setEntered] = useState("");
  const [prepared, setPrepared] = useState(false);
  const [error, setError] = useState("");
  const amount = mode === "fixo" ? fixed : entered;
  const valid = Number.isFinite(Number(amount)) && Number(amount) >= 0.01 && Number(amount) <= 999999.99;
  function changeMode(next: "fixo" | "aberto") {
    setMode(next); setPrepared(false); setError("");
  }
  return (
    <section id="link-demonstrativo" className={`${s.section} ${d.section}`} aria-labelledby="link-title">
      <div className={d.explanation}>
        <h2 id="link-title">O link que chega<br /><span>à sua cliente.</span></h2>
        <p>A loja organiza a cobrança. O vendedor envia o link no atendimento, inclusive na venda porta a porta. A cliente acessa pelo celular, sem criar uma conta.</p>
        <div className={d.modes} role="group" aria-label="Tipo de link demonstrativo">
          <button type="button" aria-pressed={mode === "fixo"} onClick={() => changeMode("fixo")}>Valor fixo</button>
          <button type="button" aria-pressed={mode === "aberto"} onClick={() => changeMode("aberto")}>Cliente informa o valor</button>
        </div>
        {mode === "fixo" ? <label className={d.field}>Valor definido na cobrança (R$)<input type="number" inputMode="decimal" min="0.01" max="999999.99" step="0.01" value={fixed} onChange={e => {setFixed(e.target.value);setPrepared(false);setError("");}} /></label> : <p className={d.modeHint}>Com o valor aberto, a cliente preenche quanto vai pagar diretamente na página do link.</p>}
        <div className={d.delivery}><Link2 size={20} aria-hidden="true" /><div><strong>Pronto para o vendedor compartilhar</strong><span>app.rotapay.site/pagar/exemplo</span></div></div>
        <p className={d.notice}>Link e loja fictícios. Esta demonstração não gera uma cobrança nem movimenta dinheiro.</p>
      </div>
      <div className={d.phone} aria-label="Prévia do link no celular da cliente">
        <div className={d.phoneTop}><Smartphone size={16} aria-hidden="true" /> Visão da cliente</div>
        <div className={d.screen}>
          <div className={d.store}><span>LE</span><div><strong>Loja Exemplo</strong><small>Atendimento com Vendedor Exemplo</small></div></div>
          <h3>Seu pagamento por PIX</h3>
          <p>{mode === "fixo" ? "Confira o valor da sua compra." : "Informe o valor combinado com o vendedor."}</p>
          {mode === "fixo" ? <div className={d.amount} aria-live="polite">{valid ? currency(fixed) : "Informe um valor válido"}</div> : <label className={d.field}>Quanto você vai pagar? (R$)<input type="number" inputMode="decimal" min="0.01" max="999999.99" step="0.01" placeholder="Ex.: 250,00" value={entered} onChange={e => {setEntered(e.target.value);setPrepared(false);setError("");}} /></label>}
          {error && <p className={d.error} role="alert">{error}</p>}
          <button type="button" className={d.pay} onClick={() => {if (!valid) {setError("Informe um valor entre R$ 0,01 e R$ 999.999,99.");return;} setError("");setPrepared(true);}}>Simular preparação do PIX <ArrowRight size={17} aria-hidden="true" /></button>
          {prepared && <div className={d.result} role="status"><strong>Valor escolhido: {currency(amount)}</strong><p>No aplicativo, o próximo passo apresenta as instruções de pagamento. Aqui, a simulação termina antes de gerar o PIX.</p></div>}
          <p className={d.screenNote}>Prévia ilustrativa · nenhum pagamento é realizado</p>
        </div>
      </div>
    </section>
  );
}
