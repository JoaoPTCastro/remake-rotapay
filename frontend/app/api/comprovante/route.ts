import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

// Download/visualização autenticada: o browser não tem o Bearer (httpOnly),
// então o proxy anexa o token e devolve o arquivo. Sem isso todo clique dá 401.
// mid = comprovante da movimentação (download); cid = comprovante por identificador (ver no
// navegador com &ver=1 ou baixar sem ele).
export async function GET(req: Request) {
  const params = new URL(req.url).searchParams;
  const mid = params.get("mid");
  const cid = params.get("cid");
  const ver = params.get("ver") === "1";
  if (!mid && !cid) {
    return NextResponse.json({ error: "mid ou cid obrigatório" }, { status: 400 });
  }
  const token = (await cookies()).get("token")?.value;
  if (!token) return NextResponse.json({ error: "não autenticado" }, { status: 401 });
  const alvo = mid ? `/movimentacoes/${mid}/comprovante` : `/comprovantes/${cid}/arquivo`;
  const res = await fetch(`${API_URL}${alvo}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json({ error: "comprovante não encontrado" }, { status: 404 });
  }
  const buf = await res.arrayBuffer();
  const nome = mid ? `comprovante-${mid}` : `comprovante-${cid}`;
  return new NextResponse(buf, {
    headers: {
      "Content-Type": res.headers.get("content-type") ?? "application/octet-stream",
      "Content-Disposition": `${ver ? "inline" : "attachment"}; filename="${nome}"`,
    },
  });
}
