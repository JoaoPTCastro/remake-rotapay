import Link from "next/link";
import { apiGet } from "../../lib/api";
import ExportButton from "../../components/ExportButton";
import PrimeirosPassos from "./PrimeirosPassos";
import VerMais from "../../components/VerMais";
import { brl } from "../../lib/format";
import {
  ArrowLeftRight, ArrowRight, Banknote, BookUser, Building2,
  CircleAlert, ClipboardCheck, Info, Lightbulb, Link2,
  OctagonAlert, TriangleAlert,
} from "lucide-react";

const LIMITE = 8;

const RAPIDO = [
  ["/movimentacoes", "Registrar PIX", <Banknote size={22} key="pix" />],
  ["/controle", "Controle", <ClipboardCheck size={22} key="ctrl" />],
  ["/links", "Gerar link", <Link2 size={22} key="link" />],
  ["/cadastro", "Cadastrar", <BookUser size={22} key="cad" />],
  ["/conciliacoes", "Conciliar", <ArrowLeftRight size={22} key="conc" />],
] as const;

type PF = { fornecedor_id: number; saldo: number; ultima_compra: { data: string; valor: number } | null };
type Mov = {
  id: number; codigo: string; data_pix: string; valor: number; status: string;
  representante_id: number | null; fornecedor_id: number | null; link_token?: string;
};
type PL = {
  id: number; codigo: string; data_pix: string; valor: number; status: string;
  representante_id: number | null; fornecedor_id: number | null; link_token: string;
};
type Insight = {
  codigo: string; nivel: string; mensagem: string;
  acao: string | null; destino: string | null;
};
type FilaItem = {
  fornecedor_id: number; fornecedor_nome: string; prioridade: number;
  nota_antiga: { id: number; data: string; valor: number; saldo_aberto: number; dias_em_aberto: number };
  total_devido: number; faltante_nota_antiga: number;
  pix_em_maos: number; quitavel_agora: boolean;
};

const ROTULO_NIVEL: Record<string, string> = {
  ok: "Tudo certo",
  info: "Informação",
  atencao: "Atenção",
  erro: "Erro",
};

const TITULO_INSIGHT: Record<string, string> = {
  pix_pendentes: "PIX pendentes",
  comprovantes_aguardando: "Comprovantes aguardando",
  obrigacoes_abertas: "Obrigações abertas",
  obrigacoes_proximas: "Pagamentos previstos",
  conciliacoes_recentes: "Conciliações recentes",
};

const ESTILO_NIVEL = {
  info: {
    cor: "var(--muted)",
    fundo: "color-mix(in srgb, var(--muted) 10%, var(--surface))",
    borda: "color-mix(in srgb, var(--muted) 35%, var(--border))",
    icone: <Info size={14} />,
  },
  atencao: {
    cor: "var(--warning)",
    fundo: "color-mix(in srgb, var(--warning) 12%, var(--surface))",
    borda: "color-mix(in srgb, var(--warning) 40%, var(--border))",
    icone: <TriangleAlert size={14} />,
  },
  erro: {
    cor: "var(--danger)",
    fundo: "color-mix(in srgb, var(--danger) 10%, var(--surface))",
    borda: "color-mix(in srgb, var(--danger) 40%, var(--border))",
    icone: <OctagonAlert size={14} />,
  },
  neutro: {
    cor: "var(--muted)",
    fundo: "color-mix(in srgb, var(--muted) 10%, var(--surface))",
    borda: "color-mix(in srgb, var(--muted) 35%, var(--border))",
    icone: <CircleAlert size={14} />,
  },
} as const;

const PESO_NIVEL = { erro: 0, atencao: 1, info: 2, ok: 3 } as const;
const pesoNivel = (n: string) => PESO_NIVEL[n as keyof typeof PESO_NIVEL] ?? 3;

function tituloInsight(codigo: string) {
  return TITULO_INSIGHT[codigo] ?? codigo.replace(/_/g, " ");
}

function InsightCard({ i }: { i: Insight }) {
  const est = i.nivel === "erro" ? ESTILO_NIVEL.erro
    : i.nivel === "atencao" ? ESTILO_NIVEL.atencao
    : i.nivel === "info" ? ESTILO_NIVEL.info
    : ESTILO_NIVEL.neutro;
  const rotulo = ROTULO_NIVEL[i.nivel] ?? i.nivel;
  return (
    <article
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderLeft: `4px solid ${est.cor}`,
        borderRadius: "var(--radius)",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        padding: 16,
      }}
    >
      <span
        style={{
          alignItems: "center",
          background: "var(--surface)",
          border: `1px solid ${est.cor}`,
          borderRadius: 99,
          color: est.cor,
          display: "inline-flex",
          fontSize: 11,
          fontWeight: 750,
          gap: 6,
          letterSpacing: ".05em",
          padding: "3px 10px",
          textTransform: "uppercase",
          width: "fit-content",
        }}
      >
        {est.icone}{rotulo}
      </span>
      <strong style={{ display: "block", fontSize: 16, letterSpacing: "-.02em" }}>
        {tituloInsight(i.codigo)}
      </strong>
      <p style={{ color: "var(--muted)", fontSize: 13, margin: "0", flex: 1 }}>
        {i.mensagem}
      </p>
      {i.destino && i.acao ? (
        <a
          href={i.destino}
          style={{ alignItems: "center", display: "inline-flex", fontWeight: 700, gap: 6, width: "fit-content" }}
        >
          {i.acao}<ArrowRight size={15} />
        </a>
      ) : null}
    </article>
  );
}

