"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { Search, X } from "lucide-react";
import type { NavItem } from "./Shell";

export type NavGroup = { title: string; items: NavItem[] };

const FOCUSABLE = "input, button";

const norm = (s: string) => s.toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");

function matches(item: NavItem, ql: string) {
  return ql === "" || norm(item.label + " " + item.href).includes(ql);
}

function filterGroups(groups: NavGroup[], ql: string) {
  const rendered: { title: string; items: NavItem[]; start: number }[] = [];
  let offset = 0;
  for (const g of groups) {
    const items = g.items.filter((i) => matches(i, ql));
    rendered.push({ title: g.title, items, start: offset });
    offset += items.length;
  }
  return rendered;
}

function ResultList({
  rendered,
  active,
  onSelect,
  onHover,
}: {
  rendered: { title: string; items: NavItem[]; start: number }[];
  active: number;
  onSelect: (i: number) => void;
  onHover: (i: number) => void;
}) {
  return (
    <ul id="cm-list" role="listbox" aria-label="Telas e ações" className="cm-list">
      {rendered.map((g) => (
        <li key={g.title} role="presentation" className="cm-group">
          {g.items.length > 0 && <div className="cm-group-title">{g.title}</div>}
          {g.items.map((item, j) => {
            const i = g.start + j;
            return (
              <button
                key={item.href}
                type="button"
                role="option"
                id={`cm-opt-${i}`}
                tabIndex={-1}
                aria-selected={i === active}
                className={`cm-opt${i === active ? " active" : ""}`}
                onClick={() => onSelect(i)}
                onMouseMove={() => onHover(i)}
              >
                <span className="cm-opt-icon">{item.icon}</span>
                <span className="cm-opt-label">{item.label}</span>
                <kbd className="cm-opt-route">{item.href}</kbd>
              </button>
            );
          })}
        </li>
      ))}
    </ul>
  );
}

function MenuDialog({ groups, onClose }: { groups: NavGroup[]; onClose: () => void }) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const ql = q.trim().toLowerCase();
  const rendered = filterGroups(groups, ql);
  const flat = rendered.flatMap((g) => g.items);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    document.getElementById(`cm-opt-${active}`)?.scrollIntoView({ block: "nearest" });
  }, [active]);

  function go(index: number) {
    const item = flat[index];
    if (!item) return;
    router.push(item.href);
    onClose();
  }

  function onQueryChange(e: React.ChangeEvent<HTMLInputElement>) {
    setQ(e.target.value);
    setActive(0);
  }

  function trapFocus(e: React.KeyboardEvent) {
    const els = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
    if (!els.length) return;
    const first = els[0];
    const last = els[els.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => (flat.length ? (a + 1) % flat.length : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => (flat.length ? (a - 1 + flat.length) % flat.length : 0));
    } else if (e.key === "Enter" && (e.target as HTMLElement).tagName !== "BUTTON") {
      e.preventDefault();
      go(active);
    } else if (e.key === "Tab") {
      trapFocus(e);
    }
  }

  return (
    <div className="cm-backdrop" onMouseDown={onClose}>
      <div
        ref={dialogRef}
        id="cm-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Busca global"
        className="cm-dialog"
        onKeyDown={onKeyDown}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="cm-head">
          <Search size={18} aria-hidden="true" />
          <input
            ref={inputRef}
            role="combobox"
            aria-label="Buscar telas e ações"
            aria-expanded="true"
            aria-autocomplete="list"
            aria-controls={flat.length > 0 ? "cm-list" : undefined}
            aria-activedescendant={flat[active] ? `cm-opt-${active}` : undefined}
            type="text"
            placeholder="Buscar telas e ações…"
            autoComplete="off"
            spellCheck={false}
            value={q}
            onChange={onQueryChange}
          />
          <button type="button" className="cm-close" onClick={onClose} aria-label="Fechar busca">
            <X size={16} aria-hidden="true" />
          </button>
        </div>
        {flat.length > 0 ? (
          <ResultList rendered={rendered} active={active} onSelect={go} onHover={setActive} />
        ) : (
          <p className="cm-empty" role="status">{`Nenhum resultado para "${q}".`}</p>
        )}
        <div className="cm-foot">
          <span><kbd>↑↓</kbd> navegar</span>
          <span><kbd>Enter</kbd> abrir</span>
          <span><kbd>Esc</kbd> fechar</span>
        </div>
      </div>
    </div>
  );
}

export default function CommandMenu({ groups }: { groups: NavGroup[] }) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const isMac = useSyncExternalStore(
    () => () => {},
    () => /Mac|iPhone|iPad/i.test(navigator.platform),
    () => false,
  );

  function openDialog() {
    setOpen(true);
  }

  function closeDialog() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  useEffect(() => {
    function onGlobalKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (open) {
          setOpen(false);
          triggerRef.current?.focus();
        } else {
          setOpen(true);
        }
      } else if (e.key === "Escape" && open) {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onGlobalKeyDown);
    return () => window.removeEventListener("keydown", onGlobalKeyDown);
  }, [open]);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className="cm-trigger"
        onClick={openDialog}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? "cm-dialog" : undefined}
        aria-label="Busca global"
      >
        <Search size={16} aria-hidden="true" />
        <span className="cm-trigger-label">Buscar</span>
        <kbd className="cm-kbd">{isMac ? "⌘K" : "Ctrl K"}</kbd>
      </button>
      {open && <MenuDialog groups={groups} onClose={closeDialog} />}
    </>
  );
}