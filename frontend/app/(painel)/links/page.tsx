import LinksTitular from "./LinksTitular";
import { apiGet } from "../../../lib/api";
import { createLink, revokeLink, cobrarLink } from "../../../lib/actions";
import CopyLink from "../../../components/CopyLink";

async function Revogar({ id }: { id: number }) {
  const act = async () => {
    "use server";
    await revokeLink(id);
  };
  return (
    <form action={act}>
      <button type="submit" className="danger">Revogar</button>
    </form>
  );
}

async function Cobrar({ id }: { id: number }) {
  const act = async () => {
    "use server";
    await cobrarLink(id);
  };
  return (
    <form action={act}>
      <button type="submit">Gerar cobrança PIX</button>
    </form>
  );
}

export default async function Links({ searchParams }: { searchParams: Promise<{ pessoa_id?: string; status?: string; offset?: string }> }) {
  const filtros = await searchParams;
  if (filtros.pessoa_id) { if (!/^[1-9]\d*$/.test(filtros.pessoa_id)) return <p role="alert">Identificador de titular inválido.</p>; return <LinksTitular id={filtros.pessoa_id} status={filtros.status} offset={filtros.offset} />; }
  const [links, reps, forns] = await Promise.all([
    apiGet("/links"),
    apiGet("/representantes"),
    apiGet("/fornecedores"),
  ]);
  return (
    <div>
      <h1>Links do vendedor</h1>
      <p className="muted">
        Você (loja) gera o link e envia ao vendedor. Ele abre, informa o valor
        e recebe a chave PIX do fornecedor para repassar ao cliente.
      </p>
      <h2>Gerar link</h2>
      <form action={createLink} className="grid">
        <select name="representante_id" required defaultValue="">
          <option value="" disabled>Vendedor…</option>
          {reps.map((r: { id: number; nome: string }) => <option key={r.id} value={r.id}>{r.nome}</option>)}
        </select>
        <select name="fornecedor_id" required defaultValue="">
          <option value="" disabled>Chave de qual fornecedor…</option>
          {forns.filter((f: { chave_pix: string }) => f.chave_pix).map((f: { id: number; nome: string }) => (
            <option key={f.id} value={f.id}>{f.nome}</option>
          ))}
        </select>
        <input name="valor_fixo" type="number" step="0.01" min="0.01" placeholder="Valor fixo (opcional)" />
        <button type="submit">Gerar link</button>
      </form>
      <p className="muted">Só fornecedores com chave PIX cadastrada aparecem acima.</p>
      <div className="tablewrap">
        <table>
        <thead><tr><th>Vendedor</th><th>Fornecedor</th><th>Valor fixo</th><th>Link</th><th>Cobrança PIX</th><th>Ativo</th><th></th></tr></thead>
        <tbody>
          {links.map((l: { id: number; token: string; representante_nome: string; fornecedor_nome: string; valor_fixo: number | null; ativo: boolean; tem_cobranca: boolean }) => (
            <tr key={l.id}>
              <td data-label="Vendedor">{l.representante_nome}</td><td data-label="Fornecedor">{l.fornecedor_nome}</td>
              <td data-label="Valor fixo">{l.valor_fixo ? `R$ ${l.valor_fixo.toFixed(2)}` : "livre"}</td>
              <td data-label="Link"><CopyLink path={`/v/${l.token}`} /></td>
              <td data-label="Cobrança PIX">{l.tem_cobranca
                ? <span className="badge">QR ativo</span>
                : (l.ativo && l.valor_fixo ? <Cobrar id={l.id} /> : <span className="muted">—</span>)}</td>
              <td data-label="Ativo">{l.ativo ? "sim" : "não"}</td>
              <td data-label="">{l.ativo && <Revogar id={l.id} />}</td>
            </tr>
          ))}
          {links.length === 0 && <tr><td colSpan={7} className="muted">Nenhum link gerado.</td></tr>}
        </tbody>
        </table>
      </div>
      <p className="muted">Cobrança exige valor fixo no link e vendedor com email, telefone e documento (regra da Checkto). Ao pagar, o sistema registra tudo sozinho.</p>
    </div>
  );
}
