import { apiGet } from "../../../lib/api";
import { createConciliacao, createLancamento, createProjecao, estornarConciliacao } from "../../../lib/actions";
import ExportButton from "../../../components/ExportButton";

type SP = { pix?: string; alvo?: string };
type PessoaOpt = { id: number; nome: string };
type MovOpt = { id: number; codigo: string; saldo_disponivel: number };
type AlvoOpt = { id: number; tipo?: string; descricao?: string; saldo_aberto?: number; saldo?: number };
type Conc = { id: number; movimentacao_id: number; alvo_tipo: string; alvo_id: number; valor: number; estornada: boolean };
type Sug = {
  alvo_tipo: "lancamento" | "projecao";
  alvo_id: number;
  fornecedor_id: number | null;
  saldo_alvo: number;
  valor_sugerido: number;
  data_alvo: string | null;
  confianca: string;
  motivo: string;
};
type SugRes = { sugestoes: Sug[] };

async function Estorno({ id }: { id: number }) {
  const act = estornarConciliacao.bind(null, id);
  return (
    <form action={act} style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
      <input name="motivo" placeholder="Motivo" size={10} aria-label="Motivo do estorno" />
      <input name="senha" type="password" placeholder="Sua senha" size={10} aria-label="Confirme com sua senha" required />
      <button type="submit" className="secondary">Estornar</button>
    </form>
  );
}

