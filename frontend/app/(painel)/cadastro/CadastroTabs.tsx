import { apiGet } from "../../../lib/api";
import CopyKey from "../../../components/CopyKey";
import PessoaForm from "../../../components/PessoaForm";
import { Building2, Users, KeyRound } from "lucide-react";

type Pessoa = {
  id: number; nome: string; documento: string; telefone: string; ativo: boolean;
  apelido: string; chave_pix: string; banco: string; conta: string;
  prazo_dias: number; tolerancia_credito: number;
};

const ABAS = [
  ["fornecedores", "Fornecedores", <Building2 size={16} key="f" />],
  ["pessoas", "Pessoas", <Users size={16} key="p" />],
  ["chaves", "Chaves PIX", <KeyRound size={16} key="c" />],
] as const;

export default async function CadastroTabs({ aba }: { aba: string }) {
  const atual = ABAS.some(([v]) => v === aba) ? aba : "fornecedores";
  const [reps, forns] = await Promise.all([
    apiGet("/representantes"),
    apiGet("/fornecedores"),
  ]);
  return (
    <div>
      <h1>Cadastro</h1>
      <nav style={{ display: "flex", gap: 8, margin: "12px 0" }}>
        {ABAS.map(([v, label, icon]) => (
          <a key={v} href={`/cadastro?aba=${v}`} className={v === atual ? "btn" : "btn-secondary"}
             style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>{icon}{label}</a>
        ))}
      </nav>
      {atual === "fornecedores" && (
        <>
          <PessoaForm tipoPadrao="fornecedor" />
          <div className="tablewrap">
          <table>
            <thead><tr><th>ID</th><th>Nome</th><th>Documento</th><th>Chave PIX</th><th>Banco</th><th>Prazo</th><th>Tolerância</th><th></th></tr></thead>
            <tbody>
              {(forns as Pessoa[]).map((p) => (
                <tr key={p.id}>
                  <td data-label="ID">#{p.id}</td><td data-label="Nome">{p.nome}</td><td data-label="Documento">{p.documento || "—"}</td>
                  <td data-label="Chave PIX">{p.chave_pix ? <CopyKey value={p.chave_pix} /> : <span className="badge">sem chave</span>}</td>
                  <td data-label="Banco">{p.banco || "—"}</td>
                  <td data-label="Prazo">{p.prazo_dias ? `${p.prazo_dias}d` : "—"}</td>
                  <td data-label="Tolerância">{p.tolerancia_credito ? `R$ ${p.tolerancia_credito.toFixed(2)}` : "—"}</td>
                  <td data-label="">{p.chave_pix ? <a href={`/pagar/${p.id}`} target="_blank">Página</a> : null}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </>
      )}
      {atual === "pessoas" && (
        <>
          <PessoaForm tipoPadrao="representante" />
          <div className="tablewrap">
          <table>
            <thead><tr><th>ID</th><th>Nome</th><th>Apelido</th><th>Telefone</th><th>Ativo</th></tr></thead>
            <tbody>
              {(reps as Pessoa[]).map((p) => (
                <tr key={p.id}>
                  <td data-label="ID">#{p.id}</td><td data-label="Nome">{p.nome}</td><td data-label="Apelido">{p.apelido || "—"}</td>
                  <td data-label="Telefone">{p.telefone || "—"}</td><td data-label="Ativo">{p.ativo ? "sim" : "não"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </>
      )}
      {atual === "chaves" && (
        <div className="tablewrap">
        <table>
          <thead><tr><th>Fornecedor</th><th>Chave PIX</th><th>Banco / Conta</th><th>Titular</th><th>Página</th></tr></thead>
          <tbody>
            {(forns as Pessoa[]).map((f) => (
              <tr key={f.id}>
                <td data-label="Fornecedor">{f.nome}<br /><span className="muted">{f.documento}</span></td>
                <td data-label="Chave PIX">{f.chave_pix ? <CopyKey value={f.chave_pix} /> : <span className="badge">sem chave</span>}</td>
                <td data-label="Banco / Conta">{f.banco}{f.conta ? ` · ${f.conta}` : ""}</td>
                <td data-label="Titular">{f.nome}</td>
                <td data-label="">{f.chave_pix ? <a href={`/pagar/${f.id}`} target="_blank">Abrir</a> : null}</td>
              </tr>
            ))}
          </tbody>
        </table>
          </div>
      )}
    </div>
  );
}
