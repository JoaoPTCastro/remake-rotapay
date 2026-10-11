"use client";
import s from "./SalesPage.module.css";
import { ReceiptText } from "lucide-react";
export default function Problem() {
  return (
    <section className={`${s.section} ${s.problem}`} id="problema">
      <div className={s.problemTitle}>
        <h2>
          O comprovante chegou.
          <br />
          <span>A dúvida ficou.</span>
        </h2>
        <p>
          A venda aconteceu. Mas, para fechar o acerto, alguém ainda precisa
          reconstruir o caminho do dinheiro.
        </p>
      </div>
      <div className={s.questions}>
        <p>“Esse PIX é de qual venda?”</p>
        <p>“O fornecedor já recebeu?”</p>
        <p>“Esse valor já foi abatido?”</p>
        <p>“Quanto ainda falta pagar?”</p>
        <div className={s.problemFoot}>
          <ReceiptText size={21} />
          <span>
            Uma conversa. Outra planilha.
            <br />
            Mais uma conferência manual.
          </span>
        </div>
      </div>
      <div className={s.problemStatement} data-consequences>
        <h3>O custo da desorganização.</h3>
        <div className={s.consequenceLines}>
          <p data-consequence>Cobrar quem <em>já pagou.</em></p>
          <p data-consequence>Repetir <em>um acerto.</em></p>
          <p data-consequence>Descobrir uma diferença <em>tarde demais.</em></p>
        </div>
        <strong data-consequence>Seu controle precisa acompanhar sua venda.</strong>
      </div>
    </section>
  );
}
