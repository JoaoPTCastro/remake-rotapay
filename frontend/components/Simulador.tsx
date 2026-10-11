"use client";

import { useState } from "react";

type Pessoa = { id: number; nome: string };
type Resultado = {
  pix_disponivel: number; divida_aberta: number; tolerancia: number;
  tolerancia_em_uso: number; pode_pagar_sem_exceder: number;
  pode_pagar_total: number; credito_gerado_se_pagar_tudo: number;
};

export default function Simulador({ reps, forns }: { reps: Pessoa[]; forns: Pessoa[] }) {
  const [rep, setRep] = useState("");
  const [forn, setForn] = useState("");
  const [res, setRes] = useState<Resultado | null>(null);
  const [err, setErr] = useState("");

  async function simular(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    const r = await fetch(`/api/simulacao?representante_id=${rep}&fornecedor_id=${forn}`);
    if (!r.ok) {
      setErr("Falha na simulação.");
      return;
    }
    setRes(await r.json());
  }

  const BRL = (v: number) => `R$ ${v.toFixed(2)}`;
  return (
    <div>
      <h2>Simulador: quanto o rifeiro pode pagar?</h2>
      <form onSubmit={simular} className="grid">
        <select value={rep} onChange={(e) => setRep(e.target.value)} required>
          <option value="" disabled>Representante…</option>
          {reps.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
        </select>
        <select value={forn} onChange={(e) => setForn(e.target.value)} required>
          <option value="" disabled>Fornecedor…</option>
          {forns.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
        </select>
        <button type="submit">Simular (não persiste nada)</button>
      </form>
      {err && <p className="error">{err}</p>}
      {res && (
        <div className="cards">
          <div className="card"><small>PIX disponível</small><strong>{BRL(res.pix_disponivel)}</strong></div>
          <div className="card"><small>Dívida aberta</small><strong>{BRL(res.divida_aberta)}</strong></div>
          <div className="card"><small>Pode pagar sem exceder</small><strong>{BRL(res.pode_pagar_sem_exceder)}</strong></div>
          <div className="card"><small>Com tolerância ({BRL(res.tolerancia)}, em uso {BRL(res.tolerancia_em_uso)})</small><strong>{BRL(res.pode_pagar_total)}</strong></div>
          <div className="card"><small>Crédito se pagar tudo</small><strong>{BRL(res.credito_gerado_se_pagar_tudo)}</strong></div>
        </div>
      )}
    </div>
  );
}
