import Link from "next/link";
import LoginForm from "../../components/LoginForm";
import BrandMark from "../../components/BrandMark";
import { BRAND } from "../../lib/brand";

export default function LoginPage() {
  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <BrandMark size={56} />
          <div>
            <h1>{BRAND.name}</h1>
            <p className="login-tagline">Cobranças no caminho certo.</p>
          </div>
        </div>
        <p className="login-description">{BRAND.description}</p>
        <LoginForm />
        <p className="login-footnote">
          Ainda não tem conta?{" "}
          <Link href="/cadastro-loja">Crie a conta da sua loja</Link>
        </p>
        <p className="login-footnote">
          Da cobrança à conciliação, cada valor tem uma rota.
        </p>
      </div>
    </div>
  );
}
