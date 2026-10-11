"use client";

import { useRef, useState } from "react";
import { createPessoa } from "../lib/actions";

// Cadastro em 3 etapas; campos de pagamento só para fornecedor.
// Todas as etapas ficam montadas (só escondidas) para nada se perder no envio.
const ETAPAS = ["Quem é", "Contato", "Pagamento"];

export default function PessoaForm({ tipoPadrao }: { tipoPadrao: string }) {
  const [etapa, setEtapa] = useState(0);
  const [tipo, setTipo] = useState(tipoPadrao);
  const nomeRef = useRef<HTMLInputElement>(null);
  const fornecedor = tipo === "fornecedor";
  const mostra = (i: number) => (i === etapa ? undefined : { display: "none" as const });
  const avancar = () => {
    if (etapa === 0 && (nomeRef.current?.value.trim().length ?? 0) < 2) {
      nomeRef.current?.focus();
      return;
    }
    setEtapa(etapa + 1);
  };
  return (
    <form action={createPessoa} className="grid">
      <p className="muted" role="status">
        Etapa {etapa + 1} de {ETAPAS.length}: {ETAPAS[etapa]}
        {" · "}
        {ETAPAS.map((t, i) => (i === etapa ? "●" : "○")).join(" ")}
      </p>
      <div className="grid" style={mostra(0)}>
        <select name="tipo" value={tipo} aria-label="Tipo" onChange={(e) => setTipo(e.target.value)}>
          <option value="representante">Representante (cliente/rifeiro)</option>
          <option value="fornecedor">Fornecedor</option>
        </select>
        <input ref={nomeRef} name="nome" placeholder="Nome / razão social" required minLength={2} aria-label="Nome" />
        <input name="apelido" placeholder="Apelido" aria-label="Apelido" />
        <input name="documento" placeholder="CPF/CNPJ" aria-label="Documento" />
      </div>
      <div className="grid" style={mostra(1)}>
        <input name="telefone" placeholder="Telefone" aria-label="Telefone" />
        <input name="email" type="email" placeholder="Email" aria-label="Email" />
        <input name="endereco" placeholder="Endereço" aria-label="Endereço" />
      </div>
      <div className="grid" style={mostra(2)}>
        {fornecedor ? (
          <>
            <input name="chave_pix" placeholder="Chave PIX" aria-label="Chave PIX" />
            <input name="banco" placeholder="Banco da chave" aria-label="Banco" />
            <input name="conta" placeholder="Conta" aria-label="Conta" />
            <input name="titular_chave" placeholder="Titular da chave" aria-label="Titular" />
            <input name="prazo_dias" type="number" min="0" placeholder="Prazo (dias)" aria-label="Prazo em dias" />
            <input name="tolerancia_credito" type="number" step="0.01" min="0" placeholder="Tolerância crédito R$" aria-label="Tolerância de crédito" />
            <select name="prioridade" defaultValue="2" aria-label="Prioridade de pagamento">
              <option value="1">Prioridade alta</option>
              <option value="2">Prioridade normal</option>
              <option value="3">Prioridade baixa</option>
            </select>
          </>
        ) : (
          <>
            <input type="hidden" name="prioridade" value="2" />
            <p className="muted">Representante não usa chave nem prazo — pode concluir.</p>
          </>
        )}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {etapa > 0 && (
          <button type="button" className="secondary" onClick={() => setEtapa(etapa - 1)}>
            Voltar
          </button>
        )}
        {etapa < ETAPAS.length - 1 ? (
          <button type="button" onClick={avancar}>
            Continuar
          </button>
        ) : (
          <button type="submit">Cadastrar</button>
        )}
      </div>
    </form>
  );
}
