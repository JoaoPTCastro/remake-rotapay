"use client";
import { perspectives } from "./sales-content";
import { useState } from "react";
import s from "./SalesPage.module.css";
import {
  ArrowUpRight,
  ArrowRight,
  Check,
  Link2,
  Wallet,
  ShieldCheck,
  ReceiptText,
} from "lucide-react";
import Link from "next/link";
import Image from "next/image";
export default function Participants() {
  const [tab, setTab] = useState(0);
  const view = perspectives[tab];
  const ViewIcon = view.icon;
  return (
    <section className={s.perspectives} id="recursos">
      <div className={s.section}>
        <div className={s.sectionHeading}>
          <h2>
            Uma operação.
            <br />
            <span>Cada pessoa no seu lugar.</span>
          </h2>
          <p>
            A loja organiza. O vendedor entrega. O cliente paga. O fornecedor
            acompanha suas relações.
          </p>
        </div>
        <div
          className={s.tabs}
          role="tablist"
          aria-label="Visões dos participantes"
        >
          {perspectives.map((p, i) => (
            <button
              key={p.name}
              role="tab"
              id={`tab-${i}`}
              aria-selected={tab === i}
              aria-controls="participant-panel"
              tabIndex={tab === i ? 0 : -1}
              onClick={() => setTab(i)}
              onKeyDown={(e) => {
                if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                  e.preventDefault();
                  const next = (tab + (e.key === "ArrowRight" ? 1 : 3)) % 4;
                  setTab(next);
                  document.getElementById(`tab-${next}`)?.focus();
                }
              }}
            >
              {p.name}
              <ArrowUpRight size={17} />
            </button>
          ))}
        </div>
        <div
          className={s.participant}
          role="tabpanel"
          id="participant-panel"
          aria-labelledby={`tab-${tab}`}
          tabIndex={0}
        >
          <div>
            <ViewIcon size={36} />
            <h3>{view.title}</h3>
            <p>{view.text}</p>
            <Link href="https://app.rotapay.site/login" className={s.textLink}>
              Acessar o aplicativo <ArrowRight size={18} />
            </Link>
          </div>
          <div className={s.preview} data-screen>
            <div className={s.previewBar}>
              <Image
                src="/brand/rotapay-mark.svg"
                alt=""
                width={24}
                height={24}
              />
              <span>Visão de {view.name.toLowerCase()}</span>
              <span className={s.previewDots}>● ● ●</span>
            </div>
            <div className={s.previewBody}>
              <span>{view.label}</span>
              <strong>{view.amount}</strong>
              <div className={s.previewStatus}>
                <Check size={16} />
                {view.status}
              </div>
              <div className={s.previewRow}>
                <span>Pagamento</span>
                <b>R$ 500,00</b>
              </div>
              <div className={s.previewRow}>
                <span>Histórico</span>
                <b>Disponível para consulta</b>
              </div>
            </div>
            <div className={s.previewCaption}>
              Exemplo ilustrativo, com dados fictícios
            </div>
          </div>
        </div>
        <div className={s.featureList}>
          {[
            {
              icon: Link2,
              title: "Cobranças por link",
              text: "Informações organizadas para o cliente pagar.",
            },
            {
              icon: ReceiptText,
              title: "Comprovantes e notas",
              text: "Documentos ligados à relação e ao pagamento.",
            },
            {
              icon: Wallet,
              title: "Abatimentos e saldos",
              text: "Aplicação explícita dos valores às obrigações.",
            },
            {
              icon: ShieldCheck,
              title: "Acesso por relação",
              text: "Cada loja e fornecedor com seu escopo autorizado.",
            },
          ].map((f) => (
            <div key={f.title}>
              <f.icon size={23} />
              <h3>{f.title}</h3>
              <p>{f.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
