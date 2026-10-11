import Link from "next/link";
import { unstable_rethrow } from "next/navigation";
import { apiGet } from "../../../lib/api";
import type { CadastroPessoa } from "../../../lib/cadastro-types";
import SelecionarExtrato from "./SelecionarExtrato";
import styles from "./Extratos.module.css";
export default async function ExtratosPage() {
  let pessoas: CadastroPessoa[];
  try { pessoas = await apiGet("/pessoas") as CadastroPessoa[]; }
  catch (erro) { unstable_rethrow(erro); return <section><h1>Extratos individuais</h1><p role="alert">Não foi possível carregar os cadastros.</p><Link href="/extratos">Tentar novamente</Link></section>; }
  return <div className={styles.stack}><header><h1>Extratos individuais</h1><p>Consulte notas, pagamentos, créditos e acertos de um titular em uma relação por vez.</p></header><p className={styles.notice}>Cliente e fornecedor mantêm contas independentes. Crédito de conta é saldo reconhecido de uma sobra, não nova entrada, receita ou dinheiro em caixa. Esta consulta reúne somente os módulos novos do RotaPay; os registros antigos continuam nas telas existentes.</p><SelecionarExtrato pessoas={pessoas} /></div>;
}
