import type {ExtratoPublicoDados,NotaPublica,PagamentoPublico,PaginaPublica} from "./compartilhamentos-types";
function obj(v:unknown):Record<string,unknown>{if(!v || typeof v!=="object" || Array.isArray(v))throw new Error("Resposta inválida");return v as Record<string,unknown>;}
function texto(v:unknown):string{if(typeof v!=="string" || v.length>160)throw new Error("Resposta inválida");return v;}
function dataHora(v:unknown):string{const s=texto(v);if(Number.isNaN(new Date(s).getTime()) || !/(?:Z|[+-]\d{2}:\d{2})$/.test(s))throw new Error("Resposta inválida");return s;}
function numero(v:unknown):number{if(typeof v!=="number" || !Number.isFinite(v) || v<0)throw new Error("Resposta inválida");return v;}
function inteiro(v:unknown):number{const n=numero(v);if(!Number.isSafeInteger(n))throw new Error("Resposta inválida");return n;}
function booleano(v:unknown):boolean{if(typeof v!=="boolean")throw new Error("Resposta inválida");return v;}
function pagina<T>(v:unknown,converter:(r:Record<string,unknown>)=>T):PaginaPublica<T>{const p=obj(v);if(!Array.isArray(p.itens) || p.itens.length>100)throw new Error("Resposta inválida");const limit=inteiro(p.limit);if(limit<1 || limit>100)throw new Error("Resposta inválida");return{itens:p.itens.map(x=>converter(obj(x))),total:inteiro(p.total),limit,offset:inteiro(p.offset),tem_mais:booleano(p.tem_mais)};}
export function validarExtratoPublico(v:unknown):ExtratoPublicoDados{const r=obj(v);if(!["cliente","fornecedor"].includes(String(r.relacao)) || r.escopo!=="compartilhado_restrito")throw new Error("Resposta inválida");const t=obj(r.totais_globais),n=obj(t.notas),p=obj(t.pagamentos);return{relacao:r.relacao as "cliente"|"fornecedor",escopo:"compartilhado_restrito",expira_em:dataHora(r.expira_em),totais_globais:{notas:{valor_original:numero(n.valor_original),valor_abatido:numero(n.valor_abatido),saldo_aberto:numero(n.saldo_aberto),saldo_vencido:numero(n.saldo_vencido)},pagamentos:{valor_elegivel:numero(p.valor_elegivel),valor_aplicado:numero(p.valor_aplicado),destinado_credito:numero(p.destinado_credito),saldo_disponivel:numero(p.saldo_disponivel)}},notas:pagina<NotaPublica>(r.notas,x=>({numero_documento:texto(x.numero_documento),data_emissao:texto(x.data_emissao),vencimento:x.vencimento===null ? null : texto(x.vencimento),valor_original:numero(x.valor_original),valor_abatido:numero(x.valor_abatido),saldo_aberto:numero(x.saldo_aberto),status:texto(x.status),em_atraso:booleano(x.em_atraso)})),pagamentos:pagina<PagamentoPublico>(r.pagamentos,x=>({data:texto(x.data),forma:texto(x.forma),valor:numero(x.valor),valor_aplicado:numero(x.valor_aplicado),destinado_credito:numero(x.destinado_credito),saldo_disponivel:numero(x.saldo_disponivel),status:texto(x.status)}))};}

export function validarLojaPublica(valor: string | null): number | null {
  if (valor === null) return 1;
  if (!/^[1-9]\d*$/.test(valor)) return null;
  const id = Number(valor);
  return Number.isSafeInteger(id) ? id : null;
}
