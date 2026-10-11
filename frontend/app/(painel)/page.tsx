import { redirect } from "next/navigation";
import { perfil } from "../../lib/api";
import DashboardLegado from "./DashboardLegado";
import VisaoGeral from "./visao-geral/VisaoGeral";
import type { ParamsVisaoGlobal } from "../../lib/visao-geral-types";
export default async function Dashboard({ searchParams }: { searchParams: Promise<ParamsVisaoGlobal> }) {
  if (await perfil() === "fornecedor") redirect("/organizacoes");
  const params = await searchParams;
  return params.escopo === "legado" ? <DashboardLegado /> : <VisaoGeral params={params} />;
}
