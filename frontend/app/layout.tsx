import type { Metadata } from "next";
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
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "try{var t=localStorage.getItem('theme');document.documentElement.dataset.theme=t==='dark'?'dark':'light';}catch(e){document.documentElement.dataset.theme='light';}",
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
