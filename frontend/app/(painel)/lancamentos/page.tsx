import Link from "next/link";
import { apiGet } from "../../../lib/api";
import { createLancamento } from "../../../lib/actions";
import ExportButton from "../../../components/ExportButton";

export default async function Lancamentos() {
  const [lancs, reps, forns] = await Promise.all([
    apiGet("/lancamentos"),
    apiGet("/representantes"),
    apiGet("/fornecedores"),
  ]);
  return (
    <div>
      <h1>Débitos e créditos</h1>
      <p>Os lançamentos antigos permanecem aqui. Consulte as novas <Link href="/notas">Notas e extratos</Link> para acompanhar documentos, saldos e abatimentos externos.</p>
      <p><ExportButton file="lancamentos.csv" label="Exportar CSV" /></p>
      <form action={createLancamento} className="grid">
        <select name="tipo" defaultValue="debito">
          {["debito", "credito", "pagamento", "desconto", "despesa", "imposto", "salario", "perda"].map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <input name="valor" type="number" step="0.01" min="0.01" placeholder="Valor R$" required />
        <input name="data" type="date" required />
        <select name="fornecedor_id" defaultValue="">
          <option value="">Fornecedor…</option>
          {forns.map((f: { id: number; nome: string }) => <option key={f.id} value={f.id}>{f.nome}</option>)}
        </select>
        <select name="representante_id" defaultValue="">
          <option value="">Representante…</option>
          {reps.map((r: { id: number; nome: string }) => <option key={r.id} value={r.id}>{r.nome}</option>)}
        </select>
        <input name="descricao" placeholder="Descrição" />
        <button type="submit">Lançar</button>
      </form>
      <table>
        <thead><tr><th>ID</th><th>Tipo</th><th>Valor</th><th>Em aberto</th><th>Status</th><th>Descrição</th></tr></thead>
        <tbody>
          {lancs.map((l: { id: number; tipo: string; valor: number; saldo_aberto: number; status: string; descricao: string }) => (
            <tr key={l.id}>
              <td data-label="ID">#{l.id}</td><td data-label="Tipo">{l.tipo}</td>
              <td data-label="Valor" className={l.tipo === "credito" ? "pos" : "neg"}>R$ {l.valor.toFixed(2)}</td><td data-label="Em aberto" className={l.saldo_aberto > 0 ? "pend" : ""}>R$ {l.saldo_aberto.toFixed(2)}</td>
              <td data-label="Status"><span className="badge">{l.status}</span></td><td data-label="Descrição">{l.descricao}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
