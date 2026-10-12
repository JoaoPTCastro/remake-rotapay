"use client";

import { useMemo, useRef, useState } from "react";
import {
  ArrowUpDown,
  BarChart3,
  Building2,
  Columns3,
  Download,
  Edit3,
  Filter,
  KeyRound,
  Link2,
  MessageCircle,
  Plus,
  Search,
  Upload,
  UserRound,
  X,
} from "lucide-react";
import { salvarCadastro } from "../../../lib/cadastro-actions";
import type { CadastroPessoa, ChavePix, Contato } from "../../../lib/cadastro-types";
import PreferenciasTabela from "../../../components/PreferenciasTabela";
import CopyKey from "../../../components/CopyKey";
import { filtrosCadastro, ordenarCadastros, situacaoCadastro } from "../../../lib/cadastro-tabela";
import { rotulosColunas, type PreferenciaTabela } from "../../../lib/configuracoes-types";
import styles from "./CadastroManager.module.css";

type AbaFicha = "dados" | "financeiro" | "dashboard";
type Operacao = "pessoa" | "contato" | "chave";

function Campo({ nome, titulo, valor, tipo = "text", obrigatorio = false }: { nome: string; titulo: string; valor?: string | number | null; tipo?: string; obrigatorio?: boolean }) {
  return (
    <label>
      <span>{titulo}{obrigatorio ? " *" : ""}</span>
      <input name={nome} type={tipo} defaultValue={valor ?? ""} required={obrigatorio} min={tipo === "number" ? 0 : undefined} step={nome === "tolerancia_credito" ? "0.01" : undefined} />
    </label>
  );
}

