import { unstable_rethrow } from "next/navigation";
import { apiGet } from "./api";
import type { RelacaoNota, Nota } from "./notas-types";
import type { Pagamento } from "./pagamentos-types";
import type { Credito } from "./creditos-types";
import type { Acerto } from "./acertos-types";
import type { ExtratoConsulta, ExtratoGlobal, ExtratoParams, ExtratoSecao, ExtratoEvento, ConsultaExtrato, ListaExtrato } from "./extratos-types";
import { estadosExtrato } from "./extratos-types";
export function parametrosExtrato(filtros: ExtratoParams, relacao: RelacaoNota): URLSearchParams {
  const qs = new URLSearchParams({ relacao });
  for (const chave of ["data_de", "data_ate"] as const) if (/^\d{4}-\d{2}-\d{2}$/.test(filtros[chave] ?? "")) qs.set(chave, filtros[chave] as string);
  for (const secao of ["notas", "pagamentos", "creditos", "acertos"] as const) { const chave = `${secao}_status` as const; if (estadosExtrato[secao].includes(filtros[chave] ?? "")) qs.set(chave, filtros[chave] as string); }
  for (const secao of ["notas", "pagamentos", "creditos", "acertos", "timeline"] as const) { const chave = `${secao}_offset` as const; const offset = Number.parseInt(filtros[chave] ?? "0", 10); if (Number.isSafeInteger(offset) && offset > 0) qs.set(chave, String(offset)); }
  return qs;
}
function queryLista(secao: ExtratoSecao, qs: URLSearchParams) {
  const query = new URLSearchParams({ relacao: qs.get("relacao") ?? "", limit: "50", offset: qs.get(`${secao}_offset`) ?? "0" });
  for (const data of ["data_de", "data_ate"]) if (qs.has(data)) query.set(data, qs.get(data) as string);
  if (qs.has(`${secao}_status`)) query.set("status", qs.get(`${secao}_status`) as string);
  return query;
}
async function consultarLista<T>(id: string, secao: ExtratoSecao, qs: URLSearchParams): Promise<ConsultaExtrato<T>> {
  try { const pagina = await apiGet(`/extratos/${id}/${secao}?${queryLista(secao, qs)}`) as ListaExtrato<T>; return { ok: true, pagina }; }
  catch (erro) { unstable_rethrow(erro); return { ok: false, mensagem: "Não foi possível carregar esta lista. Confira os filtros e tente novamente." }; }
}
export async function carregarExtrato(id: string, qs: URLSearchParams): Promise<ExtratoConsulta> {
  const [resumo, notas, pagamentos, creditos, acertos, timeline] = await Promise.all([apiGet(`/extratos/${id}?relacao=${qs.get("relacao")}`) as Promise<ExtratoGlobal>, consultarLista<Nota>(id, "notas", qs), consultarLista<Pagamento>(id, "pagamentos", qs), consultarLista<Credito>(id, "creditos", qs), consultarLista<Acerto>(id, "acertos", qs), consultarLista<ExtratoEvento>(id, "timeline", qs)]);
  return { resumo, notas, pagamentos, creditos, acertos, timeline };
}
