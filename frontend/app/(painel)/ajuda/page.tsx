import {
  Sparkles, Banknote, ClipboardCheck, ArrowLeftRight, BookUser, Link2,
   ChartCandlestick, HandCoins, History,  Map,
  Lightbulb, ShieldCheck, HelpCircle, Rocket, Users, Gauge,
} from "lucide-react";

const ROTEIRO = [
  { n: "01", t: "Cadastre um fornecedor com chave PIX", d: "A base de tudo. Sem fornecedor com chave, você não consegue gerar link de pagamento.", href: "/cadastro", o: "Fornecedores → preencha nome, CNPJ/CPF e a chave PIX com banco e titular. Marque o prazo em dias e a tolerância se quiser permitir crédito." },
  { n: "02", t: "Cadastre as pessoas (clientes e rifeiros)", d: "Todo mundo que paga ou recebe no nome da loja.", href: "/cadastro", o: "Abra a aba Pessoas e cadastre clientes/rifeiros com telefone e e-mail. Se for vendedor que receberá link da Checkto, email/telefone/documento são obrigatórios." },
  { n: "03", t: "Registre o primeiro PIX", d: "Leva menos de 30 segundos e já nasce pronto para conciliar.", href: "/movimentacoes", o: "PIX → preencha data, valor, remetente (quem pagou), representante e fornecedor de destino. Preencha também o autor (quem lançou) — aparece no Controle." },
  { n: "04", t: "Gere o link do vendedor", d: "Com valor fixo, o link vira QR de cobrança real na Checkto.", href: "/links", o: "Links → escolha o vendedor e a chave do fornecedor. Com valor fixo + vendedor completo, clique em “Gerar cobrança PIX”. Ao pagar, o sistema registra sozinho." },
  { n: "05", t: "Concilie o valor com a obrigação", d: "Diga qual dívida aquele PIX quitou.", href: "/conciliacoes", o: "No Controle, aperte Conciliar na linha (ou em Conciliar → escolha Débito/Projeção). O sistema mostra o saldo restante e recusa excedente acima da tolerância." },
  { n: "06", t: "Crie projeções e acompanhe o futuro", d: "Planeje o que vai pagar para cada fornecedor.", href: "/projecoes", o: "Projeções → crie uma por Representante + Fornecedor e use o Simulador para saber quanto o rifeiro pode pagar sem estourar a dívida." },
];

