import Link from "next/link";
import { perfil } from "../../../lib/api";
import ImportarCSV from "./ImportarCSV";
import ExportarCSV from "./ExportarCSV";
import styles from "./Intercambio.module.css";
export default async function Intercambio() { const podeImportar = ["admin", "financeiro"].includes(await perfil()); return <div className={styles.stack}><header><h1>Intercâmbio de dados</h1><p>Importação conferida e exportação privada de dados do RotaPay.</p></header><p className={styles.notice}>Cadastros importados exigem CPF/CNPJ com 11 ou 14 dígitos. Registros existentes são preservados: conflitos não sobrescrevem dados. Notas importadas representam novas obrigações abertas; saldos históricos, pagamentos, créditos e quitações não são inferidos.</p><div className={styles.actions}><Link href="/cadastro">Ver cadastros</Link><Link href="/notas">Ver notas</Link></div>{podeImportar ? <ImportarCSV /> : <p className={styles.box}>Seu perfil permite consultar modelos e exportações. Importar exige administrador ou financeiro.</p>}<ExportarCSV /></div>; }
