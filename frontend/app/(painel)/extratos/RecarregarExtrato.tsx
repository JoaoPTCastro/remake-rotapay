"use client";
import { useRouter } from "next/navigation";
export default function RecarregarExtrato() { const router = useRouter(); return <button type="button" className="secondary" onClick={() => router.refresh()}>Recarregar consulta</button>; }