const MODULOS: { id: string; icone: React.ReactNode; t: string; conteudo: React.ReactNode[] }[] = [
  {
    id: "inicio", icone: <Sparkles size={18} />, t: "Início (dashboard)",
    conteudo: [
      <>Veja sua situação financeira de uma olhada: total a pagar, PIX disponível, pendentes e conciliados, projeções abertas.</>,
      <>No topo fica o <strong>Acesso rápido</strong> com as 5 ações do dia a dia (Registrar PIX, Controle, Gerar link, Cadastrar, Conciliar).</>,
      <>Abaixo, três quadros: <strong>Valores por fornecedor</strong> (com a última compra), <strong>Últimas saídas</strong> e <strong>PIX gerados pelos links</strong>. Cada um mostra 8 itens — use <strong>Ver mais</strong> para expandir sem sair da página.</>,
      <>No meio fica a seção <strong>Insights</strong>: avisos prontos do sistema (PIX parados, comprovantes aguardando, obrigações abertas, pagamentos previstos) em linguagem simples. Cada card tem um <strong>link direto</strong> para a tela que resolve a pendência — é só clicar.</>,
      <>Dica: o botão <strong>Exportar posição CSV</strong> baixa a posição dos fornecedores em Excel.</>,
    ],
  },
  {
    id: "pix", icone: <Banknote size={18} />, t: "PIX — registro rápido",
    conteudo: [
      <>Esta tela serve para <strong>registrar entradas rápido</strong>: data, valor, remetente (quem pagou), representante, fornecedor, autor, forma de pagamento, natureza e observação. Ao salvar, o sistema <strong>abre o detalhe do PIX</strong> na hora.</>,
      <>Para <strong>consultar, filtrar, exportar ou conciliar</strong>, use o <a href="/controle">Controle</a> — esta tela não vira planilha, para não atrapalhar o registro.</>,
      <>Se o PIX for igual a outro já registrado (mesmo fornecedor, mesmo valor e mesma data), o sistema <strong>marca como possível duplicidade</strong> para você conferir — nada é bloqueado nem lançado sozinho.</>,
      <>No <strong>detalhe</strong> do PIX você anexa o comprovante (arrastando o arquivo), baixa o que já está anexado e pode cancelar (exclusão lógica) — cancelar exige sua senha.</>,
    ],
  },
  {
    id: "cadastro", icone: <BookUser size={18} />, t: "Cadastro — fornecedores, pessoas e chaves",
    conteudo: [
      <>Três abas em uma tela só: <strong>Fornecedores</strong>, <strong>Pessoas</strong> e <strong>Chaves PIX</strong>.</>,
      <>No fornecedor, cadastre a <strong>chave PIX</strong> (e-mail, CPF, CNPJ, telefone ou EVP), banco, titular, prazo em dias, tolerância de crédito e <strong>prioridade de pagamento</strong> (alta/normal/baixa — base do rodízio).</>,
      <>O cadastro é em <strong>3 etapas</strong> (quem é → contato → pagamento); a etapa de pagamento só aparece para fornecedor.</>,
      <>Sem chave cadastrada, o fornecedor não aparece na hora de gerar link — o sistema avisa em vez de deixar quebrar.</>,
    ],
  },
  {
    id: "controle", icone: <ClipboardCheck size={18} />, t: "Controle de saídas",
    conteudo: [
      <>É a sua planilha viva: cliente, data, valor, autor, remetente, fornecedor de destino, forma, natureza e a coluna de <strong>conciliação</strong> (☐ pendente, ◐ parcial, ☑ conciliada, ✕ cancelada).</>,
      <>Use a <strong>busca</strong> por código ou remetente e os <strong>filtros</strong> por cliente, fornecedor, status, período, <strong>chave PIX</strong> e <strong>com/sem link</strong>. A <strong>exportação CSV</strong> respeita os filtros aplicados.</>,
      <>A linha com saldo mostra o botão <strong>Conciliar</strong>, que já leva o PIX selecionado para a tela certa. As demais abrem o <strong>detalhe</strong> do PIX.</>,
    ],
  },
  {
    id: "conciliar", icone: <ArrowLeftRight size={18} />, t: "Conciliar e estornar",
    conteudo: [
      <>Conciliação = dizer <strong>qual obrigação aquele PIX quitou</strong>. Escolha o PIX com saldo e o alvo (débito ou projeção). O valor não pode passar do saldo nem do alvo.</>,
      <>Ao abrir a tela com um PIX selecionado, o sistema <strong>sugere um alvo e um valor</strong> (com o motivo, ex.: saldo exato ou datas próximas). A sugestão já preenche o formulário — <strong>nada é conciliado automaticamente</strong>: revise e clique em Conciliar.</>,
      <>Se não existir débito/projeção em aberto, a própria tela oferece <strong>criar um ali mesmo</strong>.</>,
      <>Parcial: pagou 700 de 1000 → o saldo restante (300) continua no débito. <strong>Excedente nunca vira crédito automático</strong> — acima da tolerância é recusado na hora.</>,
      <><strong>Estornar</strong> (desfazer) exige motivo + sua senha, e preserva o histórico: nunca some um registro conciliado.</>,
    ],
  },

  {
    id: "projecoes", icone: <ChartCandlestick size={18} />, t: "Projeções",
    conteudo: [
      <>Regra: <strong>uma projeção aberta por Representante + Fornecedor</strong>. O saldo é calculado pelo sistema conforme os PIX vão sendo conciliados.</>,
      <>O <strong>Simulador</strong> mostra quanto o rifeiro pode pagar sem exceder a dívida (considera a tolerância do fornecedor) — sem registrar nada.</>,
      <>As <strong>projeções automáticas</strong> compõem sozinhas PIX disponível × dívida na ordem do rodízio: revise a lista e clique em <strong>Aplicar</strong> — nada é criado sem a sua aprovação.</>,
    ],
  },
  {
    id: "fila", icone: <ArrowLeftRight size={18} />, t: "Fila de pagamentos (rodízio)",
    conteudo: [
      <>No Início: por fornecedor, a <strong>nota mais antiga em aberto</strong> e <strong>quanto falta para quitá-la</strong>, na ordem de prioridade. Quite as menores para liberar posições no rodízio.</>,
      <>Se o PIX em mãos cobre o faltante, aparece <strong>Quitar agora</strong> levando à conciliação.</>,
    ],
  },
  {
    id: "lancamentos", icone: <HandCoins size={18} />, t: "Débitos e créditos (lançamentos)",
    conteudo: [
      <>Onde vivem as obrigações: débito, crédito, despesa, imposto, salário, desconto, pagamento, perda — cada um com saldo em aberto.</>,
      <>Crie o débito da NF do fornecedor aqui (ou direto na tela de Conciliação quando não existir).</>,
      <>Crédito explícito: só nasce por este lançamento ou pela tolerância configurada — nunca silencioso.</>,
    ],
  },
  {
    id: "links", icone: <Link2 size={18} />, t: "Links do vendedor",
    conteudo: [
      <>Você (loja) gera um link e envia para o vendedor. O vendedor abre em <strong>/v/…</strong> e o cliente vê a chave copia-e-cola ou o <strong>QR de cobrança</strong>.</>,
      <>Com <strong>valor fixo</strong> e vendedor com email, telefone e documento, a <strong>cobrança PIX é gerada sozinha na hora</strong> — o vendedor abre o link e o QR já está lá, sem digitar nada. A cliente só escaneia e paga.</>,
      <>Sem esses dados (ou sem gateway), o link continua valendo no modo manual: copia-e-cola gerado na loja. O botão <strong>Gerar cobrança PIX</strong> serve para tentar de novo depois.</>,
      <>Link sem valor fixo mostra o <strong>copia-e-cola gerado na loja</strong> (sem depender de banco) para o pagador colar no app. Após pagar, a página mostra <strong>pagamento recebido</strong>.</>,
    ],
  },
  {
    id: "usuarios", icone: <Users size={18} />, t: "Usuários (só admin)",
    conteudo: [
      <>Seção exclusiva de <strong>administrador</strong> dentro da guia <strong>Conta</strong> para gerir quem entra no painel: <strong>criar usuário</strong> (nome, email, senha inicial e perfil), <strong>trocar o perfil</strong>, <strong>ativar/desativar</strong> o acesso e <strong>redefinir a senha</strong>.</>,
      <>O admin não consegue desativar a própria conta — proteção para nunca ficar sem acesso.</>,
      <>O <strong>login aceita email com maiúsculas</strong> (EXEMPLO@Loja.com funciona igual a exemplo@loja.com).</>,
    ],
  },
  {
    id: "historico", icone: <History size={18} />, t: "Histórico",
    conteudo: [
      <>Registro de <strong>quem fez o que e quando</strong> em tudo que mexeu com dinheiro: criação, edição, cancelamento, conciliação, estorno, exportação.</>,
      <>Disponível para admin e financeiro — é a trilha de auditoria em linguagem simples, com <strong>IP de origem</strong>, <strong>filtros</strong> por ação/entidade/usuário e <strong>exportação CSV</strong>.</>,
    ],
  },

  {
    id: "roadmap", icone: <Map size={18} />, t: "Roadmap",
    conteudo: [
      <>Histórico de entregas e mudanças do painel, do início até hoje — bom para o time acompanhar o que mudou e o que está por vir.</>,
    ],
  },
  {
    id: "metricas", icone: <Gauge size={18} />, t: "Métricas",
    conteudo: [
      <>Seção dentro da guia <strong>Conta</strong> com os números da operação: comprovantes por <strong>gateway</strong> (Checkto) e por <strong>upload manual</strong>, quantos comprovantes e conciliações por dia e os créditos ainda em aberto.</>,
      <>Ótimo para fechar o mês: mostra o ritmo de trabalho e o quanto a operação automatizou.</>,
    ],
  },
  {
    id: "senha", icone: <ShieldCheck size={18} />, t: "Trocar minha senha",
    conteudo: [
      <>Você troca a própria senha no menu do usuário (ícone no canto superior direito) ou na guia Conta.</>,
      <>Ao trocar, <strong>todas as suas sessões antigas são encerradas na hora</strong> — você entra de novo com a senha nova.</>,
    ],
  },
  {
    id: "conta", icone: <BookUser size={18} />, t: "Conta — perfil da loja",
    conteudo: [
      <>Cadastre o <strong>nome e o contato da loja</strong> na guia Conta — ela concentra perfil da loja, sua senha, usuários (admin) e métricas, com <strong>navegação lateral</strong> que sinaliza em qual configuração você está.</>,
      <>Só admin e financeiro alteram o perfil da loja; os demais perfis só visualizam.</>,
      <>Valores no painel têm cor: <strong>verde</strong> para entradas e disponível, <strong>vermelho</strong> para dívidas e cancelados, <strong>âmbar</strong> para pendências e saldos em aberto.</>,
    ],
  },
];

