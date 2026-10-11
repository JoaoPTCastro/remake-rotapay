"use client";

import Link from "next/link";
import { useState } from "react";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Banknote, BookUser, ClipboardCheck, Link2,
  ArrowLeftRight, ChartCandlestick, HandCoins, ShieldCheck,
  GraduationCap, PanelLeftClose, PanelLeftOpen, Map, Gauge, Users, Store,
} from "lucide-react";
import LogoutButton from "./LogoutButton";
import ThemeToggle from "./ThemeToggle";
import CommandMenu, { type NavGroup } from "./CommandMenu";
import UserMenu from "./UserMenu";
import BrandMark from "./BrandMark";
import { BRAND } from "../lib/brand";

export type NavItem = { href: string; label: string; icon: React.ReactNode };

// Menu principal (definido pelo time): Início, PIX, Cadastro, Controle, Links
const PRINCIPAL: NavItem[] = [
  { href: "/", label: "Início", icon: <LayoutDashboard size={20} /> },
  { href: "/movimentacoes", label: "PIX", icon: <Banknote size={20} /> },
  { href: "/cadastro", label: "Cadastro", icon: <BookUser size={20} /> },
  { href: "/controle", label: "Controle", icon: <ClipboardCheck size={20} /> },
  { href: "/links", label: "Links", icon: <Link2 size={20} /> },
];

const GERENCIAR: NavItem[] = [
  { href: "/organizacoes", label: "Organizações e fornecedores", icon: <Store size={20} /> },
  { href: "/visao-geral", label: "Posições e notas abertas", icon: <LayoutDashboard size={20} /> },
  { href: "/configuracoes", label: "Configurações", icon: <ClipboardCheck size={20} /> },
  { href: "/intercambio", label: "Intercâmbio de dados", icon: <ArrowLeftRight size={20} /> },
  { href: "/legado", label: "Legado e classificação", icon: <ClipboardCheck size={20} /> },
  { href: "/extratos", label: "Extratos individuais", icon: <BookUser size={20} /> },
  { href: "/conciliacoes", label: "Conciliar", icon: <ArrowLeftRight size={20} /> },
  { href: "/projecoes", label: "Projeções", icon: <ChartCandlestick size={20} /> },
  { href: "/creditos", label: "Créditos de conta", icon: <HandCoins size={20} /> },
  { href: "/acertos", label: "Acertos", icon: <ClipboardCheck size={20} /> },
  { href: "/pagamentos", label: "Pagamentos", icon: <Banknote size={20} /> },
  { href: "/notas", label: "Notas e extratos", icon: <BookUser size={20} /> },
  { href: "/lancamentos", label: "Lançamentos", icon: <HandCoins size={20} /> },
  { href: "/historico", label: "Histórico", icon: <ShieldCheck size={20} /> },
  { href: "/usuarios", label: "Usuários", icon: <Users size={20} /> },
  { href: "/metricas", label: "Métricas", icon: <Gauge size={20} /> },
  { href: "/conta", label: "Conta", icon: <Store size={20} /> },
  { href: "/ajuda", label: "Ajuda", icon: <GraduationCap size={20} /> },
  { href: "/senha", label: "Trocar minha senha", icon: <ShieldCheck size={20} /> },
];

const TITLES: Record<string, string> = {
  "/organizacoes": "Organizações e fornecedores",
  "/": "Visão geral",
  "/visao-geral": "Posições e notas abertas",
  "/movimentacoes": "PIX",
  "/cadastro": "Cadastro",
  "/controle": "Controle de saídas",
  "/links": "Links do vendedor",
  "/conciliacoes": "Conciliação",
  "/projecoes": "Projeções",
  "/configuracoes": "Configurações",
  "/intercambio": "Intercâmbio de dados",
  "/legado": "Legado e classificação",
  "/extratos": "Extratos individuais",
  "/creditos": "Créditos de conta",
  "/acertos": "Acertos e conferência",
  "/pagamentos": "Pagamentos e aplicações",
  "/notas": "Notas e extratos",
  "/lancamentos": "Lançamentos",
  "/historico": "Histórico",
  "/usuarios": "Usuários",
  "/metricas": "Métricas",
  "/conta": "Conta da loja",
  "/ajuda": "Guia de uso",
  "/senha": "Trocar minha senha",
};

const principalPorPerfil = (perfil: string) => perfil === "fornecedor" ? [] : PRINCIPAL;
const destinosMoveis = (perfil: string, gerenciar: NavItem[], principal: NavItem[]) => perfil === "fornecedor" ? gerenciar : principal;
const tituloContexto = (perfil: string) => perfil === "fornecedor" ? "VÍNCULOS DE FORNECEDOR" : "PAINEL FINANCEIRO";
const atalhosExtras = (perfil: string) => perfil === "fornecedor" ? [] : [{ href: "/roadmap", label: "Roadmap", icon: <Map size={20} /> }];

