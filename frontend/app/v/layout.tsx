export default function VLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <header className="topbar"><strong>Pagamento PIX do vendedor</strong></header>
      <main className="wrap">{children}</main>
    </>
  );
}