const DICAS = [
  ["Preencha o remetente com o nome de quem pagou", "É do remetente que o sistema deriva a sugestão de fornecedor (leitura simulada). Nome genérico = sugestão errada."],
  ["Nunca edite valor de movimentação conciliada", "O sistema bloqueia de propósito: use estorno (com senha) e refaça."],
  ["Excedente não vira crédito sozinho", "Pagou 1.200 numa dívida de 1.000? O saldo do PIX fica disponível para usar depois, não vira crédito silencioso."],
  ["Estorno e cancelamento pedem sua senha", "É a trava contra clique sem querer em operação de dinheiro."],
  ["Cadastre a chave PIX de todo fornecedor", "Sem chave, o fornecedor nem aparece para gerar link."],
  ["Vendedor de link precisa de email, telefone e documento", "A Checkto exige — preencha em Pessoas antes de cobrar."],
  ["Valor fixo no link vira QR de cobrança", "Sem valor fixo, o pagador digita o valor na chave manual."],
  ["Use a exportação CSV com os filtros aplicados", "O CSV respeita os filtros da tela — ótimo para fechar o dia e mandar pro contador."],
  ["Troque para o tema escuro no topo", "Prefere painel escuro? Clique no ícone de lua na barra superior — fica salvo."],
  ["Comprovante repetido é barrado", "A mesma foto não pode entrar duas vezes: proteção contra duplicidade."],
  ["Sugestão é só sugestão", "Na Conciliação, o sistema propõe alvo e valor com motivo — revise antes de clicar em Conciliar. Nada é feito sozinho."],
  ["PIX igual ao de outro dia? Confira", "Mesmo fornecedor, valor e data iguais viram alerta de possível duplicidade — pode ser lançamento repetido sem querer."],
  ["Pule de tela com Ctrl+K (⌘K no Mac)", "A busca global abre de qualquer tela: digite o nome da tela ou ação e Enter leva você direto."],
];

