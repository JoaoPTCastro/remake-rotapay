import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function GET(req: Request) {
  const qs = new URL(req.url).searchParams.toString();
  const token = (await cookies()).get("token")?.value;
  const res = await fetch(`${API_URL}/simulacao?${qs}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json({ error: "falha na simulação" }, { status: res.status });
  }
  return NextResponse.json(await res.json());
}
