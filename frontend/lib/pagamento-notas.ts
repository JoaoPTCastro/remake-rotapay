import { apiGet } from "./api";
import type { Nota, RelacaoNota } from "./notas-types";
import type { PaginaNotasPagamento } from "./pagamentos-types";

// Cada situação tem sua própria janela: nenhuma nota quitada ocupa uma vaga.
// Avançar 50 em ambas as consultas permite percorrer todos os documentos.
export async function notasElegiveis(pessoaId: number | null, relacao: RelacaoNota, offset = 0): Promise<PaginaNotasPagamento> {
  if (!pessoaId) return { notas: [], offset, mais: false };
  const base = `/notas?pessoa_id=${pessoaId}&relacao=${relacao}&limit=51&offset=${offset}`;
  const [abertas, parciais] = await Promise.all([apiGet(`${base}&status=aberto`) as Promise<Nota[]>, apiGet(`${base}&status=parcial`) as Promise<Nota[]>]);
  const notas = [...abertas.slice(0, 50), ...parciais.slice(0, 50)].filter(n => n.saldo_aberto > 0).sort((a, b) => b.id - a.id);
  return { notas, offset, mais: abertas.length > 50 || parciais.length > 50 };
}