function Opcoes({ nome, titulo, valor, itens }: { nome: string; titulo: string; valor: string; itens: [string, string][] }) {
  return (
    <label>
      <span>{titulo}</span>
      <select name={nome} defaultValue={valor}>{itens.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select>
    </label>
  );
}

function Editor({ operacao, pessoaId, itemId, children, onSaved }: { operacao: Operacao; pessoaId: number | null; itemId: number | null; children: React.ReactNode; onSaved?: () => void }) {
  const formRef = useRef<HTMLFormElement>(null);
  const [estado, setEstado] = useState<{ ok: boolean; mensagem: string } | null>(null);
  const [enviando, setEnviando] = useState(false);

  return (
    <form
      ref={formRef}
      className={styles.editorGrid}
      action={async (form) => {
        setEnviando(true);
        try {
          const resultado = await salvarCadastro(operacao, pessoaId, itemId, form);
          setEstado(resultado);
          if (resultado.ok && (operacao === "pessoa" ? pessoaId === null : itemId === null)) formRef.current?.reset();
          if (resultado.ok) onSaved?.();
        } finally {
          setEnviando(false);
        }
      }}
    >
      {children}
      <div className={styles.full}>
        <button disabled={enviando}>{enviando ? "Salvando..." : "Salvar"}</button>
        {estado && <p role={estado.ok ? "status" : "alert"} className={estado.ok ? "pos" : "neg"}>{estado.mensagem}</p>}
      </div>
    </form>
  );
}

function Dados({ pessoa }: { pessoa?: CadastroPessoa }) {
  const dados = pessoa ?? { nome: "", tipo: "representante", documento: "", apelido: "", endereco: "", prazo_dias: 0, prioridade: 2, tolerancia_credito: 0, observacoes: "" };
  return (
    <>
      <Campo nome="nome" titulo="Nome / razao social" valor={dados.nome} obrigatorio />
      <Opcoes nome="tipo" titulo="Papel no cadastro" valor={dados.tipo} itens={[["representante", "Cliente / representante"], ["fornecedor", "Fornecedor"], ["ambos", "Cliente e fornecedor"]]} />
      <Campo nome="documento" titulo="CPF/CNPJ" valor={dados.documento} />
      <Campo nome="apelido" titulo="Apelido" valor={dados.apelido} />
      <Campo nome="endereco" titulo="Endereco" valor={dados.endereco} />
      <Campo nome="prazo_dias" titulo="Prazo em dias" valor={dados.prazo_dias} tipo="number" />
      <Opcoes nome="prioridade" titulo="Prioridade" valor={String(dados.prioridade)} itens={[["1", "Alta"], ["2", "Normal"], ["3", "Baixa"]]} />
      <Campo nome="tolerancia_credito" titulo="Tolerancia de credito (R$)" valor={dados.tolerancia_credito} tipo="number" />
      <Campo nome="observacoes" titulo="Observacoes" valor={dados.observacoes} />
      {pessoa && <label className={styles.checkLabel}><input type="checkbox" name="ativo" defaultChecked={pessoa.ativo} /> Cadastro ativo</label>}
    </>
  );
}

function ContatoCampos({ contato, primeiro }: { contato?: Contato; primeiro: boolean }) {
  return (
    <>
      <Campo nome="nome" titulo="Nome do contato" valor={contato?.nome} obrigatorio />
      <Campo nome="cargo" titulo="Cargo / responsabilidade" valor={contato?.cargo} />
      <Campo nome="telefone" titulo="Telefone com DDI e DDD" valor={contato?.telefone} />
      <Campo nome="email" titulo="E-mail" tipo="email" valor={contato?.email} />
      <label className={styles.checkLabel}><input type="checkbox" name="principal" defaultChecked={contato?.principal ?? primeiro} /> Contato principal</label>
      <label className={styles.checkLabel}><input type="checkbox" name="ativo" defaultChecked={contato?.ativo ?? true} /> Ativo</label>
    </>
  );
}

function ChaveCampos({ chave, primeiro }: { chave?: ChavePix; primeiro: boolean }) {
  const dados = chave ?? { chave: "", tipo: "aleatoria", titular: "", banco: "", agencia: "", conta: "", tipo_conta: "corrente", categoria: "fixa", validade: null, principal: primeiro, ativo: true };
  return (
    <>
      <Campo nome="chave" titulo="Chave PIX" valor={dados.chave} obrigatorio />
      <Opcoes nome="tipo" titulo="Natureza da chave" valor={dados.tipo} itens={[["cpf", "CPF"], ["cnpj", "CNPJ"], ["email", "E-mail"], ["telefone", "Telefone"], ["aleatoria", "Aleatoria"]]} />
      <Campo nome="titular" titulo="Titular" valor={dados.titular} obrigatorio />
      <Campo nome="banco" titulo="Banco" valor={dados.banco} />
      <Campo nome="agencia" titulo="Agencia" valor={dados.agencia} />
      <Campo nome="conta" titulo="Conta" valor={dados.conta} />
      <Opcoes nome="tipo_conta" titulo="Tipo de conta" valor={dados.tipo_conta} itens={[["corrente", "Corrente"], ["poupanca", "Poupanca"], ["pagamento", "Pagamento"]]} />
      <Opcoes nome="categoria" titulo="Categoria" valor={dados.categoria} itens={[["fixa", "Fixa"], ["temporaria", "Temporaria"]]} />
      <Campo nome="validade" titulo="Validade" tipo="date" valor={dados.validade} />
      <label className={styles.checkLabel}><input type="checkbox" name="principal" defaultChecked={dados.principal} /> Chave principal</label>
      <label className={styles.checkLabel}><input type="checkbox" name="ativo" defaultChecked={dados.ativo} /> Ativa</label>
    </>
  );
}

const papel = (tipo: string) => tipo === "ambos" ? "Cliente e fornecedor" : tipo === "fornecedor" ? "Fornecedor" : "Cliente / representante";
const documentoResumo = (pessoa: CadastroPessoa) => pessoa.documento || "Sem documento";
const telefonePrincipal = (contato: Contato | undefined, pessoa: CadastroPessoa) => contato?.telefone ?? pessoa.telefone;
const dataHoje = () => {
  const partes = new Intl.DateTimeFormat("en", { timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  return ["year", "month", "day"].map((tipo) => partes.find((p) => p.type === tipo)?.value ?? "").join("-");
};
const vencida = (chave: ChavePix) => Boolean(chave.validade && chave.validade < dataHoje());
const chavePrincipal = (item: CadastroPessoa) => item.chaves_pix.find((c) => c.principal && c.ativo) ?? item.chaves_pix.find((c) => c.ativo);

function corresponde(item: CadastroPessoa, filtro: string, situacao: string, busca: string) {
  const papelCorreto = filtro === "todos" || item.tipo === filtro || (item.tipo === "ambos" && ["representante", "fornecedor"].includes(filtro));
  const estadoCorreto = situacao === "todos" || item.ativo === (situacao === "ativos");
  const texto = [item.nome, item.apelido, String(item.id), item.documento, item.telefone, ...item.contatos.map((c) => `${c.nome} ${c.telefone} ${c.email}`), ...item.chaves_pix.map((k) => k.chave)].join(" ").toLocaleLowerCase("pt-BR");
  return papelCorreto && estadoCorreto && texto.includes(busca.trim().toLocaleLowerCase("pt-BR"));
}

function ChaveCopiavel({ chave, cadastroAtivo }: { chave: ChavePix; cadastroAtivo: boolean }) {
  if (!cadastroAtivo || !chave.ativo || vencida(chave)) {
    return <span className={styles.blockedKey}>{!cadastroAtivo ? "Cadastro inativo" : !chave.ativo ? "Chave inativa" : "Chave vencida"}</span>;
  }
  return <CopyKey value={chave.chave} />;
}

export default function CadastroManager({ pessoas, filtroInicial, abaInicial, podeEditar, pessoaInicial, preferencia }: { pessoas: CadastroPessoa[]; filtroInicial: string; abaInicial: string; podeEditar: boolean; pessoaInicial: number | null; preferencia: PreferenciaTabela }) {
  const [busca, setBusca] = useState(valorSalvo(preferencia, "q", ""));
  const [filtro, setFiltro] = useState(valorSalvo(preferencia, "tipo", filtroInicial));
  const [situacao, setSituacao] = useState(situacaoCadastro(preferencia.filtros));
  const [selecionado, setSelecionado] = useState<number | null>(pessoaInicial);
  const [aba, setAba] = useState<AbaFicha>(abaInicial === "financeiro" ? "financeiro" : "dados");
  const [filterOpen, setFilterOpen] = useState(false);
  const [columnsOpen, setColumnsOpen] = useState(false);
  const [newOpen, setNewOpen] = useState(false);

  const lista = useMemo(() => ordenarCadastros(pessoas.filter((item) => corresponde(item, filtro, situacao, busca)), preferencia), [busca, filtro, pessoas, preferencia, situacao]);
  const pessoa = pessoas.find((item) => item.id === selecionado);
  const totalFornecedores = pessoas.filter((item) => item.tipo === "fornecedor" || item.tipo === "ambos").length;
  const totalSemChave = pessoas.filter((item) => !chavePrincipal(item)).length;
  const filtrosAtuais = filtrosCadastro(filtro, situacao, busca);

  function limparFiltros() {
    setBusca("");
    setFiltro("todos");
    setSituacao("todos");
  }

  return (
    <div className={styles.manager}>
      <section className={styles.hero}>
        <div>
          <p className={styles.kicker}>RotaPay · Cadastros</p>
          <h1>Cadastros</h1>
          <p className="muted">Clientes, fornecedores, contatos e chaves PIX no mesmo fluxo operacional.</p>
        </div>
        <div className={styles.heroActions}>
          <a className="btn-secondary" href="/intercambio"><Upload size={16} /> Importar</a>
          <a className="btn-secondary" href="/intercambio"><Download size={16} /> Exportar</a>
          {podeEditar && <button type="button" onClick={() => setNewOpen(true)}><Plus size={16} /> Novo cadastro</button>}
        </div>
      </section>

      <section className={styles.cards} aria-label="Resumo dos cadastros">
        <Resumo titulo="Total de cadastros" valor={String(pessoas.length)} />
        <Resumo titulo="Fornecedores" valor={String(totalFornecedores)} />
        <Resumo titulo="Sem chave principal" valor={String(totalSemChave)} />
      </section>

      <AlertasInline pessoas={pessoas} />

      <section className={styles.toolbar} aria-label="Busca e filtros de cadastros">
        <div className={styles.toolbarLeft}>
          <label className={styles.search}>
            <Search size={16} />
            <input aria-label="Buscar cadastros" value={busca} onChange={(event) => setBusca(event.target.value)} placeholder="Buscar cadastros..." />
            {busca && <button type="button" className="iconbtn" aria-label="Limpar busca" onClick={() => setBusca("")}><X size={14} /></button>}
          </label>
          <div className={styles.popoverWrap}>
            <button type="button" className="btn-secondary" onClick={() => setFilterOpen((open) => !open)}><Filter size={16} /> Filtros</button>
            {filterOpen && (
              <div className={styles.popover}>
                <div className={styles.popoverTitle}>
                  <div><h2>Filtrar cadastros</h2><p className="muted">A lista atualiza sem alterar dados.</p></div>
                  <button type="button" className="iconbtn" aria-label="Fechar filtros" onClick={() => setFilterOpen(false)}><X size={16} /></button>
                </div>
                <label>
                  <span>Papel</span>
                  <select value={filtro} onChange={(event) => setFiltro(event.target.value)}>
                    <option value="todos">Todos</option><option value="representante">Clientes</option><option value="fornecedor">Fornecedores</option><option value="ambos">Cliente e fornecedor</option>
                  </select>
                </label>
                <label>
                  <span>Situacao</span>
                  <select value={situacao} onChange={(event) => setSituacao(event.target.value)}>
                    <option value="ativos">Ativos</option><option value="inativos">Inativos</option><option value="todos">Todos</option>
                  </select>
                </label>
                <button type="button" className="secondary" onClick={limparFiltros}>Limpar filtros</button>
              </div>
            )}
          </div>
        </div>
        <div className={styles.toolbarRight}>
          <button type="button" className="btn-secondary" onClick={() => setColumnsOpen(true)}><Columns3 size={16} /> Colunas e ordem</button>
          <span className={styles.statusLine}>{lista.length} de {pessoas.length} cadastro(s)</span>
        </div>
      </section>

      <section className={styles.tableCard}>
        <div className={styles.tableHeader}>
          <div><h2>Lista de cadastros</h2><p className="muted">Abra a ficha para editar dados, contatos e chaves.</p></div>
        </div>
        <TabelaCadastros lista={lista} preferencia={preferencia} abrir={(id) => { setSelecionado(id); setAba("dados"); }} />
      </section>

      {pessoa && <FichaCadastro pessoa={pessoa} aba={aba} setAba={setAba} podeEditar={podeEditar} onClose={() => setSelecionado(null)} />}

      {newOpen && (
        <Modal title="Novo cadastro" onClose={() => setNewOpen(false)}>
          <Editor operacao="pessoa" pessoaId={null} itemId={null} onSaved={() => setNewOpen(false)}><Dados /></Editor>
        </Modal>
      )}

      {columnsOpen && (
        <Modal title="Colunas, ordenacao e filtros" onClose={() => setColumnsOpen(false)}>
          <PreferenciasTabela tela="cadastros" preferencia={preferencia} filtros={filtrosAtuais} />
        </Modal>
      )}
    </div>
  );
}

function AlertasInline({ pessoas }: { pessoas: CadastroPessoa[] }) {
  const semChave = pessoas.filter((p) => p.ativo && ["fornecedor", "ambos"].includes(p.tipo) && !chavePrincipal(p)).length;
  const vencidas = pessoas.flatMap((p) => p.chaves_pix).filter((c) => c.ativo && vencida(c)).length;
  if (!semChave && !vencidas) return null;
  return <div className={styles.alerts}>{semChave > 0 && <span>{semChave} fornecedor(es) sem chave PIX principal.</span>}{vencidas > 0 && <span>{vencidas} chave(s) PIX vencida(s).</span>}</div>;
}

function FichaCadastro({ pessoa, aba, setAba, podeEditar, onClose }: { pessoa: CadastroPessoa; aba: AbaFicha; setAba: (aba: AbaFicha) => void; podeEditar: boolean; onClose: () => void }) {
  return (
    <>
      <button className={styles.drawerBackdrop} aria-label="Fechar ficha" onClick={onClose} />
      <aside className={styles.drawer} aria-label={`Cadastro de ${pessoa.nome}`}>
        <header className={styles.drawerHead}>
          <div><span className={styles.idTag}>#{pessoa.id}</span><h2>{pessoa.nome}</h2><p className="muted">{papel(pessoa.tipo)} · {documentoResumo(pessoa)}</p></div>
          <button type="button" className="iconbtn" aria-label="Fechar ficha" onClick={onClose}><X size={18} /></button>
        </header>
        <div className={styles.drawerBody}>
          <nav className={styles.quickLinks} aria-label="Atalhos do cadastro">
            <a className="btn-secondary" href={`/notas?pessoa_id=${pessoa.id}&relacao=${relacaoExtrato(pessoa.tipo)}`}>Notas</a>
            <a className="btn-secondary" href={`/extratos/${pessoa.id}?relacao=${relacaoExtrato(pessoa.tipo)}`}>Extrato</a>
            <a className="btn-secondary" href={`/links?pessoa_id=${pessoa.id}`}>Links</a>
          </nav>
          <nav className={styles.tabs} aria-label="Areas da ficha">
            <button className={aba === "dados" ? "" : "secondary"} onClick={() => setAba("dados")}><UserRound size={16} /> Dados</button>
            <button className={aba === "financeiro" ? "" : "secondary"} onClick={() => setAba("financeiro")}><KeyRound size={16} /> Financeiro</button>
            <button className={aba === "dashboard" ? "" : "secondary"} onClick={() => setAba("dashboard")}><BarChart3 size={16} /> Dashboard</button>
          </nav>
          {aba === "dados" && <AbaDados pessoa={pessoa} podeEditar={podeEditar} />}
          {aba === "financeiro" && <AbaFinanceiro pessoa={pessoa} podeEditar={podeEditar} />}
          {aba === "dashboard" && <AbaDashboard pessoa={pessoa} />}
        </div>
      </aside>
    </>
  );
}

function AbaDados({ pessoa, podeEditar }: { pessoa: CadastroPessoa; podeEditar: boolean }) {
  return (
    <div className={styles.panel}>
      {podeEditar ? <Editor key={`p${pessoa.id}-${pessoa.ativo}`} operacao="pessoa" pessoaId={pessoa.id} itemId={null}><Dados pessoa={pessoa} /></Editor> : <p>{papel(pessoa.tipo)} · {documentoResumo(pessoa)} · {pessoa.endereco || "Sem endereco"}</p>}
      <p className="muted">Cadastros com movimentacao devem ser inativados, nao apagados.</p>
      <section className={styles.sectionBlock}>
        <h3>Contatos e responsaveis</h3>
        {pessoa.contatos.map((c) => <details className={styles.subCard} key={JSON.stringify(c)}><summary>{c.nome} {c.principal ? "· Principal" : ""} {!c.ativo ? "· Inativo" : ""}</summary>{podeEditar ? <Editor operacao="contato" pessoaId={pessoa.id} itemId={c.id}><ContatoCampos contato={c} primeiro={false} /></Editor> : <p>{c.telefone} · {c.email} · {c.cargo}</p>}</details>)}
        {podeEditar && <details className={styles.subCard}><summary>Adicionar contato</summary><Editor key={`novo-contato-${pessoa.id}-${pessoa.contatos.length}`} operacao="contato" pessoaId={pessoa.id} itemId={null}><ContatoCampos primeiro={!pessoa.contatos.some((c) => c.ativo)} /></Editor></details>}
      </section>
    </div>
  );
}

function AbaFinanceiro({ pessoa, podeEditar }: { pessoa: CadastroPessoa; podeEditar: boolean }) {
  return (
    <div className={styles.panel}>
      <p className="muted">A validade da chave nao altera pagamentos ja lancados.</p>
      <section className={styles.sectionBlock}>
        {pessoa.chaves_pix.map((c) => <details className={styles.subCard} key={JSON.stringify(c)}><summary>{c.principal ? "★ " : ""}{c.tipo.toUpperCase()} {c.principal ? "· Principal" : ""} {!c.ativo ? "· Inativa" : vencida(c) ? "· Vencida" : ""}</summary><ChaveCopiavel chave={c} cadastroAtivo={pessoa.ativo} />{podeEditar ? <Editor operacao="chave" pessoaId={pessoa.id} itemId={c.id}><ChaveCampos chave={c} primeiro={false} /></Editor> : <p>{c.titular} · {c.banco} · Agencia {c.agencia} · Conta {c.conta} · Validade {c.validade ?? "Sem vencimento"}</p>}</details>)}
        {pessoa.chaves_pix.length === 0 && <p>Nenhuma chave cadastrada.</p>}
        {podeEditar && <details className={styles.subCard}><summary>Adicionar chave PIX</summary><Editor key={`nova-chave-${pessoa.id}-${pessoa.chaves_pix.length}`} operacao="chave" pessoaId={pessoa.id} itemId={null}><ChaveCampos primeiro={!pessoa.chaves_pix.some((c) => c.ativo)} /></Editor></details>}
      </section>
    </div>
  );
}

function AbaDashboard({ pessoa }: { pessoa: CadastroPessoa }) {
  const chave = chavePrincipal(pessoa);
  return (
    <div className={styles.dashboardPanel}>
      <div className={styles.shareBox}>
        <div><h3>Resumo compartilhavel</h3><p className="muted">Base visual para o painel do cliente ou fornecedor.</p></div>
        <a className="btn-secondary" href={`/extratos/${pessoa.id}?relacao=${relacaoExtrato(pessoa.tipo)}`}><Link2 size={16} /> Abrir link</a>
      </div>
      <div className={styles.metricGrid}>
        <Resumo titulo="Status" valor={pessoa.ativo ? "Ativo" : "Inativo"} />
        <Resumo titulo="Chaves PIX" valor={String(pessoa.chaves_pix.length)} />
        <Resumo titulo="Contatos" valor={String(pessoa.contatos.length)} />
        <Resumo titulo="Prazo" valor={pessoa.prazo_dias ? `${pessoa.prazo_dias} dias` : "Sem prazo"} />
      </div>
      <div className={styles.placeholderList}><h3>Resumo financeiro</h3><p>Debitos em aberto, creditos recebidos, anexos e permissoes do link entram aqui quando validarmos os dados.</p><p>Chave principal: {chave ? <ChaveCopiavel chave={chave} cadastroAtivo={pessoa.ativo} /> : "sem chave ativa"}</p></div>
    </div>
  );
}

function Resumo({ titulo, valor }: { titulo: string; valor: string }) {
  return <div className={styles.summary}><span>{titulo}</span><strong>{valor}</strong></div>;
}

function TabelaCadastros({ lista, preferencia, abrir }: { lista: CadastroPessoa[]; preferencia: PreferenciaTabela; abrir: (id: number) => void }) {
  const colunas = preferencia.colunas.filter((c) => c.visivel);
  return (
    <div className="tablewrap">
      <table className={styles.cadastroTable}>
        <thead><tr>{colunas.map((c) => <th key={c.campo}>{rotulosColunas[c.campo]} <SortHint /></th>)}<th>WhatsApp</th><th>Chave principal</th><th>Acoes</th></tr></thead>
        <tbody>
          {lista.map((item) => <tr key={item.id}>{colunas.map((c) => <td key={c.campo} data-label={rotulosColunas[c.campo]}><CelulaCadastro item={item} campo={c.campo} /></td>)}<td data-label="WhatsApp"><WhatsAppCell item={item} /></td><td data-label="Chave principal"><ChaveDaTabela item={item} /></td><td data-label="Acoes"><button type="button" className="secondary" onClick={() => abrir(item.id)}><Edit3 size={15} /> Editar</button></td></tr>)}
          {!lista.length && <tr><td colSpan={colunas.length + 3}><div className={styles.empty}><Search size={22} /><p>Nenhum cadastro encontrado</p><p className="muted">Ajuste a busca ou limpe os filtros.</p></div></td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function SortHint() {
  return <ArrowUpDown size={13} aria-hidden="true" />;
}

function ChaveDaTabela({ item }: { item: CadastroPessoa }) {
  const chave = chavePrincipal(item);
  return chave ? <span className={styles.pixCell}><span className={styles.pixValue}>Chave principal</span><ChaveCopiavel chave={chave} cadastroAtivo={item.ativo} /></span> : <span className="badge">Sem chave principal ativa</span>;
}

function CelulaCadastro({ item, campo }: { item: CadastroPessoa; campo: string }) {
  if (campo === "nome") return <span className={styles.nameCell}><span className={styles.idTag}>#{item.id}</span><strong>{item.nome}</strong>{item.apelido && <span className="muted">{item.apelido}</span>}</span>;
  if (campo === "tipo") { const Icon = item.tipo === "fornecedor" ? Building2 : UserRound; return <span className={styles.typeBadge}><Icon size={13} /> {papel(item.tipo)}</span>; }
  if (campo === "ativo") return <span className={`${styles.statusBadge} ${item.ativo ? "" : styles.inactive}`}>{item.ativo ? "Ativo" : "Inativo"}</span>;
  if (campo === "telefone") return <TelefoneTabela item={item} />;
  if (campo === "email") return item.contatos.find((c) => c.principal && c.ativo)?.email || item.email || "-";
  return item[campo as "documento" | "prazo_dias"] || "-";
}

function TelefoneTabela({ item }: { item: CadastroPessoa }) {
  const contato = item.contatos.find((c) => c.principal && c.ativo);
  const telefoneBruto = telefonePrincipal(contato, item);
  const telefone = telefoneBruto.replace(/\D/g, "");
  if (!telefone) return <span className="muted">Sem telefone</span>;
  return <span>{contato?.nome || formatPhone(telefone)}</span>;
}

function WhatsAppCell({ item }: { item: CadastroPessoa }) {
  const contato = item.contatos.find((c) => c.principal && c.ativo);
  const telefone = telefonePrincipal(contato, item).replace(/\D/g, "");
  if (!telefone) return <span className="muted">Indisponivel</span>;
  return <a className={styles.phoneLink} href={`https://wa.me/${telefone}`} target="_blank" rel="noreferrer"><span className={styles.iconBubble}><MessageCircle size={16} /></span></a>;
}

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <>
      <button className={styles.modalBackdrop} aria-label="Fechar janela" onClick={onClose} />
      <section className={styles.modal} role="dialog" aria-modal="true" aria-label={title}>
        <header className={styles.modalHead}><div><h2>{title}</h2><p className="muted">Preencha os dados e salve para atualizar o cadastro.</p></div><button type="button" className="iconbtn" aria-label="Fechar janela" onClick={onClose}><X size={18} /></button></header>
        <div className={styles.modalBody}>{children}</div>
      </section>
    </>
  );
}

function relacaoExtrato(tipo: string) {
  return tipo === "fornecedor" ? "fornecedor" : "cliente";
}

function valorSalvo(preferencia: PreferenciaTabela, campo: string, padrao: string) {
  return String(preferencia.filtros[campo] ?? padrao);
}

function formatPhone(phone: string) {
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 13 && digits.startsWith("55")) return `(${digits.slice(2, 4)}) ${digits.slice(4, 9)}-${digits.slice(9)}`;
  if (digits.length === 11) return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
  return phone;
}
