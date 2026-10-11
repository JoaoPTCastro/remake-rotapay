import Link from "next/link";
import BrandMark from "../../components/BrandMark";
import CadastroConvite from "./CadastroConvite";

export default function ConvitePage() {
  return <main className="wrap" style={{ maxWidth: 600, margin: "48px auto" }}>
    <BrandMark size={48} /><h1>Seu acesso como fornecedor</h1>
    <p>Recebeu um convite de uma loja? Informe o código para criar sua conta e registrar seu vínculo.</p>
    <CadastroConvite />
    <p>Já possui conta? <Link href="/login">Entre</Link> e aceite o convite em Organizações e fornecedores.</p>
  </main>;
}