const REGRAS = [
  ["Sem crédito automático", "Conciliação nunca cria crédito sozinho. Excedente fica no PIX; crédito só com lançamento explícito ou tolerância."],
  ["Uma projeção aberta por par", "Só uma projeção aberta/parcial por Representante + Fornecedor."],
  ["Exclusão é sempre lógica", "Cancelar marca como cancelada; nada some do histórico."],
  ["Estorno preserva o rastro", "Desfazer gera registro próprio (RN-008) — auditoria fica intacta."],
  ["Movimentação conciliada não pode sumir", "Ela fica no histórico; para mexer, estorne primeiro."],
  ["Conciliação limitada ao saldo", "Não dá para conciliar mais do que existe disponível."],
  ["Tolerância por fornecedor", "Só permite crédito até o teto configurado e sempre como lançamento explícito visível."],
];

const GLOSSARIO = [
  ["Pagamento atravessado", "O cliente paga direto ao fornecedor via PIX, e a loja acompanha o caminho desse valor."],
  ["Representante", "Cliente, rifeiro ou vendedor que move valores na operação."],
  ["Fornecedor", "Quem recebe os PIX: a loja guarda chave, banco, prazo e tolerância dele."],
  ["Movimentação (PIX)", "Registro de um valor recebido, com quem pagou e o destino."],
  ["Saldo disponível", "Quanto daquele PIX ainda pode ser usado em conciliação."],
  ["Conciliação", "Ato de ligar um PIX a um débito/projeção e abater dos dois lados."],
  ["Projeção", "Expectativa de pagamento para um fornecedor, com saldo calculado pelo sistema."],
  ["Débito / lançamento", "A obrigação (ex.: NF) que precisa ser quitada."],
  ["Tolerância", "Teto de crédito que um fornecedor aceita receber além do devido."],
  ["OCR / leitura do comprovante", "Leitura experimental (simulada no MVP): não analisa a imagem de verdade; preenche campos só quando há dados extraídos e sugere fornecedor para revisão."],
  ["Comprovante de gateway", "Registro automático criado quando um pagamento da Checkto é confirmado."],
];

