"use client";

import Link from "next/link";
import { useActionState } from "react";
import { registrarFornecedor, type EstadoCadastroConvite } from "./actions";

const inicial: EstadoCadastroConvite = { ok: false, mensagem: "" };

export default function CadastroConvite() {
  const [estado, acao, pendente] = useActionState(registrarFornecedor, inicial);
  if (estado.ok) return <div><p role="status">{estado.mensagem}</p><Link href="/login">Entrar na minha conta</Link></div>;
  return <form action={acao} style={{ display: "grid", gap: 16 }}>
    <label>Código recebido da loja<input name="token" type="password" required minLength={32} maxLength={128} autoComplete="off" spellCheck={false} /></label>
    <label>Seu nome<input name="nome" required maxLength={120} autoComplete="name" /></label>
    <label>Nova senha<input name="senha" type="password" required minLength={8} maxLength={128} autoComplete="new-password" /></label>
    <label>Confirmar senha<input name="confirmacao" type="password" required minLength={8} maxLength={128} autoComplete="new-password" /></label>
    <p className="muted">Sua conta usará o email convidado pela loja. O código é informado somente neste formulário.</p>
    <button disabled={pendente}>{pendente ? "Criando conta…" : "Criar conta e aceitar convite"}</button>
    {estado.mensagem && <p role="alert" className="error">{estado.mensagem}</p>}
  </form>;
}
