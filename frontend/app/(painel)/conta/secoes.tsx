import { brl } from "../../../lib/format";
export type Metricas = { comprovantes_por_dia: { data: string; qtd: number }[]; conciliacoes_por_dia: { data: string; qtd: number }[]; auto_gateway: number; manual_upload: number; creditos_em_aberto: number; };

export function SecaoMetricas({ met }: { met: Metricas | null }) {
  const comp = met ? [...met.comprovantes_por_dia].reverse().slice(-30) : [];
  const conc = met ? [...met.conciliacoes_por_dia].reverse().slice(-30) : [];
  return (
    <section id="metricas" aria-label="Métricas">
      <h2>Métricas</h2>
      <p className="muted">Números da operação: origem dos comprovantes, ritmo de conciliação e créditos.</p>
      {!met && <p className="muted">Métricas indisponíveis no momento.</p>}
      {met && (
        <>
          <div className="cards">
            <div className="card"><small>Comprovantes via gateway</small><strong>{met.auto_gateway}</strong></div>
            <div className="card"><small>Uploads manuais</small><strong>{met.manual_upload}</strong></div>
            <div className="card"><small>Créditos em aberto</small><strong className="pend">{brl(met.creditos_em_aberto)}</strong></div>
          </div>

          <h3>Comprovantes por dia</h3>
          <div className="tablewrap">
            <table>
              <thead><tr><th>Data</th><th>Quantidade</th></tr></thead>
              <tbody>
                {comp.length === 0 && <tr><td colSpan={2} className="muted">Nenhum comprovante ainda.</td></tr>}
                {comp.map((d) => (
                  <tr key={d.data}><td data-label="Data">{d.data}</td><td data-label="Quantidade">{d.qtd}</td></tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3>Conciliações por dia</h3>
          <div className="tablewrap">
            <table>
              <thead><tr><th>Data</th><th>Quantidade</th></tr></thead>
              <tbody>
                {conc.length === 0 && <tr><td colSpan={2} className="muted">Nenhuma conciliação ainda.</td></tr>}
                {conc.map((d) => (
                  <tr key={d.data}><td data-label="Data">{d.data}</td><td data-label="Quantidade">{d.qtd}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
