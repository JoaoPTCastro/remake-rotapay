import { NextResponse } from "next/server";
export async function POST(req: Request) {
  const origin = req.headers.get("origin");
  let validOrigin = false;
  try {
    validOrigin = !!origin && new URL(origin).host === req.headers.get("host");
  } catch {
    validOrigin = false;
  }
  if (!validOrigin) {
    return NextResponse.json(
      { error: "Origem da solicitação inválida." },
      { status: 403 },
    );
  }
  try {
    const body: unknown = await req.json();
    const res = await fetch(
      `${process.env.API_URL ?? "http://localhost:8000"}/publico/interesse-lojas`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-RotaPay-Client-IP": req.headers.get("x-rotapay-client-ip") ?? "",
          "X-RotaPay-Proxy-Key": process.env.PRIVATE_PROXY_KEY ?? "",
        },
        body: JSON.stringify(body),
        cache: "no-store",
      },
    );
    if (!res.ok) {
      const messages: Record<number, string> = {
        409: "Não foi possível usar este email. Se já possui conta, entre no sistema.",
        422: "Confira os campos e os requisitos da senha.",
        429: "Muitas tentativas. Aguarde uma hora para tentar novamente.",
        503: "Cadastro indisponível no momento. Tente novamente mais tarde.",
      };
      return NextResponse.json(
        {
          error:
            messages[res.status] ??
            "Não foi possível criar sua conta. Tente novamente.",
        },
        { status: res.status },
      );
    }
    const data = await res.json();
    return NextResponse.json(data, { status: 201 });
  } catch {
    return NextResponse.json(
      { error: "Serviço indisponível. Tente novamente em alguns instantes." },
      { status: 503 },
    );
  }
}
