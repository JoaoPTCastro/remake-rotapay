import { redirect } from "next/navigation";
import Extrato from "../../../components/Extrato";

type SP = { [k: string]: string | string[] | undefined };

const FILTROS = ["q", "representante_id", "fornecedor_id", "status", "data_ini", "data_fim"] as const;

function str(v: string | string[] | undefined) {
  return typeof v === "string" ? v : "";
}

export default async function PIX({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  const ativos = FILTROS.filter((k) => str(sp[k]) !== "");
  if (ativos.length > 0) {
    const qs = new URLSearchParams();
    for (const k of ativos) qs.set(k, str(sp[k]));
    redirect(`/controle?${qs.toString()}`);
  }
  return (
    <div>
      <h1>Registrar PIX</h1>
      <p className="muted">Registre uma entrada em menos de 30 segundos. Para consultar, filtrar, exportar ou conciliar, acesse o <a href="/controle">Controle</a>.</p>
      <Extrato modo="registro" />
    </div>
  );
}