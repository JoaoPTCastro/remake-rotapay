"use client";

import { useEffect, useRef, useState } from "react";
import { CircleUserRound } from "lucide-react";
import type { NavItem } from "./Shell";

export default function UserMenu({ items }: { items: NavItem[] }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open ]);

  return (
    <div className="usermenu-wrap" ref={wrapRef}>
      <button
        type="button"
        className="iconbtn"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Menu do usuário"
        title="Conta e configurações"
        onClick={() => setOpen((o) => !o)}
      >
        <CircleUserRound size={18} aria-hidden="true" />
      </button>
      {open && (
        <div className="usermenu-pop" role="menu" aria-label="Conta e configurações">
          {items.map((n) => (
            <a key={n.href} href={n.href} role="menuitem" onClick={() => setOpen(false)}>
              {n.icon}<span>{n.label}</span>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
