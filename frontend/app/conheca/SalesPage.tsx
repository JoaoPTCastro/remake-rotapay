"use client";
import { useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { ArrowUpRight, Menu, X } from "lucide-react";
import s from "./SalesPage.module.css";
import { useSalesMotion } from "./useSalesMotion";
import PaymentStory from "./PaymentStory";
import Hero from "./Hero";
import Problem from "./Problem";
import PaymentRoute from "./PaymentRoute";
import Participants from "./Participants";
import Questions from "./Questions";
import Demo from "./Demo";
export default function SalesPage() {
  const root = useRef<HTMLDivElement>(null);
  const [menu, setMenu] = useState(false);
  useSalesMotion(root);
  const closeMenu = () => setMenu(false);
  return (
    <div className={s.page} ref={root}>
      <a className={s.skip} href="#conteudo">
        Pular para o conteúdo
      </a>{" "}
      <header className={s.header}>
        <Link href="/conheca" aria-label="RotaPay, início" className={s.logo}>
          <Image
            src="/brand/rotapay-logo-dark.svg"
            width={144}
            height={42}
            alt="RotaPay"
            priority
          />
        </Link>
        <nav
          className={`${s.nav} ${menu ? s.navOpen : ""}`}
          aria-label="Navegação principal"
          id="sales-nav"
        >
          <a href="#como-funciona" onClick={closeMenu}>
            Como funciona
          </a>
          <a href="#recursos" onClick={closeMenu}>
            Recursos
          </a>
          <a href="#duvidas" onClick={closeMenu}>
            Dúvidas
          </a>
          <Link href="https://app.rotapay.site/login" className={s.navLogin}>
            Entrar no sistema <ArrowUpRight size={16} />
          </Link>
        </nav>
        <button
          className={s.menu}
          onClick={() => setMenu(!menu)}
          aria-label={menu ? "Fechar menu" : "Abrir menu"}
          aria-expanded={menu}
          aria-controls="sales-nav"
        >
          {menu ? <X /> : <Menu />}
        </button>
      </header>
      <main id="conteudo">
        <Hero />
        <PaymentStory />
        <Problem />
        <PaymentRoute />
        <Participants />
        <Questions />
        <Demo />
      </main>{" "}
      <footer className={s.footer}>
        <Image
          src="/brand/rotapay-logo-dark.svg"
          width={130}
          height={38}
          alt="RotaPay"
        />
        <p>
          O RotaPay organiza as cobranças, os comprovantes
          <br />e os pagamentos aos fornecedores.
        </p>
        <a href="#conteudo">
          Voltar ao início <ArrowUpRight size={17} />
        </a>
        <span>© {new Date().getFullYear()} RotaPay</span>
      </footer>
    </div>
  );
}
