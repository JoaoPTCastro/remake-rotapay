import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { API_URL } from "../../../../lib/api";
function parametrosArquivo(params: URLSearchParams) { const pagamento = params.get("pagamento") ?? ""; const anexo = params.get("anexo") ?? ""; const modo = params.get("modo"); if (!/^[1-9]\d*$/.test(pagamento) || !/^[1-9]\d*$/.test(anexo)) return null; if (modo !== null && modo !== "inline") return null; return { pagamento, anexo, inline: modo === "inline" }; }
export async function GET(req: Request) {
  const p = parametrosArquivo(new URL(req.url).searchParams);
  if (!p) return NextResponse.json({ error: "Identificador ou modo de arquivo inválido." }, { status: 400 });
  const token = (await cookies()).get("token")?.value;
  if (!token) return NextResponse.json({ error: "Entre novamente para acessar o arquivo." }, { status: 401 });
  try { const resposta = await fetch(`${API_URL}/pagamentos/${p.pagamento}/anexos/${p.anexo}/arquivo${p.inline ? "?inline=true" : ""}`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store", redirect: "error" }); return respostaArquivo(resposta, p.inline); }
  catch { return NextResponse.json({ error: "Não foi possível acessar o arquivo. Tente novamente." }, { status: 502 }); }
}
function respostaArquivo(resposta: Response, inline: boolean) {
  if (!resposta.ok) return NextResponse.json({ error: "Não foi possível acessar este anexo." }, { status: resposta.status });
  const mime = resposta.headers.get("content-type")?.split(";")[0] ?? "application/octet-stream";
  if (inline && !["image/png", "image/jpeg", "image/webp", "application/pdf"].includes(mime)) return NextResponse.json({ error: "Formato indisponível para visualização. Baixe o original." }, { status: 415 });
  return new NextResponse(resposta.body, { headers: { "Content-Type": mime, "Content-Disposition": inline ? "inline" : resposta.headers.get("content-disposition") ?? "attachment", "Content-Security-Policy": "sandbox; default-src 'none'; frame-ancestors 'self'", "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" } });
}