function InsightsSection({ raw }: { raw: Insight[] }) {
  const visiveis = raw
    .filter((i) => i.destino && i.mensagem)
    .sort((a, b) => pesoNivel(a.nivel) - pesoNivel(b.nivel));
  if (visiveis.length === 0) return null;
  return (
    <section className="painel" aria-label="Insights">
      <h2><Lightbulb size={18} /> Insights</h2>
      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))" }}>
        {visiveis.map((i) => <InsightCard key={i.codigo} i={i} />)}
      </div>
    </section>
  );
}

function FilaPagamentos({ fila }: { fila: FilaItem[] }) {
  return (
    <section className="painel" aria-label="Fila de pagamentos">
      <h2><ArrowLeftRight size={18} /> Fila de pagamentos (rodízio)</h2>
      <p className="muted">Nota mais antiga em aberto por fornecedor e quanto falta para quitá-la. Quite as menores para liberar posições.</p>
      <div className="tablewrap">
        <table>
          <thead><tr><th>#</th><th>Fornecedor</th><th>Nota antiga</th><th>Faltante</th><th>Total devido</th><th>PIX em mãos</th><th></th></tr></thead>
          <tbody>
            {fila.length === 0 && (
              <tr><td colSpan={7} className="muted">Nenhum débito em aberto. 🎉</td></tr>
            )}
            {fila.map((f, i) => (
              <tr key={f.fornecedor_id}>
                <td data-label="Posição">{i + 1}º</td>
                <td data-label="Fornecedor">{f.fornecedor_nome}</td>
                <td data-label="Nota antiga">{f.nota_antiga.data} ({f.nota_antiga.dias_em_aberto}d)</td>
                <td data-label="Faltante" className="pend">{brl(f.faltante_nota_antiga)}</td>
                <td data-label="Total devido" className="neg">{brl(f.total_devido)}</td>
                <td data-label="PIX em mãos" className="pos">{brl(f.pix_em_maos)}</td>
                <td data-label="">{f.quitavel_agora
                  ? <a className="btn" href="/conciliacoes">Quitar agora</a>
                  : <span className="muted">aguardando PIX</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default async function DashboardLegado() {
  const [d, movs, pls, forns, reps, fila] = await Promise.all([
    apiGet("/dashboard"),
    apiGet("/movimentacoes?limit=60"),
    apiGet("/pix-de-links?limit=60"),
    apiGet("/fornecedores").catch(() => []),
    apiGet("/representantes").catch(() => []),
    apiGet("/fila-pagamentos").catch(() => []),
  ]);
  const fnome = new Map((forns as { id: number; nome: string }[]).map((f) => [f.id, f.nome]));
  const rnome = new Map((reps as { id: number; nome: string }[]).map((r) => [r.id, r.nome]));
  const cards: [string, string, string][] = [
    ["Total a pagar", brl(d.total_a_pagar), "neg"],
    ["PIX disponível", brl(d.pix_disponivel), "pos"],
    ["PIX pendentes", String(d.pix_pendentes), "pend"],
    ["PIX conciliados", String(d.pix_conciliados), "pos"],
    ["Projeções abertas", String(d.projecoes_abertas), "pend"],
  ];
  const pfs = d.por_fornecedor as PF[];
  const saidas = movs as Mov[];
  const links = pls as PL[];
  const nome = (m: Map<number, string>, id: number | null) => (!id ? "—" : (m.get(id) ?? `#${id}`));

  return (
    <div>
      <h1>Painel legado</h1><p className="muted">Registros antigos e projeções. Estes valores não integram os totais dos módulos novos.</p><p><Link href="/">Voltar à visão dos módulos novos</Link></p>
      <PrimeirosPassos />
      <section className="quickbox" aria-label="Acesso rápido">
        <h2>Acesso rápido</h2>
        <p className="muted">O dia a dia da loja em um toque.</p>
        <div className="quickgrid">
          {RAPIDO.map(([href, label, icon]) => (
            <a key={href} href={href} className="quickbtn">
              {icon}<strong>{label}</strong>
            </a>
          ))}
        </div>
      </section>
      <div className="cards">
        {cards.map(([k, v, tone]) => (
          <div className="card" key={k}><small>{k}</small><strong className={tone}>{v}</strong></div>
        ))}
      </div>
      <InsightsSection raw={d.insights ?? []} />

      <FilaPagamentos fila={fila as FilaItem[]} />

      <section className="painel" aria-label="Valores por fornecedor">
        <h2><Building2 size={18} /> Valores por fornecedor</h2>
        <p><ExportButton file="posicao-fornecedores.csv" label="Exportar posição CSV" /></p>
        <div className="tablewrap">
          <table>
            <thead><tr><th>Fornecedor</th><th>Saldo aberto</th><th>Última compra</th></tr></thead>
            <tbody>
              <VerMais total={pfs.length} limite={LIMITE} colSpan={3} extra={
                <>{pfs.slice(LIMITE).map((r) => (
                  <tr key={r.fornecedor_id}>
                    <td data-label="Fornecedor">{fnome.get(r.fornecedor_id) ?? `#${r.fornecedor_id}`}</td>
                    <td data-label="Saldo aberto" className="neg">{brl(r.saldo)}</td>
                    <td data-label="Última compra">{r.ultima_compra ? `${r.ultima_compra.data} · ${brl(r.ultima_compra.valor)}` : "—"}</td>
                  </tr>
                ))}</>
              }>
                {pfs.slice(0, LIMITE).map((r) => (
                  <tr key={r.fornecedor_id}>
                    <td data-label="Fornecedor">{fnome.get(r.fornecedor_id) ?? `#${r.fornecedor_id}`}</td>
                    <td data-label="Saldo aberto" className="neg">{brl(r.saldo)}</td>
                    <td data-label="Última compra">{r.ultima_compra ? `${r.ultima_compra.data} · ${brl(r.ultima_compra.valor)}` : "—"}</td>
                  </tr>
                ))}
              </VerMais>
            </tbody>
          </table>
        </div>
      </section>

      <section className="painel" aria-label="Últimas saídas">
        <h2><Banknote size={18} /> Últimas saídas</h2>
        <div className="tablewrap">
          <table>
            <thead><tr><th>Data</th><th>Valor</th><th>Cliente</th><th>Destino</th><th>Status</th><th></th></tr></thead>
            <tbody>
              <VerMais total={saidas.length} limite={LIMITE} colSpan={6} extra={
                <>{saidas.slice(LIMITE).map((m) => (
                  <tr key={m.id}>
                    <td data-label="Data">{m.data_pix}</td>
                    <td data-label="Valor">{brl(m.valor)}</td>
                    <td data-label="Cliente">{nome(rnome, m.representante_id)}</td>
                    <td data-label="Destino">{nome(fnome, m.fornecedor_id)}</td>
                    <td data-label="Status"><span className="badge">{m.status}</span></td>
                    <td data-label=""><a href={`/movimentacoes/${m.id}`}>Detalhes</a></td>
                  </tr>
                ))}</>
              }>
                {saidas.slice(0, LIMITE).map((m) => (
                  <tr key={m.id}>
                    <td data-label="Data">{m.data_pix}</td>
                    <td data-label="Valor">{brl(m.valor)}</td>
                    <td data-label="Cliente">{nome(rnome, m.representante_id)}</td>
                    <td data-label="Destino">{nome(fnome, m.fornecedor_id)}</td>
                    <td data-label="Status"><span className="badge">{m.status}</span></td>
                    <td data-label=""><a href={`/movimentacoes/${m.id}`}>Detalhes</a></td>
                  </tr>
                ))}
              </VerMais>
            </tbody>
          </table>
        </div>
      </section>

      <section className="painel" aria-label="Últimos PIX gerados pelos links">
        <h2><Link2 size={18} /> Últimos PIX gerados pelos links</h2>
        <p className="muted">Só pagamentos rastreáveis (QR, cobrança e gateway).</p>
        <div className="tablewrap">
          <table>
            <thead><tr><th>Data</th><th>Valor</th><th>Vendedor</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {links.length === 0 && <tr><td colSpan={5} className="muted">Nenhum PIX de link ainda.</td></tr>}
              <VerMais total={links.length} limite={LIMITE} colSpan={5} extra={
                <>{links.slice(LIMITE).map((m) => (
                  <tr key={m.id}>
                    <td data-label="Data">{m.data_pix}</td>
                    <td data-label="Valor">{brl(m.valor)}</td>
                    <td data-label="Vendedor">{nome(rnome, m.representante_id)}</td>
                    <td data-label="Status"><span className="badge">{m.status}</span></td>
                    <td data-label=""><a href={`/movimentacoes/${m.id}`}>Detalhes</a></td>
                  </tr>
                ))}</>
              }>
                {links.slice(0, LIMITE).map((m) => (
                  <tr key={m.id}>
                    <td data-label="Data">{m.data_pix}</td>
                    <td data-label="Valor">{brl(m.valor)}</td>
                    <td data-label="Vendedor">{nome(rnome, m.representante_id)}</td>
                    <td data-label="Status"><span className="badge">{m.status}</span></td>
                    <td data-label=""><a href={`/movimentacoes/${m.id}`}>Detalhes</a></td>
                  </tr>
                ))}
              </VerMais>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
