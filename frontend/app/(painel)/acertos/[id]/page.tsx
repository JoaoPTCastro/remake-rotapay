import Link from "next/link";
import { notFound, unstable_rethrow } from "next/navigation";
import { apiGet, perfil } from "../../../../lib/api";
import type { Acerto } from "../../../../lib/acertos-types";
import { podeEditarPagamento } from "../../../../lib/pagamentos-types";
import { AcertoOperacoes } from "../AcertoActions";
import { AcertoCabecalho, AcertoResumo, AcertoPares, AcertoHistorico, AcertoEtapas } from "../AcertoSummary";
import styles from "../Acertos.module.css";
export default async function AcertoPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; if (!/^\d+$/.test(id)) notFound(); let acerto: Acerto; let papel: string;
  try { [acerto, papel] = await Promise.all([apiGet(`/acertos/${id}`) as Promise<Acerto>, perfil()]); }
  catch (erro) { unstable_rethrow(erro); if (erro instanceof Error && "status" in erro && erro.status === 404) notFound(); return <section><h1>Acerto</h1><p role="alert">Não foi possível carregar este acerto.</p><Link href={`/acertos/${id}`}>Tentar novamente</Link></section>; }
  return <div className={styles.stack}><Link href="/acertos">← Voltar aos acertos</Link><AcertoCabecalho acerto={acerto} /><AcertoEtapas acerto={acerto} /><AcertoResumo acerto={acerto} /><AcertoPares itens={acerto.itens ?? []} /><p className={styles.notice}>Esta relação é independente da outra conta do mesmo pagamento. Os itens do rascunho são fixos. Se algum recurso mudar desde a prévia, cancele este rascunho e crie outro; para fornecedor, registre novo envio e nova concordância externa.</p>{podeEditarPagamento(papel) ? <AcertoOperacoes acerto={acerto} /> : <p><Link href={`/acertos/${acerto.id}/conferencia`}>Abrir resumo local para conferência</Link></p>}<CreditosAcerto acerto={acerto} editar={podeEditarPagamento(papel)} /><AcertoHistorico acerto={acerto} /></div>;
}

function CreditosAcerto({ acerto, editar }: { acerto: Acerto; editar: boolean }) { return <section className={styles.box}><h2>Créditos de conta da sobra</h2><p>O reconhecimento é explícito e vinculado a um pagamento deste acerto. Não cria dinheiro novo. Créditos não revertidos bloqueiam o estorno do acerto, mesmo quando integralmente usados.</p>{editar && acerto.status === "efetivado" && <Link href={`/creditos/novo?acerto_id=${acerto.id}`}>Reconhecer crédito de conta da sobra</Link>}{acerto.creditos?.length ? <ul>{acerto.creditos.map(c => <li key={c.id}><Link href={`/creditos/${c.id}`}>{c.codigo}</Link> · pagamento #{c.pagamento_id} · {c.status === "revertido" ? "Reconhecimento revertido" : "Reconhecimento não revertido"}</li>)}</ul> : <p>Nenhum crédito reconhecido a partir deste acerto.</p>}</section>; }
