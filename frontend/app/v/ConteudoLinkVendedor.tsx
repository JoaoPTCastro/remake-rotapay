import { notFound } from "next/navigation";
import PagarForm from "../../components/PagarForm";
import CopyKey from "../../components/CopyKey";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

function validarContexto(token: string, organizacaoId: number) {
  if (!/^[A-Za-z0-9_-]{22,24}$/.test(token) || !Number.isSafeInteger(organizacaoId) || organizacaoId < 1) notFound();
}

export async function ConteudoLinkVendedor({token, organizacaoId = 1}: {token: string; organizacaoId?: number}) {
  validarContexto(token, organizacaoId);
  const prefixo = organizacaoId === 1 ? "" : `/lojas/${organizacaoId}`;
  const res = await fetch(`${API_URL}${prefixo}/links/v/${token}`, { cache: "no-store", redirect: "error" });
  if (!res.ok) notFound();
  const d = await res.json();
  return (
    <div>
      <p className="muted">Vendedor: <strong>{d.vendedor_nome}</strong></p>
      {d.pago && (
        <p className="pos" role="status">Pagamento recebido — já está registrado no sistema. Obrigado!</p>
      )}
      {d.pix_code ? (
        <div className="card" style={{ maxWidth: 520 }}>
          <p className="muted">Cobrança PIX de <strong>{d.fornecedor_nome}</strong>
            {d.valor_fixo ? <> — <strong>R$ {Number(d.valor_fixo).toFixed(2)}</strong></> : null}</p>
          {d.pix_image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={d.pix_image} alt="QR Code PIX" style={{ maxWidth: 260 }} />
          ) : null}
          <p>Copia e cola:</p>
          <CopyKey value={d.pix_code} label="Copiar código" />
          <p className="muted">Pagou? O sistema registra sozinho — sem comprovante.</p>
        </div>
      ) : d.payload_pix ? (
        <div className="card" style={{ maxWidth: 520 }}>
          <p className="muted">PIX de <strong>{d.fornecedor_nome}</strong>
            {d.valor_fixo ? <> — <strong>R$ {Number(d.valor_fixo).toFixed(2)}</strong></> : <> (valor aberto)</>}</p>
          <p>Copia e cola (chave da loja):</p>
          <CopyKey value={d.payload_pix} label="Copiar código" />
          <p className="muted">Cole no app do seu banco. Pagou? Avise o vendedor com o comprovante.</p>
        </div>
      ) : (
        <PagarForm dados={{ ...d, valor_fixo: d.valor_fixo ?? null }} />
      )}
    </div>
  );
}
