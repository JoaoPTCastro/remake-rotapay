import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function POST(req: Request) {
  const mid = new URL(req.url).searchParams.get("mid");
  if (!mid) return NextResponse.json({ error: "mid obrigatório" }, { status: 400 });
  const token = (await cookies()).get("token")?.value;
  const fd = await req.formData();
  const res = await fetch(`${API_URL}/movimentacoes/${mid}/comprovante`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: fd,
    cache: "no-store",
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : "falha no envio";
    return NextResponse.json({ error: detail }, { status: res.status });
  }
  return NextResponse.json(body);
}
