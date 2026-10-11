"use client";

import { useState } from "react";

export default function CopyKey({ value, label }: { value: string; label?: string }) {
  const [ok, setOk] = useState(false);
  const [falhou, setFalhou] = useState(false);
  return (
    <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
      <code>{value}</code>
      <button
        type="button"
        className="secondary"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(value);
            setOk(true);
            setFalhou(false);
            setTimeout(() => setOk(false), 2000);
          } catch {
            setFalhou(true);
          }
        }}
      >
        {ok ? "Copiado!" : (label ?? "Copiar")}
      </button>
      {falhou && <span className="muted">selecione e copie manualmente</span>}
    </span>
  );
}
