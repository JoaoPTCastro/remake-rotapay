import Link from "next/link";
import { unstable_rethrow } from "next/navigation";
import { apiGet, perfil } from "../../../lib/api";
import type { CadastroPessoa } from "../../../lib/cadastro-types";
import type { Pagamento } from "../../../lib/pagamentos-types";
import { podeEditarPagamento } from "../../../lib/pagamentos-types";

import { NovoPagamento } from "./PagamentoForms";
import PagamentosTable from "./PagamentosTable";
import PreferenciasTabela from "../../../components/PreferenciasTabela";
import { carregarCatalogos, carregarPreferencia, aplicarOrdenacao } from "../../../lib/configuracoes-api";
import { filtrosAplicados, filtrosParaSalvar } from "../../../lib/tabela-filtros";
import type { Catalogos, PreferenciaTabela } from "../../../lib/configuracoes-types";
import AtualizarPagamentos from "./AtualizarPagamentos";
import styles from "./Pagamentos.module.css";
type Params = { cliente_id?: string; fornecedor_id?: string; tipo?: string; forma?: string; offset?: string; origem?: string; filtrar?: string; valor_min?: string; valor_max?: string; origem_registro?: string };
function parametros(filtros: Params) {
  const qs = new URLSearchParams({ filtrar: "1" });
  for (const campo of ["cliente_id", "fornecedor_id"] as const) if (/^\d+$/.test(filtros[campo] ?? "")) qs.set(campo, filtros[campo] as string);
  if (["cliente_loja", "cliente_fornecedor", "repasse_fornecedor"].includes(filtros.tipo ?? "")) qs.set("tipo", filtros.tipo as string);
  if (["PIX", "dinheiro"].includes(filtros.forma ?? "")) qs.set("forma", filtros.forma as string);
  aplicarFiltrosRastreabilidade(qs, filtros);
  const offset = Math.max(0, Number.parseInt(filtros.offset ?? "0", 10) || 0); qs.set("offset", String(offset)); qs.set("limit", "100");
  return { qs, offset };
}
export default async function PagamentosPage({ searchParams }: { searchParams: Promise<Params> }) {
  let preferencia: PreferenciaTabela; try { preferencia = await carregarPreferencia("pagamentos"); } catch (erro) { unstable_rethrow(erro); return <p role="alert">Não foi possível carregar suas preferências. Recarregue a página.</p>; } const filtros = filtrosAplicados("pagamentos", await searchParams, preferencia) as Params; const { qs, offset } = parametros(filtros); aplicarOrdenacao(qs, preferencia);
  let catalogos: Catalogos; let pagamentos: Pagamento[]; let pessoas: CadastroPessoa[]; let papel: string; let origem: Pagamento | null = null;
  try { [catalogos, pagamentos, pessoas, papel] = await Promise.all([carregarCatalogos(true),apiGet(`/pagamentos?${qs}`) as Promise<Pagamento[]>, apiGet("/pessoas") as Promise<CadastroPessoa[]>, perfil()]); if (/^\d+$/.test(filtros.origem ?? "")) origem = await apiGet(`/pagamentos/${filtros.origem}`) as Pagamento; }
  catch (erro) { unstable_rethrow(erro); return <section><h1>Pagamentos</h1><p role="alert">Não foi possível carregar os pagamentos. Confira sua conexão e tente novamente.</p><Link href="/pagamentos">Tentar novamente</Link></section>; }
  const pagina = (novo: number) => { const params = new URLSearchParams(qs); params.set("offset", String(novo)); return `/pagamentos?${params}`; };
  return <div className={styles.stack}><header><h1>Pagamentos e aplicações</h1><AtualizarPagamentos /><p className={styles.muted}>Registre cada pagamento uma vez e aplique seu valor nas notas correspondentes.</p></header><p className={styles.notice}>Um PIX direto ao fornecedor pode participar das contas do cliente e do fornecedor, mas continua sendo um único pagamento. Os saldos de cada relação não representam dois recebimentos e não são somados como caixa. PIX antigos e abatimentos externos não são importados automaticamente.</p><Filtros filtros={filtros} pessoas={pessoas} />{podeEditarPagamento(papel) && <Criacao pessoas={pessoas} origem={origem} catalogos={catalogos} />}<section><div className={styles.head}><h2>Pagamentos registrados no RotaPay</h2><span>{pagamentos.length} nesta página</span></div><PreferenciasTabela key={JSON.stringify(preferencia)} tela="pagamentos" preferencia={preferencia} filtros={filtrosParaSalvar("pagamentos", filtros)} /><p className={styles.muted}>Ordenação de todos os resultados antes da paginação.</p><PagamentosTable pagamentos={pagamentos} preferencia={preferencia} /><nav className={`${styles.actions} ${styles.controls}`} aria-label="Páginas dos pagamentos">{offset > 0 && <Link href={pagina(Math.max(0, offset - 100))}>Página anterior</Link>}{pagamentos.length === 100 && <Link href={pagina(offset + 100)}>Próxima página</Link>}</nav></section></div>;
}
function Criacao({ pessoas, origem, catalogos }: { pessoas: CadastroPessoa[]; origem: Pagamento | null; catalogos: Catalogos }) {
  if (origem && (origem.tipo !== "cliente_loja" || origem.cancelado || origem.saldo_para_repasse <= 0)) return <p role="alert" className={styles.box}>Este pagamento não possui saldo disponível para repasse. <Link href={`/pagamentos/${origem.id}`}>Conferir origem</Link></p>;
  return <NovoPagamento pessoas={pessoas} origem={origem} catalogos={catalogos} />;
}
function Filtros({ filtros, pessoas }: { filtros: Params; pessoas: CadastroPessoa[] }) {
  return <form className={`${styles.box} ${styles.form}`} method="get"><input type="hidden" name="filtrar" value="1" /><PessoaFiltro pessoas={pessoas} campo="cliente_id" valor={filtros.cliente_id} label="Cliente" /><PessoaFiltro pessoas={pessoas} campo="fornecedor_id" valor={filtros.fornecedor_id} label="Fornecedor" /><label>Tipo<select name="tipo" defaultValue={filtros.tipo ?? ""}><option value="">Todos os tipos</option><option value="cliente_loja">Cliente → loja</option><option value="cliente_fornecedor">Cliente → fornecedor</option><option value="repasse_fornecedor">Repasse ao fornecedor</option></select></label><label>Forma<select name="forma" defaultValue={filtros.forma ?? ""}><option value="">Todas as formas</option><option value="PIX">PIX</option><option value="dinheiro">Dinheiro</option></select></label><label>Valor mínimo (R$)<input name="valor_min" type="number" min="0" max="9999999999.99" step="0.01" defaultValue={filtros.valor_min ?? ""} /></label><label>Valor máximo (R$)<input name="valor_max" type="number" min="0" max="9999999999.99" step="0.01" defaultValue={filtros.valor_max ?? ""} /></label><label>Origem do registro<select name="origem_registro" defaultValue={filtros.origem_registro ?? ""}><option value="">Todas</option><option value="manual">Manual</option><option value="nao_informada">Não informada</option></select></label><div className={`${styles.wide} ${styles.actions}`}><button>Filtrar pagamentos</button><Link href="/pagamentos?filtrar=1">Limpar filtros</Link></div></form>;
}
function PessoaFiltro({ pessoas, campo, valor, label }: { pessoas: CadastroPessoa[]; campo: string; valor: string | undefined; label: string }) { return <label>{label}<select name={campo} defaultValue={valor ?? ""}><option value="">Todos os cadastros</option>{pessoas.map(p => <option key={p.id} value={p.id}>{p.nome}</option>)}</select></label>; }

function aplicarFiltrosRastreabilidade(qs: URLSearchParams, filtros: Params) {
  for (const campo of ["valor_min", "valor_max"] as const) if (filtros[campo] !== undefined && filtros[campo] !== "") qs.set(campo, filtros[campo] as string);
  if (["manual", "nao_informada"].includes(filtros.origem_registro ?? "")) qs.set("origem_registro", filtros.origem_registro as string);
}
