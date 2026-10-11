"use client";
import { useState } from "react";
import s from "./SalesPage.module.css";
import { ArrowRight } from "lucide-react";
export default function Example() {
  const [applied, setApplied] = useState(false);
  return (
    <section className={`${s.section} ${s.example}`}>
      <div>
        <h2>
          O saldo precisa
          <br />
          <span>contar uma história.</span>
        </h2>
        <p>
          Sua loja tem R$ 2.000 em aberto com um fornecedor. Um pagamento de R$
          500 entra no acompanhamento. Depois da conferência, a loja pode
          aplicar esse valor à obrigação.
        </p>
        <p className={s.small}>
          Experimente o exemplo. Isso não movimenta dinheiro nem altera a
          demonstração.
        </p>
      </div>
      <div className={s.calculator}>
        <span>Exemplo de acerto</span>
        <div className={s.calcRow}>
          <span>Obrigação com fornecedor</span>
          <strong>R$ 2.000,00</strong>
        </div>
        <div className={s.calcRow}>
          <span>Pagamento disponível</span>
          <strong>R$ 500,00</strong>
        </div>
        <div className={s.calcTotal}>
          <span>
            Saldo {applied ? "após o abatimento" : "antes do abatimento"}
          </span>
          <strong aria-live="polite">
            {applied ? "R$ 1.500,00" : "R$ 2.000,00"}
          </strong>
        </div>
        <button className={s.primary} onClick={() => setApplied(!applied)}>
          {applied ? "Reiniciar exemplo" : "Simular abatimento de R$ 500"}
          <ArrowRight size={18} />
        </button>
        <p>O abatimento é uma ação explícita. Não acontece automaticamente.</p>
      </div>
    </section>
  );
}
