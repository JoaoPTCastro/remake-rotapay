// Monograma R: uma rota contínua entre os pontos de origem e destino.
export default function BrandMark({ size = 40 }: { size?: number }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true" focusable="false" className="brand-mark">
      <rect width="64" height="64" rx="16" fill="var(--logo-bg)" />
      <path d="M20 46V18h14a10 10 0 0 1 0 20H20m12 0 13 8" fill="none" stroke="var(--logo-route)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="20" cy="46" r="4" fill="var(--logo-node)" />
      <circle cx="45" cy="46" r="4" fill="var(--logo-node)" />
    </svg>
  );
}
