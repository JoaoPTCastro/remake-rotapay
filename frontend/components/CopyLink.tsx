"use client";

import { useState } from "react";
import CopyKey from "./CopyKey";

// Copia o link ABSOLUTO (com origem), pronto para enviar no WhatsApp.
export default function CopyLink({ path }: { path: string }) {
  const [url, setUrl] = useState("");
  return (
    <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
      <button
        type="button"
        className="secondary"
        onClick={() => setUrl(`${window.location.origin}${path}`)}
      >
        Gerar link
      </button>
      {url && <CopyKey value={url} label="Copiar link" />}
    </span>
  );
}
