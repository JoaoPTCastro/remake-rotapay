"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

export default function DragDropUpload({ mid }: { mid: number }) {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(file: File) {
    setBusy(true);
    setMsg("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`/api/upload?mid=${mid}`, { method: "POST", body: fd });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail ?? body.error ?? `falha (${res.status})`);
      setMsg("Comprovante enviado — vai para a fila de leitura.");
      router.refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Falha no envio.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Enviar comprovante: arraste o arquivo ou pressione Enter para escolher"
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") input.current?.click(); }}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) void send(f); }}
      onClick={() => input.current?.click()}
      style={{
        border: `2px dashed ${drag ? "#0f172a" : "#cbd5e1"}`,
        borderRadius: 10, padding: 20, textAlign: "center", cursor: "pointer",
        background: drag ? "#f1f5f9" : "#fff",
      }}
    >
      <input
        ref={input} type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" hidden
        onChange={(e) => { const f = e.target.files?.[0]; if (f) void send(f); }}
      />
      <p>{busy ? "Enviando…" : "Arraste o comprovante para cá ou clique para escolher"}</p>
      <p className="muted">PDF, PNG ou JPG até 10 MB</p>
      {msg && <p className={msg.startsWith("Comprovante enviado") ? "muted" : "error"}>{msg}</p>}
    </div>
  );
}
