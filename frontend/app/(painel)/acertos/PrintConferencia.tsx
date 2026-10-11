"use client";
import styles from "./Acertos.module.css";
export default function PrintConferencia() { return <button type="button" className={styles.noPrint} onClick={() => window.print()}>Imprimir resumo de conferência</button>; }
