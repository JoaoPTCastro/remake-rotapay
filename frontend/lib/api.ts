import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

export const API_URL = process.env.API_URL ?? "http://localhost:8000";

async function req(path: string, init?: RequestInit) {
  const jar = await cookies();
  const t = jar.get("token")?.value;
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(t ? { Authorization: `Bearer ${t}` } : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (res.status === 401) {
    // Sessão morta ou expirada: limpa os cookies e volta ao login
    // em vez de quebrar a página (sem isso, um token antigo prende
    // o usuário na tela de erro sem saída).
    redirect("/api/logout?next=/login");
  }
  if (!res.ok) {
    const text = await res.text();
    const err = new Error(`${res.status}: ${text}`) as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  const ct = res.headers.get("content-type") ?? "";
  return ct.includes("json") ? res.json() : res.text();
}

export const apiGet = (p: string) => req(p);
export const apiPost = (p: string, body?: unknown) =>
  req(p, { method: "POST", body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body) });
export const apiPatch = (p: string, body?: unknown) =>
  req(p, { method: "PATCH", body: JSON.stringify(body) });

export const apiDelete = (p: string) => req(p, { method: "DELETE" });

export type UsuarioAtual = { id: number; nome: string; email: string; perfil: string; ativo?: boolean; organizacao_id?: number; organizacao_nome?: string | null };
export const usuarioAtual = cache(async (): Promise<UsuarioAtual> => apiGet("/auth/me") as Promise<UsuarioAtual>);
export async function perfil(): Promise<string> {
  return (await usuarioAtual()).perfil;
}

export const apiPut = (p: string, body: unknown) => req(p, { method: "PUT", body: JSON.stringify(body) });
