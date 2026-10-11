import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { API_URL } from "../../../../lib/api";
export async function GET(req: Request) {
  const params = new URL(req.url).searchParams; const nota = params.get("nota") ?? ""; const anexo = params.get("anexo") ?? "";
  if (!/^\d+$/.test(nota) || !/^\d+$/.test(anexo)) return NextResponse.json({ error: "Identificador inválido." }, { status: 400 });
  const token = (await cookies()).get("token")?.value;
  if (!token) return NextResponse.json({ error: "Entre novamente para baixar o arquivo." }, { status: 401 });
  try {
    const resposta = await fetch(`${API_URL}/notas/${nota}/anexos/${anexo}/arquivo`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
    if (!resposta.ok) return NextResponse.json({ error: "Não foi possível baixar este anexo." }, { status: resposta.status });
    return new NextResponse(resposta.body, { headers: { "Content-Type": resposta.headers.get("content-type") ?? "application/octet-stream", "Content-Disposition": resposta.headers.get("content-disposition") ?? "attachment", "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" } });
  } catch { return NextResponse.json({ error: "Não foi possível acessar o arquivo. Tente novamente." }, { status: 502 }); }
}
