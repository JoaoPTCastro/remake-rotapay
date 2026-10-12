"use client";

import { useRef, useState } from "react";
import { salvarCadastro } from "../../../lib/cadastro-actions";
import type { CadastroPessoa, Contato, ChavePix } from "../../../lib/cadastro-types";
import styles from "./CadastroManager.module.css";
import PreferenciasTabela from "../../../components/PreferenciasTabela";
import { rotulosColunas, type PreferenciaTabela } from "../../../lib/configuracoes-types";
import { ordenarCadastros, filtrosCadastro, situacaoCadastro } from "../../../lib/cadastro-tabela";
import CopyKey from "../../../components/CopyKey";

type AbaFicha = "dados" | "financeiro" | "dashboard";

function Campo({ nome, titulo, valor, tipo = "text", obrigatorio = false }: { nome: string; titulo: string; valor?: string | number | null; tipo?: string; obrigatorio?: boolean }) {
  return <label>{titulo}<input name={nome} type={tipo} defaultValue={valor ?? ""} required={obrigatorio} min={tipo === "number" ? 0 : undefined} step={nome === "tolerancia_credito" ? "0.01" : undefined} /></label>;
}
function Opcoes({ nome, titulo, valor, itens }: { nome: string; titulo: string; valor: string; itens: [string, string][] }) {
  return <label>{titulo}<select name={nome} defaultValue={valor}>{itens.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select></label>;
}
function Editor({ operacao, pessoaId, itemId, children }: { operacao: "pessoa" | "contato" | "chave"; pessoaId: number | null; itemId: number | null; children: React.ReactNode }) {
  const formRef = useRef<HTMLFormElement>(null);
  const [estado, setEstado] = useState<{ ok: boolean; mensagem: string } | null>(null);
  const [enviando, setEnviando] = useState(false);
  return <form ref={formRef} className="grid" action={async (form) => {
    setEnviando(true);
    try {
      const resultado = await salvarCadastro(operacao, pessoaId, itemId, form);
      setEstado(resultado);
      if (resultado.ok && (operacao === "pessoa" ? pessoaId === null : itemId === null)) formRef.current?.reset();
    }
    finally { setEnviando(false); }
  }}>
    {children}
    <div style={{ gridColumn: "1 / -1" }}><button disabled={enviando}>{enviando ? "Salvando..." : "Salvar"}</button>{estado && <p role={estado.ok ? "status" : "alert"} style={{ color: estado.ok ? "var(--success)" : "var(--danger)" }}>{estado.mensagem}</p>}</div>
  </form>;
}
function Dados({ pessoa }: { pessoa?: CadastroPessoa }) {
  const dados = pessoa ?? { nome: "", tipo: "representante", documento: "", apelido: "", endereco: "", prazo_dias: 0, prioridade: 2, tolerancia_credito: 0, observacoes: "" };
  return <>
    <Campo nome="nome" titulo="Nome / razão social" valor={dados.nome} obrigatorio />
    <Opcoes nome="tipo" titulo="Papel no cadastro" valor={dados.tipo} itens={[["representante", "Cliente / representante"], ["fornecedor", "Fornecedor"], ["ambos", "Cliente e fornecedor"]]} />
    <Campo nome="documento" titulo="CPF/CNPJ" valor={dados.documento} />
    <Campo nome="apelido" titulo="Apelido" valor={dados.apelido} />
    <Campo nome="endereco" titulo="Endereço" valor={dados.endereco} />
    <Campo nome="prazo_dias" titulo="Prazo em dias" valor={dados.prazo_dias} tipo="number" />
    <Opcoes nome="prioridade" titulo="Prioridade" valor={String(dados.prioridade)} itens={[["1", "Alta"], ["2", "Normal"], ["3", "Baixa"]]} />
    <Campo nome="tolerancia_credito" titulo="Tolerância de crédito (R$)" valor={dados.tolerancia_credito} tipo="number" />
    <Campo nome="observacoes" titulo="Observações" valor={dados.observacoes} />
    {pessoa && <label><input type="checkbox" name="ativo" defaultChecked={pessoa.ativo} /> Cadastro ativo</label>}
  </>;
}
function ContatoCampos({ contato, primeiro }: { contato?: Contato; primeiro: boolean }) {
  return <>
    <Campo nome="nome" titulo="Nome do contato" valor={contato?.nome} obrigatorio />
    <Campo nome="cargo" titulo="Cargo / responsabilidade" valor={contato?.cargo} />
    <Campo nome="telefone" titulo="Telefone com DDI e DDD" valor={contato?.telefone} />
    <Campo nome="email" titulo="E-mail" tipo="email" valor={contato?.email} />
    <label><input type="checkbox" name="principal" defaultChecked={contato?.principal ?? primeiro} /> Contato principal</label>
    <label><input type="checkbox" name="ativo" defaultChecked={contato?.ativo ?? true} /> Ativo</label>
  </>;
}
function ChaveCampos({ chave, primeiro }: { chave?: ChavePix; primeiro: boolean }) {
  const dados = chave ?? { chave: "", tipo: "aleatoria", titular: "", banco: "", agencia: "", conta: "", tipo_conta: "corrente", categoria: "fixa", validade: null, principal: primeiro, ativo: true };
  return <>
    <Campo nome="chave" titulo="Chave PIX" valor={dados.chave} obrigatorio />
    <Opcoes nome="tipo" titulo="Natureza da chave" valor={dados.tipo} itens={[["cpf", "CPF"], ["cnpj", "CNPJ"], ["email", "E-mail"], ["telefone", "Telefone"], ["aleatoria", "Aleatória"]]} />
    <Campo nome="titular" titulo="Titular" valor={dados.titular} obrigatorio />
    <Campo nome="banco" titulo="Banco" valor={dados.banco} />
    <Campo nome="agencia" titulo="Agência" valor={dados.agencia} />
    <Campo nome="conta" titulo="Conta" valor={dados.conta} />
    <Opcoes nome="tipo_conta" titulo="Tipo de conta" valor={dados.tipo_conta} itens={[["corrente", "Corrente"], ["poupanca", "Poupança"], ["pagamento", "Pagamento"]]} />
    <Opcoes nome="categoria" titulo="Categoria" valor={dados.categoria} itens={[["fixa", "Fixa"], ["temporaria", "Temporária"]]} />
    <Campo nome="validade" titulo="Validade" tipo="date" valor={dados.validade} />
    <label><input type="checkbox" name="principal" defaultChecked={dados.principal} /> Chave principal</label>
    <label><input type="checkbox" name="ativo" defaultChecked={dados.ativo} /> Ativa</label>
  </>;
}
const telefonePrincipal = (contato: Contato | undefined, pessoa: CadastroPessoa) => contato?.telefone ?? pessoa.telefone;
function ChaveCopiavel({ chave, cadastroAtivo }: { chave: ChavePix; cadastroAtivo: boolean }) {
  if (!cadastroAtivo || !chave.ativo || vencida(chave)) return <span><code>{chave.chave}</code><p style={{ color: "var(--warning)" }}>{!cadastroAtivo ? "Cadastro inativo" : !chave.ativo ? "Chave inativa" : "Chave vencida"} · indisponível para pagamento</p></span>;
  return <CopyKey value={chave.chave} />;
}
const documentoResumo = (pessoa: CadastroPessoa) => pessoa.documento || "Sem documento";
const papel = (tipo: string) => tipo === "ambos" ? "Cliente e fornecedor" : tipo === "fornecedor" ? "Fornecedor" : "Cliente / representante";
const dataHoje = () => {
  const partes = new Intl.DateTimeFormat("en", { timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  return ["year", "month", "day"].map(tipo => partes.find(p => p.type === tipo)?.value ?? "").join("-");
};
const vencida = (chave: ChavePix) => Boolean(chave.validade && chave.validade < dataHoje());
const chavePrincipal = (item: CadastroPessoa) => item.chaves_pix.find(c => c.principal && c.ativo) ?? item.chaves_pix.find(c => c.ativo);

function corresponde(item: CadastroPessoa, filtro: string, situacao: string, busca: string) {
  const papelCorreto = filtro === "todos" || item.tipo === filtro || (item.tipo === "ambos" && ["representante", "fornecedor"].includes(filtro));
  const estadoCorreto = situacao === "todos" || item.ativo === (situacao === "ativos");
  const texto = [item.nome, item.apelido, String(item.id), item.documento, ...item.chaves_pix.map(k => k.chave)].join(" ").toLocaleLowerCase("pt-BR");
  return papelCorreto && estadoCorreto && texto.includes(busca.trim().toLocaleLowerCase("pt-BR"));
}

export default function CadastroManager({ pessoas, filtroInicial, abaInicial, podeEditar, pessoaInicial, preferencia }: { pessoas: CadastroPessoa[]; filtroInicial: string; abaInicial: string; podeEditar: boolean; pessoaInicial: number | null; preferencia: PreferenciaTabela }) {
  const [busca, setBusca] = useState(valorSalvo(preferencia, "q", ""));
  const [filtro, setFiltro] = useState(valorSalvo(preferencia, "tipo", filtroInicial));
  const [situacao, setSituacao] = useState(situacaoCadastro(preferencia.filtros));
  const [selecionado, setSelecionado] = useState<number | null>(pessoaInicial);
  const [aba, setAba] = useState<AbaFicha>(abaInicial === "financeiro" ? "financeiro" : "dados");
  const p = pessoas.find(item => item.id === selecionado);
  const lista = ordenarCadastros(pessoas.filter(item => corresponde(item, filtro, situacao, busca)), preferencia);
  return <div className={styles.manager}>
    <header className={styles.header}>
      <div><h1>Cadastros</h1><p className="muted">Lista única de clientes, fornecedores e cadastros mistos.</p></div>
      <div className={styles.actions}><a className="btn-secondary" href="/intercambio">Importar / exportar</a>{podeEditar && <a className="btn" href="#novo-cadastro">Novo cadastro</a>}</div>
    </header>
    <AlertasInline pessoas={pessoas} />
    {podeEditar && <details id="novo-cadastro"><summary>Novo cadastro</summary><Editor operacao="pessoa" pessoaId={null} itemId={null}><Dados /></Editor></details>}
    <div className={styles.filters}>
      <label>Buscar<input value={busca} onChange={e => setBusca(e.target.value)} placeholder="Nome, ID, documento ou chave PIX" /></label>
      <label>Exibir<select value={filtro} onChange={e => setFiltro(e.target.value)}><option value="todos">Todos</option><option value="representante">Clientes</option><option value="fornecedor">Fornecedores</option><option value="ambos">Cliente e fornecedor</option></select></label>
      <label>Situação<select value={situacao} onChange={e => setSituacao(e.target.value)}><option value="ativos">Ativos</option><option value="inativos">Inativos</option><option value="todos">Todos</option></select></label>
    </div>
    <div className={styles.filterbar}><button type="button" className="secondary" onClick={() => { setBusca(""); setFiltro("todos"); setSituacao("todos"); }}>Limpar filtros</button><span className="muted">{lista.length} cadastro(s) encontrado(s)</span></div>
    <PreferenciasTabela key={JSON.stringify(preferencia)} tela="cadastros" preferencia={preferencia} filtros={filtrosCadastro(filtro, situacao, busca)} />
    <TabelaCadastros lista={lista} preferencia={preferencia} abrir={id => { setSelecionado(id); setAba("dados"); }} />
    {p && <section className={styles.sheet} aria-label={`Cadastro de ${p.nome}`}>
      <div className={styles.sheetHeader}>
        <div><p className="muted">Cadastro #{p.id}</p><h2>{p.nome}</h2><p>{papel(p.tipo)} · {p.ativo ? "Ativo" : "Inativo"}</p></div>
        <button className="secondary" onClick={() => setSelecionado(null)}>Fechar ficha</button>
      </div>
      <nav aria-label="Áreas da ficha" className={styles.tabs}><button className={aba === "dados" ? "" : "secondary"} onClick={() => setAba("dados")}>Dados</button><button className={aba === "financeiro" ? "" : "secondary"} onClick={() => setAba("financeiro")}>Financeiro</button><button className={aba === "dashboard" ? "" : "secondary"} onClick={() => setAba("dashboard")}>Dashboard</button></nav>
      {aba === "dados" && <AbaDados pessoa={p} podeEditar={podeEditar} />}
      {aba === "financeiro" && <AbaFinanceiro pessoa={p} podeEditar={podeEditar} />}
      {aba === "dashboard" && <AbaDashboard pessoa={p} />}
    </section>}
  </div>;
}

function AlertasInline({ pessoas }: { pessoas: CadastroPessoa[] }) {
  const semChave = pessoas.filter(p => p.ativo && ["fornecedor", "ambos"].includes(p.tipo) && !chavePrincipal(p)).length;
  const vencidas = pessoas.flatMap(p => p.chaves_pix).filter(c => c.ativo && vencida(c)).length;
  if (!semChave && !vencidas) return null;
  return <div className={styles.alerts}>{semChave > 0 && <span>{semChave} fornecedor(es) sem chave PIX principal.</span>}{vencidas > 0 && <span>{vencidas} chave(s) PIX vencida(s).</span>}</div>;
}

function AbaDados({ pessoa, podeEditar }: { pessoa: CadastroPessoa; podeEditar: boolean }) {
  return <div className={styles.panel}>
    {podeEditar ? <Editor key={`p${pessoa.id}-${pessoa.ativo}`} operacao="pessoa" pessoaId={pessoa.id} itemId={null}><Dados pessoa={pessoa} /></Editor> : <p>{papel(pessoa.tipo)} · {documentoResumo(pessoa)} · {pessoa.endereco || "Sem endereço"}</p>}
    <p className="muted">Cadastros com movimentação devem ser inativados, não apagados.</p><h3>Contatos e responsáveis</h3>
    {pessoa.contatos.map(c => <details key={JSON.stringify(c)}><summary>{c.nome} {c.principal ? "· Principal" : ""} {!c.ativo ? "· Inativo" : ""}</summary>{podeEditar ? <Editor operacao="contato" pessoaId={pessoa.id} itemId={c.id}><ContatoCampos contato={c} primeiro={false} /></Editor> : <p>{c.telefone} · {c.email} · {c.cargo}</p>}</details>)}
    {podeEditar && <details><summary>Adicionar contato</summary><Editor key={`novo-contato-${pessoa.id}-${pessoa.contatos.length}`} operacao="contato" pessoaId={pessoa.id} itemId={null}><ContatoCampos primeiro={!pessoa.contatos.some(c => c.ativo)} /></Editor></details>}
  </div>;
}

function AbaFinanceiro({ pessoa, podeEditar }: { pessoa: CadastroPessoa; podeEditar: boolean }) {
  return <div className={styles.panel}>
    <div className={styles.linksRow}><a href={`/notas?pessoa_id=${pessoa.id}&relacao=${relacaoExtrato(pessoa.tipo)}`}>Notas e extrato</a><a href={`/links?pessoa_id=${pessoa.id}`}>Links de pagamento</a><a href={`/extratos/${pessoa.id}?relacao=${relacaoExtrato(pessoa.tipo)}`}>Extrato consolidado</a></div>
    <p className="muted">A validade da chave não altera pagamentos já lançados.</p>
    {pessoa.chaves_pix.map(c => <details key={JSON.stringify(c)}><summary>{c.principal ? "★ " : ""}{c.tipo.toUpperCase()} {c.principal ? "· Principal" : ""} {!c.ativo ? "· Inativa" : vencida(c) ? "· Vencida" : ""}</summary><ChaveCopiavel chave={c} cadastroAtivo={pessoa.ativo} />{podeEditar ? <Editor operacao="chave" pessoaId={pessoa.id} itemId={c.id}><ChaveCampos chave={c} primeiro={false} /></Editor> : <p>{c.titular} · {c.banco} · Agência {c.agencia} · Conta {c.conta} · Validade {c.validade ?? "Sem vencimento"}</p>}</details>)}
    {pessoa.chaves_pix.length === 0 && <p>Nenhuma chave cadastrada.</p>}
    {podeEditar && <details><summary>Adicionar chave PIX</summary><Editor key={`nova-chave-${pessoa.id}-${pessoa.chaves_pix.length}`} operacao="chave" pessoaId={pessoa.id} itemId={null}><ChaveCampos primeiro={!pessoa.chaves_pix.some(c => c.ativo)} /></Editor></details>}
  </div>;
}

function AbaDashboard({ pessoa }: { pessoa: CadastroPessoa }) {
  const chave = chavePrincipal(pessoa);
  return <div className={styles.panel}>
    <div className={styles.summaryGrid}>
      <Resumo titulo="Status" valor={pessoa.ativo ? "Ativo" : "Inativo"} />
      <Resumo titulo="Chaves PIX" valor={String(pessoa.chaves_pix.length)} />
      <Resumo titulo="Contatos" valor={String(pessoa.contatos.length)} />
      <Resumo titulo="Prazo" valor={pessoa.prazo_dias ? `${pessoa.prazo_dias} dias` : "Sem prazo"} />
    </div>
    <h3>Visão compartilhável</h3>
    <p className="muted">Primeira versão: centraliza os atalhos. Permissões finas e seleção de dados visíveis entram depois.</p>
    <div className={styles.linksRow}><a href={`/extratos/${pessoa.id}?relacao=${relacaoExtrato(pessoa.tipo)}`}>Abrir dashboard do cadastro</a><a href={`/links?pessoa_id=${pessoa.id}`}>Gerenciar links</a></div>
    <h3>Resumo financeiro</h3>
    <ul className={styles.cleanList}><li>Débitos em aberto: consultar em notas e extrato.</li><li>Créditos em aberto: consultar em créditos e pagamentos.</li><li>Chave principal: {chave ? <ChaveCopiavel chave={chave} cadastroAtivo={pessoa.ativo} /> : "sem chave ativa"}</li></ul>
  </div>;
}
function Resumo({ titulo, valor }: { titulo: string; valor: string }) { return <div className={styles.summary}><span>{titulo}</span><strong>{valor}</strong></div>; }

function relacaoExtrato(tipo: string) { return tipo === "fornecedor" ? "fornecedor" : "cliente"; }

function TabelaCadastros({ lista, preferencia, abrir }: { lista: CadastroPessoa[]; preferencia: PreferenciaTabela; abrir: (id: number) => void }) { const colunas = preferencia.colunas.filter(c => c.visivel); return <div className="tablewrap"><table><thead><tr>{colunas.map(c => <th key={c.campo}>{rotulosColunas[c.campo]}</th>)}<th>WhatsApp</th><th>Chave principal</th><th>Ação</th></tr></thead><tbody>{lista.map(item => <tr key={item.id}>{colunas.map(c => <td key={c.campo} data-label={rotulosColunas[c.campo]}><CelulaCadastro item={item} campo={c.campo} /></td>)}<td data-label="WhatsApp"><button type="button" className="secondary" disabled title="Funcionalidade reservada para fase futura">WhatsApp</button></td><td data-label="Chave principal"><ChaveDaTabela item={item} /></td><td data-label="Ação"><button type="button" className="secondary" onClick={() => abrir(item.id)}>Abrir ficha</button></td></tr>)}{!lista.length && <tr><td colSpan={colunas.length + 3}>Nenhum cadastro corresponde aos filtros.</td></tr>}</tbody></table></div>; }
function ChaveDaTabela({ item }: { item: CadastroPessoa }) { const chave = chavePrincipal(item); return chave ? <ChaveCopiavel chave={chave} cadastroAtivo={item.ativo} /> : <span className="badge">Sem chave principal ativa</span>; }
function CelulaCadastro({ item, campo }: { item: CadastroPessoa; campo: string }) { if (campo === "nome") return <>#{item.id} · {item.nome}</>; if (campo === "tipo") return papel(item.tipo); if (campo === "ativo") return item.ativo ? "Ativo" : "Inativo"; if (campo === "telefone") return <TelefoneTabela item={item} />; if (campo === "email") return item.contatos.find(c => c.principal && c.ativo)?.email || item.email || "-"; return item[campo as "documento" | "prazo_dias"]; }
function TelefoneTabela({ item }: { item: CadastroPessoa }) { const contato = item.contatos.find(c => c.principal && c.ativo); const telefone = telefonePrincipal(contato, item).replace(/\D/g, ""); return <>{contato?.nome || "-"}{telefone && <><br /><a href={`tel:${telefone}`} target="_blank" rel="noreferrer">Telefone</a></>}</>; }

function valorSalvo(preferencia: PreferenciaTabela, campo: string, padrao: string) { return String(preferencia.filtros[campo] ?? padrao); }
