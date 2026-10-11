import { apiGet } from "../../../../lib/api";
import { cancelarMovimentacao, etapaComprovante } from "../../../../lib/actions";
import DragDropUpload from "../../../../components/DragDropUpload";

async function Avancar({ mid, cid, etapa }: { mid: number; cid: number; etapa: string }) {
  const act = async () => {
    "use server";
    await etapaComprovante(mid, cid, etapa === "recebido" ? "registrado" : "recebido");
  };
  return (
    <form action={act}>
      <button type="submit" className="secondary">
        {etapa === "recebido" ? "Marcar registrado" : "Voltar p/ recebido"}
      </button>
    </form>
  );
}

export default async function Detalhe({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const m = await apiGet(`/movimentacoes/${id}`);
  const comps: { id: number; origem: string; enviado_por: string; data_comprovante: string | null; etapa: string }[] =
    await apiGet(`/movimentacoes/${id}/comprovantes`).catch(() => []);
  const cancelar = cancelarMovimentacao.bind(null, m.id);
  return (
    <div>
      <h1>{m.codigo} — <span className={m.status === "cancelada" ? "neg" : "pos"}>R$ {m.valor.toFixed(2)}</span></h1>
      <p>
        <span className="badge">{m.status}</span>{" "}
        <span className="muted">Disponível: <span className="pos">R$ {m.saldo_disponivel.toFixed(2)}</span> · Data: {m.data_pix}</span>
      </p>
      <p className="muted">
        Remetente: {m.remetente || "—"} · Destinatário: {m.destinatario || "—"} ·
        Representante: {m.representante_id ?? "—"} · Fornecedor: {m.fornecedor_id ?? "—"}
      </p>
      {m.observacao && <p>{m.observacao}</p>}
      {m.possivel_duplicidade && (
        <p className="error">
          Possível duplicidade: outro PIX com mesmo fornecedor, valor e data{" "}
          {Array.isArray(m.duplicidade_movimentacao_ids) && m.duplicidade_movimentacao_ids.length > 0
            ? `(veja ${m.duplicidade_movimentacao_ids.map((d: number) => `#${d}`).join(", ")})`
            : ""} — confira antes de seguir.
        </p>
      )}

      <h2>Comprovantes</h2>
      {comps.length === 0 && <p className="muted">Nenhum comprovante anexado.</p>}
      {comps.map((c) => (
        <div className="card" key={c.id} style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 8 }}>
          <span className="badge">{c.etapa}</span>
          <span className="muted">{c.origem} · por {c.enviado_por || "—"}{c.data_comprovante ? ` · ${c.data_comprovante}` : ""}</span>
          <Avancar mid={m.id} cid={c.id} etapa={c.etapa} />
        </div>
      ))}
      {m.comprovante
        ? <p><a href={`/api/comprovante?mid=${m.id}`}>Baixar comprovante</a></p>
        : null}
      <DragDropUpload mid={m.id} />

      <h2>Zona de perigo</h2>
      <form action={cancelar} className="grid">
        <input name="senha" type="password" placeholder="Confirme com sua senha" aria-label="Confirme com sua senha" required />
        <button type="submit" className="danger">Cancelar movimentação (exclusão lógica)</button>
      </form>
    </div>
  );
}
