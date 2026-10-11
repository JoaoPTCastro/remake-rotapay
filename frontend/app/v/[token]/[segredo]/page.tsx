import {notFound} from "next/navigation";
import {ConteudoLinkVendedor} from "../../ConteudoLinkVendedor";
export default async function LinkDaLoja({params}: {params: Promise<{token: string; segredo: string}>}) {
  const {token: loja, segredo} = await params;
  if (!/^[1-9]\d*$/.test(loja)) notFound();
  return ConteudoLinkVendedor({token: segredo, organizacaoId: Number(loja)});
}
