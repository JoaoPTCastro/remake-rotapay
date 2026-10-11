"use client";
import s from "./SalesPage.module.css";
import {
  ArrowUpRight,
  ArrowRight,
  Check,
  Link2,
  Store,
  FileCheck2,
  ChevronDown,
} from "lucide-react";
export default function Hero() {
  return (
    <section className={s.hero} data-hero-section>
      <div className={s.heroCopy}>
        <h1 data-hero>
          Seu cliente pagou.
          <br />
          <span>
            O controle não
            <br />
            pode parar aí.
          </span>
        </h1>
        <p className={s.heroLead} data-hero>
          O RotaPay organiza as cobranças, os comprovantes e os pagamentos aos
          fornecedores.
        </p>
        <p className={s.heroSupport} data-hero>
          Do link PIX que o vendedor entrega ao cliente até o acerto com o
          fornecedor. Cada etapa com um lugar para ser acompanhada.
        </p>
        <div className={s.heroActions} data-hero>
          <a href="#demonstracao" className={s.primary}>
            Conhecer o RotaPay <ArrowUpRight size={20} />
          </a>
          <a href="#como-funciona" className={s.textLink}>
            Entender o caminho <ArrowRight size={17} />
          </a>
        </div>
        <div className={s.heroNote} data-hero>
          <span /> Cobranças por link · acesso separado por loja
        </div>
      </div>
      <div
        className={s.heroVisual}
        aria-label="Ilustração do link PIX ao acerto. Valores de exemplo."
      >
        <div className={s.orbit} data-orbit />
        <div className={s.orbitSmall} />
        <svg
          className={s.heroRoute}
          viewBox="0 0 560 560"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M90 130H325Q440 130 440 245V300Q440 405 335 405H170Q90 405 90 490"
            stroke="#64D5E8"
            strokeWidth="2"
            strokeDasharray="7 9"
          />
          <circle cx="90" cy="130" r="7" fill="#64D5E8" />
          <circle cx="90" cy="490" r="7" fill="#64D5E8" />
        </svg>
        <div className={s.linkCard} data-float="one">
          <div className={s.cardTop}>
            <Link2 size={19} />
            <span>Link gerado pela loja</span>
            <ArrowUpRight size={17} />
          </div>
          <div className={s.cardValue}>
            R$ 500<span>,00</span>
          </div>
          <p>Valor fixo ou preenchido pela cliente</p>
          <a className={s.linkUrl} href="#pagamento-em-movimento" aria-label="Ver o caminho do pagamento">
            <span>app.rotapay.site / pagar / …</span>
            <Check size={15} />
          </a>
          <div className={s.cardFoot}>
            <span className={s.avatar}>
              <Store size={15} />
            </span>{" "}
            Loja → vendedor → cliente
          </div>
        </div>
        <div className={s.receiptCard} data-float="two">
          <span className={s.receiptIcon}>
            <FileCheck2 size={22} />
          </span>
          <div>
            <strong>Comprovante organizado</strong>
            <p>Ligado ao pagamento certo</p>
          </div>
        </div>
        <div className={s.balanceCard}>
          <div>
            <span>Acerto com o fornecedor</span>
            <strong>Uma rota. Um histórico.</strong>
          </div>
          <ArrowUpRight size={25} />
        </div>
        <span className={s.visualCaption}>
          Ilustração do fluxo · valores fictícios
        </span>
      </div>
      <div className={s.heroBottom}>
        <span>
          FEITO PARA QUEM VENDE
          <br />E ACERTA COM FORNECEDORES
        </span>
        <span>
          Loja <ArrowRight size={15} /> Vendedor <ArrowRight size={15} />{" "}
          Cliente <ArrowRight size={15} /> Fornecedor
        </span>
        <a href="#problema" aria-label="Conhecer o problema">
          <ChevronDown size={22} />
        </a>
      </div>
    </section>
  );
}
