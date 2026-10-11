import {ConteudoLinkVendedor} from "../ConteudoLinkVendedor";
export default async function LinkVendedor({params}: {params: Promise<{token: string}>}) {
  const {token} = await params;
  return ConteudoLinkVendedor({token});
}
