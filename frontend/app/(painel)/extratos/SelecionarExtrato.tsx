"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import type { CadastroPessoa } from "../../../lib/cadastro-types";
import type { RelacaoNota } from "../../../lib/notas-types";
import styles from "./Extratos.module.css";
function corresponde(pessoa: CadastroPessoa, relacao: RelacaoNota, termo: string) { const papel = relacao === "cliente" ? "representante" : "fornecedor"; const tipo = pessoa.tipo === papel || pessoa.tipo === relacao || pessoa.tipo === "ambos"; return tipo && `${pessoa.id} ${pessoa.nome} ${pessoa.apelido}`.toLocaleLowerCase("pt-BR").includes(termo.trim().toLocaleLowerCase("pt-BR")); }
export default function SelecionarExtrato({ pessoas }: { pessoas: CadastroPessoa[] }) {
  const router = useRouter(); const [relacao, setRelacao] = useState<RelacaoNota>("cliente"); const [termo, setTermo] = useState(""); const [pessoaId, setPessoaId] = useState(""); const elegiveis = pessoas.filter(p => corresponde(p, relacao, termo));
  return <form className={`${styles.box} ${styles.form}`} onSubmit={e => { e.preventDefault(); router.push(`/extratos/${pessoaId}?relacao=${relacao}`); }}><label>Relação<select value={relacao} onChange={e => { setRelacao(e.target.value as RelacaoNota); setPessoaId(""); }}><option value="cliente">Cliente · a receber</option><option value="fornecedor">Fornecedor · a pagar</option></select></label><label>Buscar titular por nome ou ID<input type="search" value={termo} onChange={e => { setTermo(e.target.value); setPessoaId(""); }} /></label><label className={styles.wide}>Titular<select value={pessoaId} onChange={e => setPessoaId(e.target.value)} required><option value="">Selecione o cadastro</option>{elegiveis.map(p => <option key={p.id} value={p.id}>{p.nome} · #{p.id}{!p.ativo ? " (inativo)" : ""}</option>)}</select></label><div className={styles.wide}><button disabled={!pessoaId}>Consultar extrato individual</button>{!elegiveis.length && <p>Nenhum cadastro corresponde a esta relação e busca.</p>}</div></form>;
}
