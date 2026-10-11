import { NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function POST(req: Request) {
  const { email, senha } = await req.json();
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-RotaPay-Client-IP": req.headers.get("x-rotapay-client-ip") ?? "",
      "X-RotaPay-Proxy-Key": process.env.PRIVATE_PROXY_KEY ?? "",
    },
    body: JSON.stringify({ email, senha }),
  });
  if (!res.ok) {
    return NextResponse.json(
      { error: "Credenciais inválidas" },
      { status: 401 },
    );
  }
  const data = await res.json();
  const out = NextResponse.json({ ok: true, user: data.user });
  out.cookies.set("token", data.access_token, {
    secure: process.env.NODE_ENV === "production",
    httpOnly: true,
    path: "/",
    maxAge: 8 * 3600,
    sameSite: "lax",
  });
  out.cookies.set("perfil", data.user.perfil, {
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 8 * 3600,
    sameSite: "lax",
  });
  return out;
}
