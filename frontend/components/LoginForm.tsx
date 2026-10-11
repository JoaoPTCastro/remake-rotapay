"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const fd = new FormData(e.currentTarget);
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: fd.get("email"), senha: fd.get("senha") }),
    });
    setLoading(false);
    if (!res.ok) {
      setError("Credenciais inválidas. Verifique email e senha.");
      return;
    }
    router.push("/");
  }

  return (
    <form onSubmit={submit} className="login-form">
      {error && <p className="error" role="alert">{error}</p>}
      <label className="muted" htmlFor="login-email">Email</label>
      <input id="login-email" name="email" type="email" placeholder="voce@sualoja.com" required autoComplete="username" />
      <label className="muted" htmlFor="login-senha">Senha</label>
      <input id="login-senha" name="senha" type="password" placeholder="Sua senha" required autoComplete="current-password" />
      <button type="submit" disabled={loading}>{loading ? "Entrando…" : "Entrar"}</button>
    </form>
  );
}
