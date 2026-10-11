"use client";

import { useActionState } from "react";
import { adicionarMembro, atualizarMembro, confirmarRecebimento, salvarChave, vincularCadastro } from "../../../lib/fornecedor-actions";
import type { ChaveFornecedor } from "../../../lib/fornecedor-types";
import type { EstadoOrganizacao, MembroOrganizacao } from "../../../lib/organizacoes-types";
import styles from "./Organizacoes.module.css";

const inicial: EstadoOrganizacao = { ok: false, mensagem: "" };
function Retorno({ estado }: { estado: EstadoOrganizacao }) {
  return estado.mensagem ? <p role={estado.ok ? "status" : "alert"} className={estado.ok ? "pos" : "error"}>{estado.mensagem}</p> : null;
}
export function VincularCadastroForm({ org, usuario, pessoas }: { org: number; usuario: number; pessoas: { id: number; nome: string }[] }) {
  const [estado, acao, pendente] = useActionState(vincularCadastro.bind(null, org, usuario), inicial);
  return <form action={acao} className={styles.form}><label>Cadastro de fornecedor nesta loja<select name="pessoa_id" required defaultValue=""><option value="" disabled>Escolha o cadastro correto</option>{pessoas.map(pessoa => <option key={pessoa.id} value={pessoa.id}>{pessoa.nome} · #{pessoa.id}</option>)}</select></label><label><input name="confirmar" type="checkbox" required /> Confirmo que esta conta pertence ao fornecedor escolhido. O vínculo não poderá ser trocado por esta tela.</label><button disabled={pendente || !pessoas.length}>{pendente ? "Vinculando…" : "Vincular cadastro"}</button><Retorno estado={estado} /></form>;
}
export function MembroForm({ org, membro }: { org: number; membro: MembroOrganizacao }) {
  const [estado, acao, pendente] = useActionState(atualizarMembro.bind(null, org, membro.user_id), inicial);
  return <form action={acao} className={styles.form}><label>Perfil nesta loja<select name="perfil" defaultValue={membro.perfil}>{(membro.perfil === "fornecedor" ? [["fornecedor", "Fornecedor"]] : [["admin", "Administrador"], ["financeiro", "Financeiro"], ["operador", "Operador"], ["consulta", "Consulta"]]).map(([valor, nome]) => <option key={valor} value={valor}>{nome}</option>)}</select></label><label><input name="ativo" type="checkbox" defaultChecked={membro.ativo} /> Vínculo ativo nesta loja</label><label><input name="confirmar" type="checkbox" required /> Confirmo a alteração de acesso nesta loja</label><button disabled={pendente}>{pendente ? "Salvando…" : "Atualizar vínculo"}</button><Retorno estado={estado} /></form>;
}
export function ChaveFornecedorForm({ org, chave }: { org: number; chave?: ChaveFornecedor }) {
  const [estado, acao, pendente] = useActionState(salvarChave.bind(null, org, chave?.id ?? null), inicial);
  const valores = chave ?? { tipo: "aleatoria", chave: "", titular: "", banco: "", agencia: "", conta: "", tipo_conta: "", categoria: "fixa", validade: null, principal: false, ativo: true };
  return <form action={acao} className={styles.form}>
    <label>Tipo de chave<select name="tipo" defaultValue={valores.tipo}>{[["cpf", "CPF"], ["cnpj", "CNPJ"], ["email", "Email"], ["telefone", "Telefone"], ["aleatoria", "Aleatória"]].map(([valor, nome]) => <option key={valor} value={valor}>{nome}</option>)}</select></label>
    <label>Chave PIX<input name="chave" required maxLength={120} defaultValue={valores.chave} /></label>
    <label>Titular<input name="titular" maxLength={160} defaultValue={valores.titular} /></label>
    <label>Banco<input name="banco" maxLength={60} defaultValue={valores.banco} /></label>
    <label>Agência<input name="agencia" maxLength={30} defaultValue={valores.agencia} /></label>
    <label>Conta<input name="conta" maxLength={60} defaultValue={valores.conta} /></label>
    <label>Tipo de conta<input name="tipo_conta" maxLength={30} defaultValue={valores.tipo_conta} /></label>
    <label>Categoria<select name="categoria" defaultValue={valores.categoria}><option value="fixa">Fixa</option><option value="temporaria">Temporária</option></select></label>
    <label>Validade (obrigatória para temporária)<input name="validade" type="date" defaultValue={valores.validade ?? ""} /></label>
    <label><input name="principal" type="checkbox" defaultChecked={valores.principal} /> Chave principal</label>
    <label><input name="ativo" type="checkbox" defaultChecked={valores.ativo} /> Chave ativa</label>
    <button disabled={pendente}>{pendente ? "Salvando…" : chave ? "Salvar chave" : "Adicionar chave"}</button><Retorno estado={estado} />
  </form>;
}
export function RecebimentoFornecedorForm({ org, pagamento }: { org: number; pagamento: number }) {
  const [estado, acao, pendente] = useActionState(confirmarRecebimento.bind(null, org, pagamento), inicial);
  return <form action={acao} className={styles.form}><label>Referência do recebimento<input name="referencia" required minLength={3} maxLength={220} /></label><label>Observação<textarea name="observacao" maxLength={1000} /></label><label><input name="confirmar" type="checkbox" required /> Declaro que recebi o valor deste pagamento</label><button disabled={pendente}>{pendente ? "Registrando…" : "Declarar recebimento"}</button><Retorno estado={estado} /></form>;
}

export function AdicionarMembroForm({ org }: { org: number }) {
  const [estado, acao, pendente] = useActionState(adicionarMembro.bind(null, org), inicial);
  return <form action={acao} className={styles.form}><label>Email exato da conta existente<input name="email" type="email" required maxLength={160} /></label><label>Perfil nesta loja<select name="perfil" defaultValue="consulta">{[["admin", "Administrador"], ["financeiro", "Financeiro"], ["operador", "Operador"], ["consulta", "Consulta"]].map(([valor, nome]) => <option key={valor} value={valor}>{nome}</option>)}</select></label><button disabled={pendente}>{pendente ? "Adicionando…" : "Adicionar membro"}</button><Retorno estado={estado} /></form>;
}