export default function Ajuda() {
  return (
    <div>
      <h1>Ajuda — guia completo</h1>
      <p className="muted">Tudo para operar o painel com confiança: comece pelo roteiro, depois explore cada módulo.</p>

      <section className="painel" aria-label="Mapa do guia">
        <h2><Rocket size={18} /> Neste guia</h2>
        <div className="quickgrid">
          {([
            ["#roteiro", "Roteiro inicial", <Rocket size={20} key="a" />],
            ["#modulos", "Cada tela", <ClipboardCheck size={20} key="b" />],
            ["#dicas", "Dicas importantes", <Lightbulb size={20} key="c" />],
            ["#regras", "Regras do sistema", <ShieldCheck size={20} key="d" />],
            ["#glossario", "Glossário", <HelpCircle size={20} key="e" />],
          ] as [string, string, React.ReactNode][]).map(([href, label, icone]) => (
            <a key={href} href={href} className="quickbtn">
              {icone}<strong>{label}</strong>
            </a>
          ))}
        </div>
      </section>

      <section className="painel" id="roteiro" aria-label="Roteiro inicial">
        <h2><Rocket size={18} /> Comece por aqui</h2>
        <p className="muted">Siga na ordem. Cada passo abre a tela real.</p>
        <div className="steps">
          {ROTEIRO.map((p) => (
            <div className="step" key={p.n}>
              <span className="n">{p.n}</span>
              <div>
                <strong><a href={p.href}>{p.t}</a></strong>
                <p className="muted">{p.o}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="painel" id="modulos" aria-label="Cada tela do painel">
        <h2><ClipboardCheck size={18} /> Cada tela do painel</h2>
        <p className="muted">Clique em um título para abrir o passo a passo do módulo.</p>
        {MODULOS.map((m) => (
          <details className="modulo" key={m.id}>
            <summary>{m.icone} {m.t}</summary>
            <div className="modulo-body">
              {m.conteudo.map((c, i) => <p key={i}>{c}</p>)}
            </div>
          </details>
        ))}
      </section>

      <section className="painel" id="dicas" aria-label="Dicas importantes">
        <h2><Lightbulb size={18} /> Dicas importantes</h2>
        <ul className="tip-list">
          {DICAS.map(([t, d]) => (
            <li key={t}><strong>{t}.</strong> {d}</li>
          ))}
        </ul>
      </section>

      <section className="painel" id="regras" aria-label="Regras do sistema">
        <h2><ShieldCheck size={18} /> Regras que o sistema aplica sozinho</h2>
        <div className="regras">
          {REGRAS.map(([t, d]) => (
            <div className="regra" key={t}>
              <strong>{t}</strong>
              <span className="muted">{d}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="painel" id="glossario" aria-label="Glossário">
        <h2><HelpCircle size={18} /> Glossário</h2>
        <div className="regras">
          {GLOSSARIO.map(([t, d]) => (
            <div className="regra" key={t}>
              <strong>{t}</strong>
              <span className="muted">{d}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
