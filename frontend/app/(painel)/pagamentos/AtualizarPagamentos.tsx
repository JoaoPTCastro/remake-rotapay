"use client";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
export default function AtualizarPagamentos() { const router = useRouter(); const [pendente, iniciar] = useTransition(); return <button type="button" className="secondary" disabled={pendente} onClick={() => iniciar(() => router.refresh())}>{pendente ? "Atualizando…" : "Atualizar consulta"}</button>; }
