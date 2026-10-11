import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { API_URL } from "../../../../lib/api";
function destino(params: URLSearchParams) {
  const tipo = params.get("tipo"); const operacao = params.get("operacao");
  if (operacao === "modelo" && ["cadastros", "notas", "pagamentos"].includes(tipo ?? "")) return `/csv/modelos/${tipo}`;
  if (operacao !== "exportar" || !["cadastros", "notas"].includes(tipo ?? "")) return null;
  const query = new URLSearchParams();
  const permitidos = tipo === "cadastros" ? ["q", "tipo", "ativo"] : ["pessoa_id", "relacao", "status", "data_de", "data_ate"];
  for (const chave of permitidos) { const valor = params.get(chave === "tipo" ? "papel" : chave); if (valor) query.set(chave, valor); }
  return `/csv/exportar/${tipo}?${query}`;
}
export async function GET(req: Request) {
  const path = destino(new URL(req.url).searchParams);
  if (!path) return NextResponse.json({ error: "Exportação inválida." }, { status: 400 });
  const token = (await cookies()).get("token")?.value;
  if (!token) return NextResponse.json({ error: "Entre novamente para baixar." }, { status: 401 });
  try {
    const r = await fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store", redirect: "error" });
    if (!r.ok) return NextResponse.json({ error: await mensagemDownload(r) }, { status: r.status });
    return new NextResponse(r.body, { headers: { "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": r.headers.get("content-disposition") ?? "attachment; filename=rotapay.csv", "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" } });
  } catch { return NextResponse.json({ error: "Não foi possível baixar. Tente novamente." }, { status: 502 }); }
}

async function mensagemDownload(r: Response) { if (r.status === 413) return "A exportação excede 10 mil registros. Refine os filtros e tente novamente."; try { const corpo = await r.json() as { detail?: unknown }; if (typeof corpo.detail === "string") return corpo.detail; } catch { /* Sem erro JSON. */ } return "Não foi possível exportar. Confira os filtros e seu acesso."; }
