export default function ExportButton({ file, label }: { file: string; label: string }) {
  const query = typeof window !== "undefined" ? window.location.search.replace(/^\?/, "") : "";
  return (
    <a className="btn-secondary" href={`/api/export?file=${file}${query ? `&${query}` : ""}`} download>
      {label}
    </a>
  );
}