function NovoAlvo({ alvoSel, forns, reps }: { alvoSel: string; forns: PessoaOpt[]; reps: PessoaOpt[] }) {
  return (
    <div className="card">
      <p>Nenhum{alvoSel === "projecao" ? "a projeção aberta" : " débito em aberto"}. Crie um abaixo:</p>
      {alvoSel === "projecao" ? (
        <form action={createProjecao} className="grid">
          <select name="representante_id" required defaultValue="" aria-label="Representante">
            <option value="" disabled>Representante…</option>
            {reps.map((r) => <option key={r.id} value={r.id}>{r.nome}</option>)}
          </select>
          <select name="fornecedor_id" required defaultValue="" aria-label="Fornecedor">
            <option value="" disabled>Fornecedor…</option>
            {forns.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
          </select>
          <input name="valor_projetado" type="number" step="0.01" min="0.01" placeholder="Valor R$" required aria-label="Valor projetado" />
          <button type="submit">Criar projeção e voltar</button>
        </form>
      ) : (
        <form action={createLancamento} className="grid">
          <input type="hidden" name="tipo" value="debito" />
          <input name="valor" type="number" step="0.01" min="0.01" placeholder="Valor R$" required aria-label="Valor" />
          <input name="data" type="date" required aria-label="Data" />
          <select name="fornecedor_id" defaultValue="" aria-label="Fornecedor">
            <option value="">Fornecedor…</option>
            {forns.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
          </select>
          <input name="descricao" placeholder="Descrição" aria-label="Descrição" />
          <button type="submit">Criar débito e voltar</button>
        </form>
      )}
    </div>
  );
}

function FormConciliar({ movs, pixSel, alvoSel, alvos, sugPrefill }: {
  movs: MovOpt[]; pixSel: number; alvoSel: string; alvos: AlvoOpt[];
  sugPrefill: Sug | null;
}) {
  return (
    <form action={createConciliacao} className="grid">
      <select name="movimentacao_id" required defaultValue={Number.isFinite(pixSel) ? pixSel : ""} aria-label="PIX">
        <option value="" disabled>PIX com saldo…</option>
        {movs.map((m) => (
          <option key={m.id} value={m.id}>{m.codigo} — R$ {m.saldo_disponivel.toFixed(2)}</option>
        ))}
      </select>
      <input type="hidden" name="alvo_tipo" value={alvoSel} />
      <select name="alvo_id" required defaultValue={sugPrefill ? sugPrefill.alvo_id : ""} aria-label={alvoSel === "projecao" ? "Projeção" : "Débito"}>
        <option value="" disabled>{alvoSel === "projecao" ? "Qual projeção…" : "Qual débito…"}</option>
        {alvos.map((a) => (
          <option key={a.id} value={a.id}>
            #{a.id} {a.tipo ?? ""} — R$ {(a.saldo ?? a.saldo_aberto ?? 0).toFixed(2)} {a.descricao ?? ""}
          </option>
        ))}
      </select>
      <input name="valor" type="number" step="0.01" min="0.01" placeholder="Valor R$"
        defaultValue={sugPrefill ? sugPrefill.valor_sugerido.toFixed(2) : ""} required aria-label="Valor" />
      <button type="submit">Conciliar</button>
    </form>
  );
}

function SugestaoBox({ pixSel, sug, alvoSel, sugPrefill }: {
  pixSel: number; sug: Sug; alvoSel: string; sugPrefill: boolean;
}) {
  return (
    <div className="card" style={{ borderLeft: "4px solid var(--brand)", marginBottom: 12 }}>
      <p style={{ fontSize: 15, fontWeight: 750, margin: "0 0 4px" }}>
        Sugestão para PIX #{pixSel}
      </p>
      <p style={{ margin: "0 0 4px" }}>
        Conciliar <b style={{ fontVariantNumeric: "tabular-nums" }}>R$ {sug.valor_sugerido.toFixed(2)}</b>{" "}
        no {sug.alvo_tipo === "projecao" ? "projeção" : "débito"} #{sug.alvo_id} — {sug.motivo}
      </p>
      <p className="muted">
        {sugPrefill
          ? "Formulário abaixo já vem preenchido com o alvo e o valor sugeridos. Revise e clique em Conciliar: nada é executado automaticamente."
          : "Confira o alvo e o valor antes de conciliar: nada é executado automaticamente."}
      </p>
      {sug.alvo_tipo !== alvoSel && (
        <p style={{ margin: "8px 0 0" }}>
          <a className="btn-secondary" href={`/conciliacoes?pix=${pixSel}&alvo=${sug.alvo_tipo}`}>
            Ver em {sug.alvo_tipo === "projecao" ? "Projeção" : "Débito"}
          </a>
        </p>
      )}
    </div>
  );
}

async function completarMovs(movs: MovOpt[], pixSel: number) {
  if (!Number.isFinite(pixSel) || movs.some((m) => m.id === pixSel)) return;
  const extra = await apiGet(`/movimentacoes/${pixSel}`).catch(() => null);
  if (extra && extra.saldo_disponivel > 0 && extra.status !== "cancelada") movs.unshift(extra);
}

function primeiraSugestao(sugsR: SugRes | null, temPix: boolean): Sug | null {
  return sugsR && temPix && sugsR.sugestoes.length > 0 ? sugsR.sugestoes[0] : null;
}

function sugPrefillable(sug: Sug | null, alvoSel: string, alvosAbertos: AlvoOpt[]): boolean {
  return !!(sug && sug.alvo_tipo === alvoSel && alvosAbertos.some((a) => a.id === sug.alvo_id));
}

function mergeAlvos(a: AlvoOpt[], b: AlvoOpt[]): AlvoOpt[] {
  const vistos = new Set(a.map((x) => x.id));
  return [...a, ...b.filter((x) => !vistos.has(x.id))];
}

async function alvosDaAba(alvoSel: string): Promise<AlvoOpt[]> {
  const [a, p] = await Promise.all(
    alvoSel === "projecao"
      ? [apiGet("/projecoes?status=aberta"), apiGet("/projecoes?status=parcial")]
      : [apiGet("/lancamentos?status=aberto"), apiGet("/lancamentos?status=parcial")]
  );
  return mergeAlvos(a, p);
}

function AreaConciliar({ temAlvo, alvoSel, forns, reps, movs, pixSel, alvos, prefill }: {
  temAlvo: boolean; alvoSel: string; forns: PessoaOpt[]; reps: PessoaOpt[];
  movs: MovOpt[]; pixSel: number; alvos: AlvoOpt[]; prefill: Sug | null;
}) {
  return temAlvo
    ? <FormConciliar movs={movs} pixSel={pixSel} alvoSel={alvoSel} alvos={alvos} sugPrefill={prefill} />
    : <NovoAlvo alvoSel={alvoSel} forns={forns} reps={reps} />;
}

export default async function Conciliacoes({ searchParams }: { searchParams: Promise<SP> }) {
  const { pix, alvo } = await searchParams;
  const alvoSel = alvo === "projecao" ? "projecao" : "lancamento";
  const pixSel = pix ? Number(pix) : NaN;
  const pixQ = Number.isFinite(pixSel) ? `&pix=${pixSel}` : "";
  const sugsP: Promise<SugRes | null> = Number.isFinite(pixSel)
    ? apiGet(`/movimentacoes/${pixSel}/sugestoes`).catch(() => null)
    : Promise.resolve(null);
  const [concs, movsDisp, movsParc, forns, reps, sugsR] = await Promise.all([
    apiGet("/conciliacoes"),
    apiGet("/movimentacoes?status=disponivel"),
    apiGet("/movimentacoes?status=parcial"),
    apiGet("/fornecedores"),
    apiGet("/representantes"),
    sugsP,
  ]);
  const movs = [...movsDisp, ...movsParc];
  await completarMovs(movs, pixSel);
  const temPix = movs.some((m: MovOpt) => m.id === pixSel);
  const alvosAbertos = await alvosDaAba(alvoSel);
  const temAlvo = alvosAbertos.length > 0;
  const sug = primeiraSugestao(sugsR, temPix);
  const prefill = sugPrefillable(sug, alvoSel, alvosAbertos) ? sug : null;
  return (
    <div>
      <h1>Conciliações</h1>
      <p><ExportButton file="conciliacoes.csv" label="Exportar CSV" /></p>
      <p className="muted">Crédito recebido → obrigação correspondente. Excedente nunca vira crédito automático: fica no PIX.</p>
      <nav style={{ display: "flex", gap: 8, margin: "12px 0" }}>
        <a href={`/conciliacoes${pixQ ? `?${pixQ.slice(1)}` : ""}`} className={alvoSel === "lancamento" ? "btn" : "btn-secondary"}>Débito</a>
        <a href={`/conciliacoes?alvo=projecao${pixQ}`} className={alvoSel === "projecao" ? "btn" : "btn-secondary"}>Projeção</a>
      </nav>
      {Number.isFinite(pixSel) && !temPix && (
        <p className="error">PIX #{pixSel} sem saldo para conciliar (já conciliado ou cancelado).</p>
      )}
      {sug && <SugestaoBox pixSel={pixSel} sug={sug} alvoSel={alvoSel} sugPrefill={!!prefill} />}
      <AreaConciliar temAlvo={temAlvo} alvoSel={alvoSel} forns={forns} reps={reps}
                     movs={movs} pixSel={pixSel} alvos={alvosAbertos} prefill={prefill} />
      <table>
        <thead><tr><th>ID</th><th>PIX</th><th>Alvo</th><th>Valor</th><th>Estornada</th><th></th></tr></thead>
        <tbody>
          {(concs as Conc[]).map((c) => (
            <tr key={c.id}>
              <td data-label="ID">#{c.id}</td><td data-label="PIX">PIX #{c.movimentacao_id}</td>
              <td data-label="Alvo">{c.alvo_tipo} #{c.alvo_id}</td><td data-label="Valor">R$ {c.valor.toFixed(2)}</td>
              <td data-label="Estornada">{c.estornada ? "sim" : "não"}</td>
              <td data-label="">{!c.estornada && <Estorno id={c.id} />}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
