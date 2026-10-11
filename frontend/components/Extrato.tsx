import { apiGet } from "../lib/api";
import { createMovimentacao } from "../lib/actions";
import ExportButton from "./ExportButton";

type Mov = {
  id: number; codigo: string; data_pix: string; valor: number;
  saldo_disponivel: number; status: string; remetente: string;
  representante_id: number | null; fornecedor_id: number | null;
  autor: string; forma_pagamento: string; natureza: string;
};

type ModoExtrato = "registro" | "controle";
type PessoaOpt = { id: number; nome: string };

function FiltrosControle({ filtros, reps, forns }: {
  filtros: Record<string, string>; reps: PessoaOpt[]; forns: PessoaOpt[];
}) {
  return (
    <form method="get" className="grid">
      <input name="q" placeholder="Buscar código, remetente…" defaultValue={filtros.q ?? ""} aria-label="Buscar por código ou remetente" />
      <input name="chave" placeholder="Chave PIX (remetente, destino ou chave)…" defaultValue={filtros.chave ?? ""} aria-label="Buscar por chave PIX" />
      <select name="com_link" defaultValue={filtros.com_link ?? ""} aria-label="Filtrar por link">
        <option value="">Com ou sem link</option>
        <option value="sim">Só com link</option>
        <option value="nao">Só sem link</option>
      </select>
      <select name="representante_id" defaultValue={filtros.representante_id ?? ""} aria-label="Filtrar por cliente">
        <option value="">Todos os clientes…</option>
        {reps.map((r) => <option key={r.id} value={r.id}>{r.nome}</option>)}
      </select>
      <select name="fornecedor_id" defaultValue={filtros.fornecedor_id ?? ""} aria-label="Filtrar por fornecedor">
        <option value="">Todos os fornecedores…</option>
        {forns.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
      </select>
      <select name="status" defaultValue={filtros.status ?? ""} aria-label="Filtrar por status">
        <option value="">Todos os status</option>
        {["disponivel", "parcial", "conciliada", "cancelada"].map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>
      <input name="data_ini" type="date" defaultValue={filtros.data_ini ?? ""} aria-label="Data inicial" />
      <input name="data_fim" type="date" defaultValue={filtros.data_fim ?? ""} aria-label="Data final" />
      <button type="submit">Filtrar</button>
    </form>
  );
}

export default async function Extrato({ filtros = {}, modo }: { filtros?: Record<string, string>; modo: ModoExtrato }) {
  const q = new URLSearchParams();
  for (const k of ["data_ini", "data_fim", "representante_id", "fornecedor_id", "status", "q", "chave"]) {
    if (filtros[k]) q.set(k, filtros[k]);
  }
  if (filtros.com_link === "sim") q.set("com_link", "true");
  if (filtros.com_link === "nao") q.set("com_link", "false");
  const [movs, reps, forns] = await Promise.all([
    modo === "controle" ? apiGet(`/movimentacoes?${q.toString()}`) : Promise.resolve([]),
    apiGet("/representantes"),
    apiGet("/fornecedores"),
  ]);
  const repNome = new Map<number, string>(reps.map((r: { id: number; nome: string }) => [r.id, r.nome]));
  const fornNome = new Map<number, string>(forns.map((f: { id: number; nome: string }) => [f.id, f.nome]));
  const nomeRep = (id: number | null) => (!id ? "—" : (repNome.get(id) ?? ("#" + id)));
  const nomeForn = (id: number | null) => (!id ? "—" : (fornNome.get(id) ?? ("#" + id)));
  const conc = (s: string) => s === "conciliada" ? "☑" : s === "parcial" ? "◐" : s === "cancelada" ? "✕" : "☐";

  return (
    <div>
      {modo === "registro" ? (
        <>
          <h2>Dados do PIX</h2>
          <form action={createMovimentacao} className="grid">
            <input name="data_pix" type="date" required aria-label="Data do PIX" />
            <input name="valor" type="number" step="0.01" min="0.01" placeholder="Valor R$" required aria-label="Valor" />
            <input name="remetente" placeholder="Remetente" aria-label="Remetente" />
            <select name="representante_id" defaultValue="" aria-label="Representante">
              <option value="">Representante…</option>
              {reps.map((r: { id: number; nome: string }) => <option key={r.id} value={r.id}>{r.nome}</option>)}
            </select>
            <input name="destinatario" placeholder="Destinatário" aria-label="Destinatário" />
            <select name="fornecedor_id" defaultValue="" aria-label="Fornecedor">
              <option value="">Fornecedor…</option>
              {forns.map((f: { id: number; nome: string }) => <option key={f.id} value={f.id}>{f.nome}</option>)}
            </select>
            <input name="autor" placeholder="Autor (quem lançou)" aria-label="Autor" />
            <select name="forma_pagamento" defaultValue="PIX" aria-label="Forma de pagamento">
              <option value="PIX">PIX</option>
              <option value="TED">TED</option>
              <option value="DINHEIRO">Dinheiro</option>
              <option value="BOLETO">Boleto</option>
            </select>
            <input name="natureza" placeholder="Natureza" defaultValue="DESPESA" aria-label="Natureza" />
            <input name="observacao" placeholder="Observação" aria-label="Observação" />
            <button type="submit">Registrar</button>
          </form>
        </>
      ) : (
        <>
          <FiltrosControle filtros={filtros} reps={reps} forns={forns} />

          <p><ExportButton file="movimentacoes.csv" label="Exportar CSV (respeita filtros)" /></p>
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Código</th><th>Cliente</th><th>Data</th><th>Valor</th><th>Autor</th>
                  <th>Remetente</th><th>Fornecedor</th><th>Forma</th><th>Natureza</th>
                  <th title="Conciliação">Conc.</th><th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {(movs as Mov[]).map((m) => (
                  <tr key={m.id}>
                    <td data-label="Código">{m.codigo}</td>
                    <td data-label="Cliente">{nomeRep(m.representante_id)}</td>
                    <td data-label="Data">{m.data_pix}</td>
                    <td data-label="Valor" className={m.status === "cancelada" ? "neg" : "pos"}>R$ {m.valor.toFixed(2)}</td>
                    <td data-label="Autor">{m.autor || "—"}</td>
                    <td data-label="Remetente">{m.remetente || "—"}</td>
                    <td data-label="Fornecedor">{nomeForn(m.fornecedor_id)}</td>
                    <td data-label="Forma">{m.forma_pagamento}</td>
                    <td data-label="Natureza">{m.natureza}</td>
                    <td data-label="Conciliação" title={`Disponível R$ ${m.saldo_disponivel.toFixed(2)}`}>{conc(m.status)} {m.status}</td>
                    <td data-label="Ações">{m.saldo_disponivel > 0 && m.status !== "cancelada"
                      ? <a className="btn" href={`/conciliacoes?pix=${m.id}`}>Conciliar</a>
                      : <a href={`/movimentacoes/${m.id}`}>Abrir</a>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