export default function Shell({ children, perfil, lojaNome, organizacaoNome }: {
  children: React.ReactNode; perfil: string; lojaNome?: string; organizacaoNome?: string | null;
}) {
  const pathname = usePathname();
  const fornecedor = perfil === "fornecedor";
  const principal = principalPorPerfil(perfil);
  const [rail, setRail] = useState(
    () => typeof window !== "undefined" && localStorage.getItem("rail") === "1"
  );
  const toggleRail = () => {
    setRail((r) => {
      localStorage.setItem("rail", r ? "0" : "1");
      return !r;
    });
  };
  const gerenciar = GERENCIAR.filter(
    (g) =>
      (!fornecedor || g.href === "/organizacoes") &&
      (g.href !== "/historico" || perfil === "admin" || perfil === "financeiro") &&
      (g.href !== "/usuarios" || perfil === "admin")
  );
  // Itens que moram no menu do usuário (ícone no topo): fora da barra lateral.
  // Usuários e Métricas vivem como seções da guia Conta.
  const ITENS_USUARIO = ["/conta", "/usuarios", "/metricas", "/senha"];
  const ancora = (href: string) =>
    href === "/usuarios" ? "/conta#usuarios"
    : href === "/metricas" ? "/conta#metricas"
    : href === "/senha" ? "/conta#senha" : href;
  const menuUsuario = GERENCIAR.filter(
    (g) => !fornecedor && ITENS_USUARIO.includes(g.href) &&
      (g.href !== "/usuarios" || perfil === "admin")
  ).map((g) => ({ ...g, href: ancora(g.href) }));
  const sidebarGerenciar = gerenciar.filter((g) => !ITENS_USUARIO.includes(g.href));
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);
  const title = Object.entries(TITLES).find(([path]) => path === pathname || (path !== "/" && pathname.startsWith(path)))?.[1] ?? "Painel";
  const commandGroups: NavGroup[] = [
    { title: "Principal", items: principal },
    { title: "Gerenciar", items: [...gerenciar.map((g) => ({ ...g, href: ancora(g.href) })), ...atalhosExtras(perfil)] },
  ];

  return (
    <div className={`shell${rail ? " rail" : ""}`}>
      <aside className="sidebar" aria-label="Navegação principal" suppressHydrationWarning>
        <div className="brand">
          <BrandMark size={36} />
          <div className="brand-copy">
            <span>{BRAND.name}</span>
            {lojaNome && <small title={lojaNome}>{lojaNome}</small>}
          </div>
        </div>
        <nav className="nav">
          {!fornecedor && <div className="nav-group">Principal</div>}
          {principal.map((n) => (
            <a key={n.href} href={n.href} className={isActive(n.href) ? "active" : ""} title={n.label}>
              {n.icon}<span className="nav-label">{n.label}</span>
            </a>
          ))}
          <div className="nav-group">Gerenciar</div>
          {sidebarGerenciar.map((n) => (
            <a key={n.href} href={n.href} className={isActive(n.href) ? "active" : ""} title={n.label}>
              {n.icon}<span className="nav-label">{n.label}</span>
            </a>
          ))}
        </nav>
        <div className="sidebar-foot">
          {!fornecedor && <a href="/roadmap" className="btn-secondary" style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "center", marginBottom: 6 }}>
            <Map size={16} /> Roadmap
          </a>}
          <button type="button" className="iconbtn" onClick={toggleRail} title={rail ? "Expandir" : "Recolher"} style={{ width: "100%" }}>
            {rail ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>
      </aside>

      <div className="content">
        <div className="slimbar">
          <div>
            <span className="eyebrow">{BRAND.name} · {tituloContexto(perfil)}</span>
            {organizacaoNome && <p className="muted">Loja ativa: <strong>{organizacaoNome}</strong> · <Link href="/organizacoes">Trocar loja</Link></p>}
            <h1 className="chrome-title">{title}</h1>
          </div>
          <span className="sp"><CommandMenu groups={commandGroups} />{menuUsuario.length > 0 && <UserMenu items={menuUsuario} />}<span className="profile-pill">{perfil}</span><ThemeToggle /><LogoutButton /></span>
        </div>
        <main className="wrap">{children}</main>
      </div>

      <nav className="mobilebar" aria-label="Navegação móvel">
        {destinosMoveis(perfil, sidebarGerenciar, principal).map((n) => (
          <a key={n.href} href={n.href} className={isActive(n.href) ? "active" : ""}>
            {n.icon}{n.label}
          </a>
        ))}
      </nav>
    </div>
  );
}
