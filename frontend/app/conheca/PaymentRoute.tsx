"use client";
import { steps } from "./sales-content";
import s from "./SalesPage.module.css";
import Image from "next/image";
export default function PaymentRoute() {
  return (
    <section className={`${s.section} ${s.routeSection}`} id="como-funciona">
      <div className={s.routeIntro}>
        <h2>
          O link é o começo.
          <br />
          <span>O acerto é o destino.</span>
        </h2>
        <p>
          Enviar o PIX facilita a venda. Acompanhar o que acontece depois dá
          clareza para sua operação.
        </p>
        <div className={s.routeLabel}>
          <Image src="/brand/rotapay-mark.svg" alt="" width={42} height={42} />
          <div>
            <strong>Rota do Pagamento</strong>
            <span>Da cobrança ao saldo em aberto.</span>
          </div>
        </div>
      </div>
      <div className={s.routeSteps} data-route>
        <div className={s.routeRail} />
        <div className={s.routeLine} data-route-line />
        {steps.map((step, i) => (
          <article key={step.title} className={s.step} data-step>
            <span className={s.stepNumber}>{i + 1}</span>
            <div>
              <step.icon size={24} />
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </div>
          </article>
        ))}
      </div>
      <p className={s.routeDisclaimer}>
        Conferência, declaração de recebimento e abatimento são etapas
        distintas. A versão de testes não confirma PIX automaticamente pelo
        banco.
      </p>
    </section>
  );
}
