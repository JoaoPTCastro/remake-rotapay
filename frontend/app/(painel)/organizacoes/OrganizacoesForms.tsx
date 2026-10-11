"use client";

import { useActionState } from "react";
import { aceitarConvite, criarConvite, criarOrganizacao, revogarConvite, selecionarOrganizacao, provisionarOrganizacao } from "../../../lib/organizacoes-actions";
import type { EstadoOrganizacao } from "../../../lib/organizacoes-types";
import styles from "./Organizacoes.module.css";

const inicial: EstadoOrganizacao = { ok: false, mensagem: "" };
function Retorno({ estado }: { estado: EstadoOrganizacao }) {
  return estado.mensagem ? <div role={estado.ok ? "status" : "alert"}><p className={estado.ok ? "pos" : "error"}>{estado.mensagem}</p>{estado.token && <><p>Entregue este código ao fornecedor por um canal privado. Se ainda não possui conta, abra /convite para cadastrar-se. Se já possui, entre com o email convidado e aceite em Organizações.</p><code className={styles.token}>{estado.token}</code></>}</div> : null;
}

export function CriarOrganizacaoForm() {
  const [estado, acao, pendente] = useActionState(criarOrganizacao, inicial);
  return <form action={acao} className={styles.form}><label>Nome da organização<input name="nome" required minLength={2} maxLength={120} /></label><button disabled={pendente}>{pendente ? "Criando…" : "Criar organização"}</button><Retorno estado={estado} /></form>;
}

export function CriarConviteForm({ organizacaoId }: { organizacaoId: number }) {
  const [estado, acao, pendente] = useActionState(criarConvite.bind(null, organizacaoId), inicial);
  return <form action={acao} className={styles.form}><label>Nome do fornecedor<input name="nome" required minLength={2} maxLength={120} /></label><label>Email da conta do fornecedor<input name="email" type="email" required maxLength={160} /></label><p className={styles.status}>O fornecedor pode criar sua conta em /convite ou aceitar com uma conta existente deste email. Nenhuma mensagem é enviada automaticamente.</p><button disabled={pendente}>{pendente ? "Criando…" : "Criar convite"}</button><Retorno estado={estado} /></form>;
}

export function AceitarConviteForm() {
  const [estado, acao, pendente] = useActionState(aceitarConvite, inicial);
  return <form action={acao} className={styles.form}><label>Código do convite<input name="token" type="password" required minLength={32} maxLength={128} autoComplete="off" spellCheck={false} /></label><button disabled={pendente}>{pendente ? "Aceitando…" : "Aceitar convite"}</button><Retorno estado={estado} /></form>;
}

export function RevogarConviteForm({ organizacaoId, conviteId }: { organizacaoId: number; conviteId: number }) {
  const [estado, acao, pendente] = useActionState(revogarConvite.bind(null, organizacaoId, conviteId), inicial);
  return <form action={acao} className={styles.form}><label><input name="confirmar" type="checkbox" required /> Confirmo a revogação deste convite</label><button className="secondary" disabled={pendente}>{pendente ? "Revogando…" : "Revogar convite"}</button><Retorno estado={estado} /></form>;
}

export function SelecionarOrganizacaoForm({ organizacaoId }: { organizacaoId: number }) {
  const [estado, acao, pendente] = useActionState(selecionarOrganizacao.bind(null, organizacaoId), inicial);
  return <form action={acao} className={styles.form}><button disabled={pendente}>{pendente ? "Entrando…" : "Entrar no financeiro desta loja"}</button><Retorno estado={estado} /></form>;
}

export function ProvisionarOrganizacaoForm({ organizacaoId }: { organizacaoId: number }) {
  const [estado, acao, pendente] = useActionState(provisionarOrganizacao.bind(null, organizacaoId), inicial);
  return <form action={acao} className={styles.form}><p>Será criado um ambiente vazio, com registros e arquivos separados das outras lojas.</p><label><input name="confirmar" type="checkbox" required /> Confirmo a preparação deste ambiente</label><button disabled={pendente}>{pendente ? "Preparando…" : "Preparar ambiente financeiro"}</button><Retorno estado={estado} /></form>;
}
