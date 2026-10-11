import type { Metadata } from "next";
import SalesPage from "./SalesPage";
export const metadata: Metadata = {
  title: "RotaPay — Do link PIX ao acerto com o fornecedor",
  description:
    "O RotaPay organiza as cobranças, os comprovantes e os pagamentos aos fornecedores. Conheça o caminho do link PIX ao acerto.",
  openGraph: {
    title: "RotaPay — Seu cliente pagou. Continue no controle.",
    description: "O RotaPay organiza as cobranças, os comprovantes e os pagamentos aos fornecedores.",
    url: "https://rotapay.site/",
    siteName: "RotaPay",
    locale: "pt_BR",
    type: "website",
    images: [{ url: "https://rotapay.site/brand/rotapay-compartilhar-v3.jpg", width: 1200, height: 630, alt: "RotaPay: seu cliente pagou. Continue no controle." }],
  },
  twitter: {
    card: "summary_large_image",
    title: "RotaPay — Seu cliente pagou. Continue no controle.",
    description: "Cobranças, comprovantes e pagamentos aos fornecedores. Tudo organizado.",
    images: ["https://rotapay.site/brand/rotapay-compartilhar-v3.jpg"],
  },
  alternates: { canonical: "https://rotapay.site/" },
};
export default function Page() {
  return <SalesPage />;
}
