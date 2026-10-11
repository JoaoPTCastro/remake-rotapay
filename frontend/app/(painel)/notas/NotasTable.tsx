import Link from "next/link";
import type { Nota } from "../../../lib/notas-types";
import { moedaNota, dataNota } from "../../../lib/notas-types";
import { rotulosColunas } from "../../../lib/configuracoes-types";
import type { PreferenciaTabela } from "../../../lib/configuracoes-types";
import styles from "./Notas.module.css";
export default function NotasTable({ notas, preferencia }: { notas: Nota[]; preferencia: PreferenciaTabela }) { const colunas = preferencia.colunas.filter(c => c.visivel); if (!notas.length) return <p className={styles.box}>Nenhuma nota cadastrada para estes filtros.</p>; return <div className={styles.table}><table><thead><tr>{colunas.map(c => <th key={c.campo}>{rotulosColunas[c.campo]}</th>)}</tr></thead><tbody>{notas.map(n => <tr key={n.id}>{colunas.map(c => <td key={c.campo} data-label={rotulosColunas[c.campo]}><Celula nota={n} campo={c.campo} /></td>)}</tr>)}</tbody></table></div>; }
function Celula({ nota: n, campo }: { nota: Nota; campo: string }) { if (campo === "numero_documento") return <Link href={`/notas/${n.id}`}>#{n.id} · {n.numero_documento}</Link>; if (campo === "relacao") return n.relacao === "cliente" ? "Venda · a receber" : "Compra · a pagar"; if (["valor_original", "valor_abatido", "saldo_aberto"].includes(campo)) return moedaNota(n[campo as "valor_original" | "valor_abatido" | "saldo_aberto"]); if (campo === "data_emissao" || campo === "vencimento") return dataNota(n[campo]); if (campo === "status") return <>{n.status}{n.em_atraso && <span className={styles.warning}> · Em atraso</span>}</>; return n.pessoa_nome; }
