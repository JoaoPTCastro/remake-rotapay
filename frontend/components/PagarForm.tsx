"use client";

import { useState } from "react";
import CopyKey from "./CopyKey";

type Chave = {
  fornecedor_id: number;
  fornecedor_nome: string;
  chave_pix: string;
  banco: string;
  conta: string;
  titular: string;
  valor_fixo?: number | null;
};

export default function PagarForm({ dados }: { dados: Chave }) {
  const fixo = dados.valor_fixo ? String(dados.valor_fixo) : "";
  const [valor, setValor] = useState(fixo);
  const [gerado, setGerado] = useState(false);
  return (
    <div>
      {!gerado ? (
        <form
          className="grid"
          style={{ maxWidth: 440 }}
          onSubmit={(e) => {
            e.preventDefault();
            if (Number(valor) > 0) setGerado(true);
          }}
        >
          <p className="muted">Você está pagando para</p>
          <h1>{dados.fornecedor_nome}</h1>
          <input
            type="number" step="0.01" min="0.01" required
            placeholder="Valor a pagar R$" value={valor}
            disabled={!!fixo}
            onChange={(e) => setValor(e.target.value)}
          />
          {fixo && <p className="muted">Valor esperado pela loja. Pagou diferente? A diferença aparece na conciliação.</p>}
          <button type="submit">Gerar chave PIX</button>
          <p className="muted">Confira o valor antes de pagar. Guarde o comprovante.</p>
        </form>
      ) : (
        <div className="card" style={{ maxWidth: 520 }}>
          <p className="muted">Valor a pagar</p>
          <strong style={{ fontSize: 28 }}>R$ {Number(valor).toFixed(2)}</strong>
          <p>Favorecido: {dados.titular}</p>
          {dados.banco && <p className="muted">Banco: {dados.banco}{dados.conta ? ` · Conta: ${dados.conta}` : ""}</p>}
          <p>Chave PIX:</p>
          <CopyKey value={dados.chave_pix} label="Copiar chave" />
          <p className="muted">Abra o app do seu banco → PIX → Pix copia e cola → cole a chave → confira nome e valor → confirme.</p>
          <button type="button" className="secondary" onClick={() => setGerado(false)}>Voltar</button>
        </div>
      )}
    </div>
  );
}
