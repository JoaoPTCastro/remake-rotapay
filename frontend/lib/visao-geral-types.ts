import type { ExtratoGlobal } from "./extratos-types";
import type { RelacaoNota } from "./notas-types";
export type TotaisContaGlobal = ExtratoGlobal["totais_globais"];
export type CoberturaGlobal = { legado_integrado: false; consumo_integrado_habilitado: false };
export type ResumoVisaoGlobal = { escopo: "dominio_novo"; cobertura: CoberturaGlobal; contas: { cliente: TotaisContaGlobal; fornecedor: TotaisContaGlobal }; fluxo_caixa: { entradas_cliente_loja: number; saidas_repasse_fornecedor: number; saldo_liquido: number; pagamentos_diretos_cliente_fornecedor: number; quantidade_entradas: number; quantidade_saidas: number; quantidade_diretos: number } };
export type PosicaoGlobal = { pessoa: ExtratoGlobal["pessoa"]; relacao: RelacaoNota; totais_globais: TotaisContaGlobal };
export type NotaFilaGlobal = { id: number; pessoa_id: number; pessoa_nome: string; relacao: RelacaoNota; numero_documento: string; data_emissao: string; vencimento: string | null; valor_original: number; valor_abatido: number; saldo_aberto: number; em_atraso: boolean; url: string };
export type PaginaGlobal<T> = { itens: T[]; total_filtrado: number; limit: number; offset: number; tem_mais: boolean; filtros: { relacao: RelacaoNota; pessoa_id?: number | null; q?: string | null }; escopo: "dominio_novo"; cobertura: CoberturaGlobal };
export type ParamsVisaoGlobal = { escopo?: string; relacao?: string; pessoa_id?: string; q?: string; posicoes_offset?: string; fila_offset?: string };
export type FiltrosVisaoGlobal = { relacao: RelacaoNota; pessoa_id: string; q: string; posicoes_offset: number; fila_offset: number };
function pessoaValida(pessoa: string) { return pessoa === "" || (/^[1-9]\d*$/.test(pessoa) && Number.isSafeInteger(Number(pessoa))); }
export function filtrosVisaoGlobal(p: ParamsVisaoGlobal): FiltrosVisaoGlobal | null {
  if (Object.values(p).some(valor => typeof valor !== "string" && valor !== undefined)) return null;
  const relacao = p.relacao ?? "cliente";
  if (relacao !== "cliente" && relacao !== "fornecedor") return null;
  const pessoa = (p.pessoa_id ?? "").trim(), q = (p.q ?? "").trim();
  if (q.length > 120 || !pessoaValida(pessoa)) return null;
  function offset(s?: string): number | null { if (s !== undefined && !/^\d+$/.test(s)) return null; const n = Number(s ?? 0); return Number.isInteger(n) && n >= 0 && n <= 100000 ? n : null; }
  const posicoes = offset(p.posicoes_offset), fila = offset(p.fila_offset);
  if (posicoes === null || fila === null) return null;
  return { relacao, pessoa_id: pessoa, q, posicoes_offset: posicoes, fila_offset: fila };
}
export function consultaVisaoGlobal(f: FiltrosVisaoGlobal): URLSearchParams {
  const qs = new URLSearchParams({ relacao: f.relacao });
  if (f.pessoa_id) qs.set("pessoa_id", f.pessoa_id);
  if (f.q) qs.set("q", f.q);
  return qs;
}
