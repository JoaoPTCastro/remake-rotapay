import { apiGet, apiPost } from "../../../lib/api";
import { createProjecao, aplicarProjecoes } from "../../../lib/actions";
import ExportButton from "../../../components/ExportButton";
import Simulador from "../../../components/Simulador";
import { brl } from "../../../lib/format";

type Proposta = {
  representante_id: number; representante_nome: string;
  fornecedor_id: number; fornecedor_nome: string;
  pix_disponivel: number; divida_aberta: number; valor_proposto: number;
  ja_existe: boolean; motivo: string;
};

export default async function Projecoes() {
  const [projs, reps, forns, auto] = await Promise.all([
    apiGet("/projecoes"),
    apiGet("/representantes"),
    apiGet("/fornecedores"),
    apiPost("/projecoes/automaticas").catch(() => null),
  ]);
  const propostas = ((auto as { propostas: Proposta[] } | null)?.propostas ?? [])
    .filter((p) => !p.ja_existe);
  return (
    <div>
      <h1>Projeções de pagamento</h1>
      <p><ExportButton file="projecoes.csv" label="Exportar CSV" /></p>
      <Simulador reps={reps} forns={forns} />
      <p className="muted">Uma projeção aberta por combinação Representante + Fornecedor. Saldo calculado pelo sistema.</p>
      {propostas.length > 0 && (
        <section className="painel" aria-label="Projeções automáticas">
          <h2>Projeções automáticas (rodízio)</h2>
          <p className="muted">Compostas de PIX disponível × dívida. Revise e aplique — nada é criado sozinho.</p>
          <div className="tablewrap">
            <table>
              <thead><tr><th>Representante</th><th>Fornecedor</th><th>PIX</th><th>Dívida</th><th>Proposto</th><th>Motivo</th></tr></thead>
              <tbody>
                {propostas.map((p) => (
                  <tr key={`${p.representante_id}-${p.fornecedor_id}`}>
                    <td data-label="Representante">{p.representante_nome}</td>
                    <td data-label="Fornecedor">{p.fornecedor_nome}</td>
                    <td data-label="PIX" className="pos">{brl(p.pix_disponivel)}</td>
                    <td data-label="Dívida" className="neg">{brl(p.divida_aberta)}</td>
                    <td data-label="Proposto" className="pend">{brl(p.valor_proposto)}</td>
                    <td data-label="Motivo">{p.motivo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <form action={aplicarProjecoes}>
            <button type="submit">Aplicar {propostas.length} sugestão(ões)</button>
          </form>
        </section>
      )}
      <form action={createProjecao} className="grid">
        <select name="representante_id" required defaultValue="">
          <option value="" disabled>Representante…</option>
          {reps.map((r: { id: number; nome: string }) => <option key={r.id} value={r.id}>{r.nome}</option>)}
        </select>
        <select name="fornecedor_id" required defaultValue="">
          <option value="" disabled>Fornecedor…</option>
          {forns.map((f: { id: number; nome: string }) => <option key={f.id} value={f.id}>{f.nome}</option>)}
        </select>
        <input name="valor_projetado" type="number" step="0.01" min="0.01" placeholder="Valor projetado R$" required />
        <input name="data_prevista" type="date" />
        <input name="observacao" placeholder="Observação" />
        <button type="submit">Criar projeção</button>
      </form>
      <table>
        <thead><tr><th>ID</th><th>Rep.</th><th>Forn.</th><th>Projetado</th><th>Conciliado</th><th>Saldo</th><th>Status</th></tr></thead>
        <tbody>
          {projs.map((p: { id: number; representante_id: number; fornecedor_id: number; valor_projetado: number; valor_conciliado: number; saldo: number; status: string }) => (
            <tr key={p.id}>
              <td data-label="ID">#{p.id}</td><td data-label="Rep.">{p.representante_id}</td><td data-label="Forn.">{p.fornecedor_id}</td>
              <td data-label="Projetado">R$ {p.valor_projetado.toFixed(2)}</td><td data-label="Conciliado" className="pos">R$ {p.valor_conciliado.toFixed(2)}</td>
              <td data-label="Saldo" className={p.saldo > 0 ? "pend" : ""}>R$ {p.saldo.toFixed(2)}</td><td data-label="Status"><span className="badge">{p.status}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
