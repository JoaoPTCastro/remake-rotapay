import Shell from "../../components/Shell";
import { apiGet, usuarioAtual } from "../../lib/api";

export default async function PainelLayout({ children }: { children: React.ReactNode }) {
  const me = await usuarioAtual();
  const perfil = me.perfil;
  const loja = (await apiGet("/loja").catch(() => null)) as { nome?: string } | null;
  return <Shell perfil={perfil} organizacaoNome={me.organizacao_nome} lojaNome={loja?.nome || undefined}>{children}</Shell>;
}
