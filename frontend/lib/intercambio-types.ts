export type TipoImportacao = "cadastros" | "notas";
export type ResumoImportacao = { total: number; novos: number; ignorados: number; erros: number };
export type PreviaImportacao = { tipo: TipoImportacao; hash_conteudo: string; token_previa: string; pode_importar: boolean; resumo: ResumoImportacao; linhas: { linha: number; status: "novo" | "ignorado" | "erro"; erros: string[]; dados: Record<string, unknown> }[] };
export type ConfirmacaoImportacao = { importacao_id: number; resumo: ResumoImportacao; ids_criados: number[]; ids_ignorados: number[]; repetida: boolean };
export type ResultadoIntercambio<T> = { ok: true; dados: T } | { ok: false; mensagem: string };
