import Link from "next/link";
import { unstable_rethrow } from "next/navigation";
import { apiGet, perfil } from "../../../../lib/api";
import { podeEditarPagamento } from "../../../../lib/pagamentos-types";
import type { CadastroPessoa } from "../../../../lib/cadastro-types";
import NovoAcerto from "../NovoAcerto";
export default async function NovoAcertoPage() {
  let pessoas: CadastroPessoa[]; let papel: string;
  try { [pessoas, papel] = await Promise.all([apiGet("/pessoas") as Promise<CadastroPessoa[]>, perfil()]); }
  catch (erro) { unstable_rethrow(erro); return <section><h1>Criar acerto</h1><p role="alert">Não foi possível carregar os cadastros.</p><Link href="/acertos/novo">Tentar novamente</Link></section>; }
  if (!podeEditarPagamento(papel)) return <section><h1>Criar acerto</h1><p>Seu perfil permite consultar acertos. A criação está disponível para administração e financeiro.</p><Link href="/acertos">Consultar acertos</Link></section>;
  return <NovoAcerto pessoas={pessoas} />;
}
