import VisaoGeral from "./VisaoGeral";
import type { ParamsVisaoGlobal } from "../../../lib/visao-geral-types";
export default async function VisaoGeralPage({ searchParams }: { searchParams: Promise<ParamsVisaoGlobal> }) {
  return <VisaoGeral params={await searchParams} base="/visao-geral" />;
}
