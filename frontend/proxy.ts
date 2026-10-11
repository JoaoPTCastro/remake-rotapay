import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

function publicEntry(req: NextRequest, token: string | undefined) {
  if (
    !token &&
    req.nextUrl.pathname === "/" &&
    req.headers.get("host")?.split(":")[0] !== "app.rotapay.site"
  )
    return NextResponse.rewrite(new URL("/conheca", req.url));
  return null;
}

export function proxy(req: NextRequest) {
  const token = req.cookies.get("token")?.value;
  const { pathname } = req.nextUrl;
  const entry = publicEntry(req, token);
  if (entry) return entry;
  // Assets da marca e favicon precisam carregar também antes do login.
  if (pathname.startsWith("/brand/") || pathname === "/icon.svg")
    return NextResponse.next();

  if (pathname.startsWith("/api/")) return NextResponse.next();
  if (
    ["/cadastro-loja", "/cadastro-loja/", "/conheca", "/conheca/", "/e", "/e/", "/convite", "/convite/"].includes(
      pathname,
    )
  )
    return NextResponse.next(); // páginas públicas com autorização própria
  if (["/pagar/", "/v/"].some((prefix) => pathname.startsWith(prefix)))
    return NextResponse.next(); // links públicos
  if (!token && pathname !== "/login")
    return NextResponse.redirect(new URL("/login", req.url));
  if (token && pathname === "/login")
    return NextResponse.redirect(new URL("/", req.url));
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
