"use client";

import { useEffect, useState } from "react";

export type SecaoConta = { id: string; label: string };

export default function ContaNav({ secoes }: { secoes: SecaoConta[] }) {
  const [ativa, setAtiva] = useState(secoes[0]?.id ?? "");

  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) setAtiva(e.target.id);
        }
      },
      { rootMargin: "-20% 0px -70% 0px" }
    );
    for (const s of secoes) {
      const el = document.getElementById(s.id);
      if (el) obs.observe(el);
    }
    return () => obs.disconnect();
  }, [secoes]);

  return (
    <nav className="conta-nav" aria-label="Seções da conta">
      {secoes.map((s) => (
        <a
          key={s.id}
          href={`#${s.id}`}
          className={s.id === ativa ? "active" : ""}
          aria-current={s.id === ativa ? "true" : undefined}
        >
          {s.label}
        </a>
      ))}
    </nav>
  );
}
