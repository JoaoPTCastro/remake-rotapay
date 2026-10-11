import Link from "next/link";
import type { Pagamento } from "../../../lib/pagamentos-types";
import { tipoPagamento } from "../../../lib/pagamentos-types";
import { moedaNota, dataNota } from "../../../lib/notas-types";
import { rotulosColunas } from "../../../lib/configuracoes-types";
import type { PreferenciaTabela } from "../../../lib/configuracoes-types";
import styles from "./Pagamentos.module.css";
export default function PagamentosTable({ pagamentos, preferencia }: { pagamentos: Pagamento[]; preferencia: PreferenciaTabela }) { const colunas = preferencia.colunas.filter(c => c.visivel); if (!pagamentos.length) return <p className={styles.box}>Nenhum pagamento registrado para estes filtros.</p>; return <div className={styles.table}><table><thead><tr>{colunas.map(c => <th key={c.campo}>{rotulosColunas[c.campo]}</th>)}</tr></thead><tbody>{pagamentos.map(p => <tr key={p.id}>{colunas.map(c => <td key={c.campo} data-label={rotulosColunas[c.campo]}><Celula pagamento={p} campo={c.campo} /></td>)}</tr>)}</tbody></table></div>; }
function Celula({ pagamento: p, campo }: { pagamento: Pagamento; campo: string }) { if (campo === "codigo") return <><Link href={`/pagamentos/${p.id}`}>{p.codigo}</Link><br /><small>{p.referencia_externa}</small></>; if (campo === "tipo") return tipoPagamento(p.tipo); if (campo === "valor") return moedaNota(p.valor); if (campo === "data") return dataNota(p.data); if (campo === "cancelado") return p.cancelado ? "Cancelado" : "Registrado"; if (campo === "forma") return <>{p.forma}{p.forma_nome_snapshot && <small> · {p.forma_nome_snapshot}</small>}</>; return campo === "cliente_nome" ? p.cliente_nome ?? "—" : p.fornecedor_nome ?? "—"; }
