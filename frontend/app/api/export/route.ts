import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.API_URL ?? "http://localhost:8000";
const ALLOWED = new Set([
  "movimentacoes.csv",
  "conciliacoes.csv",
  "lancamentos.csv",
  "projecoes.csv",
  "posicao-fornecedores.csv",
  "auditoria.csv",
]);

export async function GET(req: Request) {
  const url = new URL(req.url);
  const file = url.searchParams.get("file") ?? "";
  if (!ALLOWED.has(file)) {
    return NextResponse.json({ error: "arquivo inválido" }, { status: 400 });
  }
  const token = (await cookies()).get("token")?.value;
  const qs = new URLSearchParams(url.searchParams);
  qs.delete("file");
  const res = await fetch(`${API_URL}/export/${file}?${qs.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json({ error: "falha na exportação" }, { status: res.status });
  }
  const buf = await res.arrayBuffer();
  return new NextResponse(buf, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="${file}"`,
    },
  });
}
