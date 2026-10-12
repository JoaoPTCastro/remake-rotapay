import type { Metadata } from "next";
import Script from "next/script";
import { BRAND } from "../lib/brand";
import "./globals.css";

export const metadata: Metadata = {
  title: `${BRAND.name} — Cobranças e conciliação`,
  description: BRAND.description,
  applicationName: BRAND.name,
  icons: { shortcut: "/brand/rotapay-mark.svg" },
  openGraph: { title: BRAND.name, description: BRAND.description, locale: "pt_BR", type: "website" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body>
        <Script id="theme-init" strategy="beforeInteractive">
          {"try{var t=localStorage.getItem('theme');document.documentElement.dataset.theme=t==='dark'?'dark':'light';}catch(e){document.documentElement.dataset.theme='light';}"}
        </Script>
        {children}
      </body>
    </html>
  );
}
