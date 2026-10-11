import Link from "next/link";
import { notFound, unstable_rethrow } from "next/navigation";
import { apiGet, perfil } from "../../../../lib/api";
import { podeEditarPagamento } from "../../../../lib/pagamentos-types";
import type { CreditoOrigem } from "../../../../lib/creditos-types";
import { ReconhecimentoCredito } from "../CreditoForms";
import styles from "../Creditos.module.css";
export default async function ReconhecerCreditoPage({ searchParams }: { searchParams: Promise<{ acerto_id?: string }> }) {
  const filtros = await searchParams; const acertoId = filtros.acerto_id; if (!/^\d+$/.test(acertoId ?? "")) return <section><h1>Reconhecer crédito de conta</h1><p>Selecione um acerto efetivado para identificar a sobra e o pagamento de origem.</p><Link href="/acertos?status=efetivado">Consultar acertos efetivados</Link></section>;
  let origem: CreditoOrigem; let papel: string;
  try { [origem, papel] = await Promise.all([apiGet(`/creditos/recursos-origem?acerto_id=${acertoId}&offset=0&limit=50`) as Promise<CreditoOrigem>, perfil()]); }
  catch (erro) { unstable_rethrow(erro); if (erro instanceof Error && "status" in erro && erro.status === 404) notFound(); return <section><h1>Reconhecer crédito de conta</h1><p role="alert">Não foi possível consultar as sobras deste acerto. A origem precisa estar efetivada e ter saldo elegível.</p><Link href={`/acertos/${acertoId}`}>Conferir acerto de origem</Link></section>; }
  if (!podeEditarPagamento(papel)) return <section><h1>Reconhecer crédito de conta</h1><p>Esta operação está disponível para administração e financeiro.</p><Link href="/creditos">Consultar créditos</Link></section>;
  return <div className={styles.stack}><Link href={`/acertos/${origem.acerto_id}`}>← Voltar ao acerto de origem</Link><h1>Reconhecer sobra como crédito de conta</h1><ReconhecimentoCredito origem={origem} /></div>;
}
