export type RelacaoNota = "cliente" | "fornecedor";
export type AbatimentoNota = { id: number; credito_aplicacao_id: number | null; credito_id: number | null; acerto_id: number | null; origem: string; pagamento_aplicacao_id: number | null; pagamento_id: number | null; valor: number; data: string; referencia: string; observacao: string; estornado: boolean; estorno: { id: number; motivo: string; created_at: string } | null };
export type AnexoNota = { id: number; nome_original: string; ativo: boolean };
export type Nota = { condicao_id?: number | null; condicao_nome_snapshot?: string | null; operacao_id?: number | null; operacao_nome_snapshot?: string | null; id: number; pessoa_id: number; pessoa_nome: string; relacao: RelacaoNota; operacao: string; numero_documento: string; valor_original: number; valor_abatido: number; saldo_aberto: number; status: string; em_atraso: boolean; data_emissao: string; vencimento: string | null; prazo_dias_snapshot: number | null; descricao: string; abatimentos?: AbatimentoNota[]; anexos?: AnexoNota[] };
export type ExtratoNotas = { pessoa_id: number; pessoa_nome: string; relacao: RelacaoNota; origem: string; resumo: { valor_original: number; valor_abatido: number; saldo_aberto: number; saldo_vencido: number }; notas: Nota[] };
export type NotaResultado = { ok: boolean; mensagem: string; id?: number };
export const moedaNota = (v: number) => Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
export const dataNota = (v: string | null) => v ? v.slice(0, 10).split("-").reverse().join("/") : "Sem vencimento";
