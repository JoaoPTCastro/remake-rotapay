export type Compartilhamento = {id:number;created_by:number;criado_por_nome:string|null;relacao:"cliente"|"fornecedor";destinatario:string;created_at:string;expira_em:string;revogado:boolean;revogado_em:string|null;motivo_revogacao:string|null;status:string};
export type PaginaCompartilhamentos = {itens:Compartilhamento[];total:number;limit:number;offset:number;tem_mais:boolean};
export type EstadoCompartilhamento = {ok:boolean;mensagem:string;token?:string;organizacao_id?:number};
export type NotaPublica={numero_documento:string;data_emissao:string;vencimento:string|null;valor_original:number;valor_abatido:number;saldo_aberto:number;status:string;em_atraso:boolean};
export type PagamentoPublico={data:string;forma:string;valor:number;valor_aplicado:number;destinado_credito:number;saldo_disponivel:number;status:string};
export type PaginaPublica<T>={itens:T[];total:number;limit:number;offset:number;tem_mais:boolean};
export type ExtratoPublicoDados={relacao:"cliente"|"fornecedor";escopo:"compartilhado_restrito";expira_em:string;totais_globais:{notas:{valor_original:number;valor_abatido:number;saldo_aberto:number;saldo_vencido:number};pagamentos:{valor_elegivel:number;valor_aplicado:number;destinado_credito:number;saldo_disponivel:number}};notas:PaginaPublica<NotaPublica>;pagamentos:PaginaPublica<PagamentoPublico>};
