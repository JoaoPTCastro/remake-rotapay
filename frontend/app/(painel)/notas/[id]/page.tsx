import Link from "next/link";
import { notFound, unstable_rethrow } from "next/navigation";
import { apiGet, perfil } from "../../../../lib/api";
import type { Nota, AbatimentoNota } from "../../../../lib/notas-types";
import { moedaNota, dataNota } from "../../../../lib/notas-types";
import { AbatimentoForm, ReversaoForm, AnexoForm, RemoverAnexo } from "../NotaForms";
import styles from "../Notas.module.css";
export default async function NotaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; if (!/^\d+$/.test(id)) notFound(); let nota: Nota; let papel: string;
  try { [nota, papel] = await Promise.all([apiGet(`/notas/${id}`) as Promise<Nota>, perfil()]); }
  catch (erro) { unstable_rethrow(erro); if (erro instanceof Error && "status" in erro && erro.status === 404) notFound(); return <section><h1>Nota</h1><p role="alert">Não foi possível carregar esta nota.</p><Link href={`/notas/${id}`}>Tentar novamente</Link></section>; }
  const editar = papel === "admin" || papel === "financeiro";
  return <Detalhe nota={nota} editar={editar} />;
}

function Detalhe({ nota, editar }: { nota: Nota; editar: boolean }) {
  return <div className={styles.stack}><Link href="/notas">← Voltar às notas</Link><header><h1>Nota #{nota.id} · {nota.numero_documento}</h1><p>{nota.pessoa_nome} · {nota.relacao === "cliente" ? "Venda · a receber" : "Compra · a pagar"}</p><Link href={`/notas?pessoa_id=${nota.pessoa_id}&relacao=${nota.relacao}`}>Ver notas deste titular</Link><p><Link href={`/extratos/${nota.pessoa_id}?relacao=${nota.relacao}`}>Ver extrato consolidado desta relação</Link></p><p><Link href="/pagamentos">Registrar e aplicar pagamento</Link></p></header><section className={styles.box}><div className={styles.stats}>{[["Original", nota.valor_original], ["Abatido registrado", nota.valor_abatido], ["Saldo da nota", nota.saldo_aberto]].map(([titulo, valor]) => <div key={titulo} className={styles.stat}><span>{titulo}</span><strong>{moedaNota(Number(valor))}</strong></div>)}</div><p>Situação: <strong>{nota.status}</strong>{atrasoNota(nota.em_atraso)}</p><p>Emissão: {dataNota(nota.data_emissao)} · Vencimento: {dataNota(nota.vencimento)}</p>{nota.prazo_dias_snapshot !== null && <p className={styles.muted}>Prazo registrado na criação: {nota.prazo_dias_snapshot} dias. Alterações futuras no cadastro não mudam o vencimento desta nota.</p>}<p>{descricaoNota(nota.descricao)}</p><p>Operação registrada: {nota.operacao_nome_snapshot || "Sem catálogo"} · Condição registrada: {nota.condicao_nome_snapshot || "Sem catálogo"}</p>{editar && nota.status !== "cancelado" && <ReversaoForm notaId={nota.id} />}</section>
    {editar && nota.saldo_aberto > 0 && nota.status !== "cancelado" && <AbatimentoForm notaId={nota.id} saldo={nota.saldo_aberto} />}<Historico nota={nota} editar={editar} /><Anexos nota={nota} editar={editar} />
  </div>;
}

function Historico({ nota, editar }: { nota: Nota; editar: boolean }) {
  return <section id="historico" className={styles.box}><h2>Histórico de abatimentos</h2>{!nota.abatimentos?.length ? <p>Nenhum abatimento registrado.</p> : <div className={styles.history}>{nota.abatimentos.map(a => <RegistroNota key={a.id} abatimento={a} nota={nota} editar={editar} />)}</div>}</section>;
}
function RegistroNota({ abatimento: a, nota, editar }: { abatimento: AbatimentoNota; nota: Nota; editar: boolean }) {
  return <article className={styles.entry}><strong>#{a.id} · {moedaNota(a.valor)} · {dataNota(a.data)}</strong><p>Origem: {origemAbatimento(a)}</p><p>Referência: {a.referencia}</p><p>{a.observacao}</p><p>{a.estornado ? "Estornado" : "Registrado"}{a.estorno?.motivo ? ` · ${a.estorno.motivo}` : ""}</p><AcaoAbatimento abatimento={a} nota={nota} editar={editar} /></article>;
}
function AcaoAbatimento({ abatimento: a, nota, editar }: { abatimento: AbatimentoNota; nota: Nota; editar: boolean }) {
  if (a.acerto_id) return <p><Link href={`/acertos/${a.acerto_id}`}>Ver acerto #{a.acerto_id}</Link>. O estorno destas aplicações deve ser feito no acerto inteiro.</p>;
  if (a.credito_id) return <p><Link href={`/creditos/${a.credito_id}#historico`}>Ver crédito de conta #{a.credito_id}</Link>. Estorne este uso no crédito; a nota não permite estorno isolado.</p>;
  if (a.credito_aplicacao_id || a.origem === "credito") return <p>Uso de crédito de conta. Consulte Créditos de conta para conferir e estornar.</p>;
  if (a.pagamento_aplicacao_id || a.origem === "pagamento") return a.pagamento_id ? <p><Link href={`/pagamentos/${a.pagamento_id}#historico`}>Ver pagamento e aplicação vinculada</Link>. O estorno desta aplicação deve ser feito no pagamento.</p> : <p>Abatimento vinculado a uma aplicação. Consulte Pagamentos para conferir e estornar.</p>;
  return editar && !a.estornado && nota.status !== "cancelado" ? <ReversaoForm notaId={nota.id} abatimentoId={a.id} /> : null;
}

function descricaoNota(descricao: string) { return descricao || "Sem descrição."; }
function atrasoNota(atraso: boolean) { return atraso ? " · Em atraso" : ""; }

function Anexos({ nota, editar }: { nota: Nota; editar: boolean }) { return <section className={styles.box}><h2>Anexos da nota</h2>{nota.anexos?.filter(a => a.ativo).length ? <ul>{nota.anexos.filter(a => a.ativo).map(a => <li key={a.id}><a href={`/api/notas/anexo?nota=${nota.id}&anexo=${a.id}`}>{a.nome_original}</a>{editar && nota.status !== "cancelado" && <RemoverAnexo notaId={nota.id} anexoId={a.id} />}</li>)}</ul> : <p>Nenhum anexo disponível.</p>}{editar && nota.status !== "cancelado" && <AnexoForm notaId={nota.id} />}</section>; }

function origemAbatimento(a: AbatimentoNota) { const nomes: Record<string, string> = { pagamento: "Aplicação de pagamento registrado", credito: "Uso de crédito de conta", registro_documental: "Abatimento externo documental" }; return nomes[a.origem] ?? "Abatimento registrado"; }
