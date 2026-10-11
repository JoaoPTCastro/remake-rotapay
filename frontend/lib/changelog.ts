// Changelog do MVP — atualize a cada entrega (mais recente primeiro).
// Fonte para a página /roadmap (botão no rodapé do menu).
export type Mudanca = { data: string; titulo: string; itens: string[] };

export const CHANGELOG: Mudanca[] = [
  {
    data: "30/09/2026",
    titulo: "RotaPay — nova marca e identidade visual",
    itens: [
      "Nova logo em SVG e PNG: uma rota que forma a letra R, com pontos de origem e destino.",
      "Identidade azul-petróleo e ciano aplicada ao login e ao painel nos temas claro e escuro.",
      "O RotaPay organiza as cobranças, os comprovantes e os pagamentos aos fornecedores.",
    ],
  },
  {
    data: "10/09/2026",
    titulo: "Cobrança automática no link",
    itens: [
      "Gerar link com valor fixo já cria o QR PIX sozinho — vendedor e cliente não digitam nada.",
      "Sem dados do vendedor ou sem gateway, o link nasce manual (copia-e-cola) sem quebrar.",
    ],
  },

  {
    data: "10/09/2026",
    titulo: "Rodízio, projeção automática e auditoria com IP",
    itens: [
      "Fila de pagamentos no Início: nota mais antiga em aberto + faltante por fornecedor, em ordem de prioridade.",
      "Projeções automáticas: compõe PIX × dívida na ordem do rodízio; você revisa e aplica.",
      "Histórico com IP, filtros por ação/entidade/usuário e exportação CSV.",
      "Controle filtra por chave PIX e com/sem link (vale no CSV).",
      "Correções da revisão: export de auditoria liberado, worker ignora comprovante rejeitado, vínculo bloqueado em rejeitado.",
    ],
  },
  {
    data: "09/09/2026",
    titulo: "Conta centraliza Usuários e Métricas",
    itens: [
      "Guia Conta com navegação lateral: Perfil da loja, Sua senha, Usuários e Métricas na mesma tela.",
      "Usuários e Métricas passam a viver só na Conta (rotas antigas redirecionam).",
    ],
  },
  {
    data: "09/09/2026",
    titulo: "Menu do usuário e Conta central",
    itens: [
      "Ícone de usuário no canto superior direito abre painel flutuante com Conta, Usuários, Métricas e Trocar senha.",
      "Guia Conta concentra tudo: perfil da loja, sua senha, atalho de usuários (admin) e métricas.",
      "Usuários, Métricas e Senha saíram da barra lateral para o menu do usuário.",
    ],
  },
  {
    data: "09/09/2026",
    titulo: "Conta da loja e cores nos números",
    itens: [
      "Tela Conta: nome, CNPJ/CPF, telefone, email e endereço da loja (só admin e financeiro alteram); o nome aparece no topo do menu.",
      "Números com destaque: verde para entradas e disponível, vermelho para dívidas e cancelados, âmbar para pendências e saldos em aberto.",
      "Corrige o endereço da API no deploy (render.yaml).",
    ],
  },
  {
    data: "09/09/2026",
    titulo: "Métricas e troca de senha",
    itens: [
      "Tela Métricas: origem dos comprovantes (gateway x manual), ritmo por dia e créditos em aberto.",
      "Cada usuário troca a própria senha (menu lateral ou busca global); sessões antigas são encerradas na hora.",
    ],
  },
  {
    data: "09/09/2026",
    titulo: "Inteligência, usuários e busca global",
    itens: [
      "Conciliação com sugestão: ao abrir com um PIX selecionado, o sistema sugere alvo e valor com o motivo — nada é executado automaticamente.",
      "Alerta de possível duplicidade (mesmo fornecedor, valor e data PIX) para conferência.",
      "Insights acionáveis no Início, com link direto para a tela que resolve cada pendência.",
      "Tela Usuários exclusiva do admin (criar, perfil, ativar/desativar, redefinir senha) e login aceitando email com maiúsculas.",
      "Busca global por telas e ações: Ctrl+K (⌘K no Mac) e botão no topo, inclusive no celular.",
      "PIX virou registro rápido (após salvar, abre o detalhe); Controle concentra consulta, filtros, exportação e conciliação; Pessoas e Chaves redirecionam para o Cadastro.",
    ],
  },
  {
    data: "09/09/2026",
    titulo: "Guia completo na aba Ajuda",
    itens: [
      "Roteiro inicial em 6 passos, tutorial de cada módulo em acordeão.",
      "Dicas importantes, regras automáticas e glossário de termos.",
    ],
  },
  {
    data: "09/09/2026",
    titulo: "Dashboard em 3 quadros",
    itens: [
      "Valores por fornecedor com última compra; Últimas saídas; PIX gerados pelos links.",
      "8 itens por quadro com ver mais no lugar; PIX de link rastreado por origem.",
    ],
  },
  {
    data: "09/09/2026",
    titulo: "Design System e painel responsivo",
    itens: [
      "Sidebar desktop, barra inferior mobile, topbar contextual e navegação por ícones.",
      "Login redesenhado com linguagem de controle financeiro e acessibilidade básica.",
      "Overflow mobile corrigido e exportações com download autenticado.",
    ],
  },
  {
    data: "08/09/2026",
    titulo: "Menu do time + estorno com senha",
    itens: [
      "Menu principal definido: Início, PIX, Cadastro, Controle, Links.",
      "Auditoria renomeada para Histórico; Chaves e Pessoas moram no Cadastro.",
      "Estorno e cancelamentos exigem a senha do usuário.",
    ],
  },
  {
    data: "08/09/2026",
    titulo: "Novo visual + tutorial",
    itens: [
      "Sidebar com ícones no desktop; barra inferior no celular.",
      "Guia de uso em 6 passos (/ajuda) + checklist de primeiros passos.",
      "Páginas públicas de pagamento (/pagar) e do vendedor (/v).",
    ],
  },

  {
    data: "08/09/2026",
    titulo: "Regras financeiras",
    itens: [
      "Tolerância de crédito por fornecedor + simulador do rifeiro.",
      "Excedente nunca vira crédito silencioso; estorno preserva histórico.",
      "Exportação CSV compatível com Excel.",
    ],
  },
  {
    data: "02–07/09/2026",
    titulo: "Fundação do MVP",
    itens: [
      "PRD, atas e roadmaps; base fiel à planilha (901 PIX, R$ 898 mil).",
      "Login com 4 perfis, auditoria completa, 15 testes automatizados.",
      "Links do vendedor, chaves PIX, projeções e dashboard.",
    ],
  },
];
