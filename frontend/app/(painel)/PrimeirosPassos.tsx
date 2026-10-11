import { cookies } from "next/headers";
import { apiGet } from "../../lib/api";
import DismissTour from "../../components/DismissTour";

async function progresso() {
  const [forns, movs, links, concs] = await Promise.all([
    apiGet("/fornecedores").catch(() => []),
    apiGet("/movimentacoes?limit=1").catch(() => []),
    apiGet("/links").catch(() => []),
    apiGet("/conciliacoes").catch(() => []),
  ]);
  return [
    { ok: forns.some((f: { chave_pix: string }) => f.chave_pix), texto: "Fornecedor com chave PIX cadastrada", href: "/cadastro" },
    { ok: movs.length > 0, texto: "Primeiro PIX registrado", href: "/movimentacoes" },
    { ok: links.length > 0, texto: "Link do vendedor gerado", href: "/links" },
    { ok: concs.some((c: { estornada: boolean }) => !c.estornada), texto: "Primeira conciliação feita", href: "/conciliacoes" },
  ];
}

export default async function PrimeirosPassos() {
  const jar = await cookies();
  if (jar.get("tour_off")?.value === "1") return null;
  const items = await progresso();
  if (items.every((i) => i.ok)) return null;
  return (
    <div className="checklist">
      <strong>Primeiros passos</strong>
      <ul>
        {items.map((i) => (
          <li key={i.texto}>
            {i.ok ? "✅" : "⬜"} <a href={i.href}>{i.texto}</a>
          </li>
        ))}
      </ul>
      <p className="muted">Guia completo em <a href="/ajuda">Ajuda</a>.</p>
      <DismissTour />
    </div>
  );
}
