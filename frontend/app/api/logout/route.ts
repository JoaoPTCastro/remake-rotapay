import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

function limpa(res: NextResponse) {
  res.cookies.delete("token");
  res.cookies.delete("perfil");
  return res;
}

export async function POST() {
  return limpa(NextResponse.json({ ok: true }));
}

// Usado quando a API responde 401 (sessão morta/expirada): limpa os
// cookies e manda ao login. O destino é restrito a caminho interno.
export async function GET(req: NextRequest) {
  const next = req.nextUrl.searchParams.get("next") ?? "/login";
  const dest = next.startsWith("/") ? next : "/login";
  return limpa(NextResponse.redirect(new URL(dest, req.url)));
}
