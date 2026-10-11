import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { API_URL } from "../../../../lib/api";
import { consultaVisaoGlobal, filtrosVisaoGlobal } from "../../../../lib/visao-geral-types";
const HEADERS = { "Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff" };
const MAX_BYTES = 16 * 1024 * 1024;
function falha(status: number, mensagem = "Não foi possível exportar as posições.") {
  return NextResponse.json({ erro: mensagem }, { status, headers: HEADERS });
}
function parametros(params: URLSearchParams) {
  for (const [nome] of params) {
    if (!["relacao", "pessoa_id", "q"].includes(nome) || params.getAll(nome).length !== 1) return null;
  }
  return filtrosVisaoGlobal(Object.fromEntries(params));
}
async function lerLimitado(resposta: Response): Promise<Uint8Array | null> {
  if (!resposta.body) return null;
  const leitor = resposta.body.getReader(), partes: Uint8Array[] = [];
  let tamanho = 0;
  try {
    while (true) {
      const parte = await leitor.read();
      if (parte.done) break;
      tamanho += parte.value.byteLength;
      if (tamanho > MAX_BYTES) { await leitor.cancel(); return null; }
      partes.push(parte.value);
    }
  } finally { leitor.releaseLock(); }
  const dados = new Uint8Array(tamanho);
  let offset = 0;
  for (const parte of partes) { dados.set(parte, offset); offset += parte.byteLength; }
  return dados;
}
export async function GET(req: Request) {
  const filtros = parametros(new URL(req.url).searchParams);
  if (!filtros) return falha(400, "Filtros inválidos para exportação.");
  const token = (await cookies()).get("token")?.value;
  if (!token) return falha(401, "Entre no RotaPay para exportar.");
  try {
    const resposta = await fetch(`${API_URL}/visao-geral/export.csv?${consultaVisaoGlobal(filtros)}`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(30000) });
    if (!resposta.ok) return falha(resposta.status >= 500 ? 502 : resposta.status, resposta.status === 413 ? "A exportação excede 10.000 contas. Refine os filtros." : undefined);
    if (!resposta.headers.get("content-type")?.startsWith("text/csv")) return falha(502);
    const dados = await lerLimitado(resposta);
    if (!dados) return falha(413, "Arquivo excede o limite de exportação. Refine os filtros.");
    return new Response(new Blob([new Uint8Array(dados)]), { headers: { ...HEADERS, "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": `attachment; filename="rotapay-posicoes-${filtros.relacao}.csv"` } });
  } catch { return falha(502); }
}
