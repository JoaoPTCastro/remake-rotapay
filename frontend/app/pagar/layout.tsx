export default function PagarLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <header className="topbar"><strong>Pagamento PIX</strong></header>
      <main className="wrap">{children}</main>
    </>
  );
}
