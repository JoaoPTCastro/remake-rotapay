"use client";
import { faq } from "./sales-content";
import s from "./SalesPage.module.css";
import { ChevronDown } from "lucide-react";
export default function Questions() {
  return (
    <section className={`${s.section} ${s.faq}`} id="duvidas">
      <h2>
        Clareza antes
        <br />
        <span>de começar.</span>
      </h2>
      <div>
        {faq.map(([q, a]) => (
          <details key={q}>
            <summary>
              {q}
              <ChevronDown size={20} />
            </summary>
            <p>{a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
