"use client";
import s from "./SalesPage.module.css";
import { MoveUpRight } from "lucide-react";
import Link from "next/link";
export default function Demo() {
  return (
    <section className={s.final} id="demonstracao">
      <div className={s.finalRoute} aria-hidden="true" />
      <div className={s.finalInner}>
        <h2>
          O cliente pagou.
          <br />
          <span>Continue no controle.</span>
        </h2>
        <p>
          Conheça o caminho do link PIX ao acerto com o fornecedor. Conte sobre sua operação
          da sua loja e comece em um ambiente exclusivo.
        </p>
        <Link
          href="https://app.rotapay.site/cadastro-loja"
          className={s.primary}
        >
          Solicitar avaliação <MoveUpRight size={20} />
        </Link>
        <p className={s.finalNote}>
          Sua loja começa com um ambiente vazio. Recebimentos e abatimentos
          dependem de conferência e ações dos participantes.
        </p>
      </div>
    </section>
  );
}
