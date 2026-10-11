import { apiGet } from "../../../lib/api";
import ExportButton from "../../../components/ExportButton";

type SP = { [k: string]: string | string[] | undefined };
type Linha = {
  id: number; acao: string; entidade: string; entidade_id: number | null;
  usuario_id: number | null; ip: string; created_at: string;
};

function str(v: string | string[] | undefined) {
  return typeof v === "string" ? v : "";
}

export default async function Historico({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  const filtros = { acao: str(sp.acao), entidade: str(sp.entidade), usuario_id: str(sp.usuario_id) };
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(filtros)) {
    if (v) q.set(k, v);
  }
  const rows = (await apiGet(`/auditoria?${q.toString()}`).catch(() => [])) as Linha[];
  return (
    <div>
      <h1>Histórico</h1>
      <p className="muted">Quem fez o quê, quando e de onde — filtre por ação, entidade ou usuário.</p>
      <form method="get" className="grid">
        <input name="acao" placeholder="Buscar ação (ex.: login, conciliação…)" defaultValue={filtros.acao} aria-label="Buscar por ação" />
        <input name="entidade" placeholder="Entidade (ex.: movimentacoes)" defaultValue={filtros.entidade} aria-label="Filtrar por entidade" />
        <input name="usuario_id" type="number" min="1" placeholder="ID do usuário" defaultValue={filtros.usuario_id} aria-label="Filtrar por usuário" />
        <button type="submit">Filtrar</button>
      </form>
      <p><ExportButton file="auditoria.csv" label="Exportar CSV (respeita filtros)" /></p>
      <div className="tablewrap">
        <table>
          <thead><tr><th>ID</th><th>Ação</th><th>Entidade</th><th>Registro</th><th>Usuário</th><th>IP</th><th>Quando</th></tr></thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id}>
                <td data-label="ID">#{a.id}</td><td data-label="Ação">{a.acao}</td><td data-label="Entidade">{a.entidade}</td>
                <td data-label="Registro">{a.entidade_id ?? "—"}</td><td data-label="Usuário">{a.usuario_id ?? "—"}</td>
                <td data-label="IP">{a.ip || "—"}</td><td data-label="Quando">{a.created_at}</td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={7} className="muted">Sem acesso ou sem registros.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
