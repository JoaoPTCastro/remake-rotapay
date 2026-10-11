import {
  Link2,
  Store,
  UserRound,
  FileCheck2,
  Wallet,
  Send,
} from "lucide-react";
export const steps = [
  {
    title: "A loja gera o link.",
    text: "A cobrança começa organizada, com as informações que o cliente precisa para pagar.",
    icon: Store,
  },
  {
    title: "O vendedor entrega.",
    text: "O link chega ao cliente no atendimento. Sem cadastro, sem complicar a venda.",
    icon: Send,
  },
  {
    title: "O cliente paga.",
    text: "Pagamento e comprovante entram no acompanhamento da operação.",
    icon: Wallet,
  },
  {
    title: "O fornecedor acompanha.",
    text: "Com acesso próprio, ele consulta suas relações e pode declarar o recebimento.",
    icon: UserRound,
  },
  {
    title: "O acerto ganha contexto.",
    text: "A loja aplica o valor à obrigação e confere o saldo que ainda falta acertar.",
    icon: FileCheck2,
  },
];
export const perspectives = [
  {
    name: "Loja",
    title: "Uma visão do que precisa ser acertado.",
    text: "Organize cobranças, notas, comprovantes e pagamentos. Saiba o que já foi aplicado e o que permanece em aberto.",
    label: "Acerto com fornecedor",
    amount: "R$ 1.500,00",
    status: "Saldo em aberto",
    icon: Store,
  },
  {
    name: "Vendedor",
    title: "O próximo passo da venda cabe em um link.",
    text: "Receba o link organizado pela loja e entregue ao cliente durante o atendimento. A cobrança começa com um caminho claro.",
    label: "Link organizado pela loja",
    amount: "R$ 500,00",
    status: "Pronto para entregar ao cliente",
    icon: Link2,
  },
  {
    name: "Cliente",
    title: "Pague e consulte. Sem criar uma conta.",
    text: "Acesse as informações da cobrança pelo link recebido e acompanhe sua situação em um só lugar.",
    label: "Informações da cobrança",
    amount: "R$ 500,00",
    status: "Acesso por link",
    icon: Wallet,
  },
  {
    name: "Fornecedor",
    title: "Seu acesso. Suas relações.",
    text: "Administre suas chaves PIX, acompanhe as relações autorizadas e declare recebimentos sem acessar toda a operação da loja.",
    label: "Recebimento informado",
    amount: "R$ 500,00",
    status: "Declaração humana registrada",
    icon: UserRound,
  },
];
export const faq = [
  [
    "Quem gera e entrega o link PIX?",
    "A loja organiza a cobrança e gera o link. O vendedor entrega esse link ao cliente final, que pode consultar as informações sem criar uma conta.",
  ],
  [
    "O dinheiro precisa passar pela loja?",
    "O sistema contempla pagamentos diretos ao fornecedor e recebimentos pela loja com posterior repasse. O trajeto depende da operação organizada pela loja.",
  ],
  [
    "O PIX é confirmado automaticamente pelo banco?",
    "A confirmação automática pelo banco ainda não está disponível. A declaração de recebimento do fornecedor é identificada como confirmação humana.",
  ],
  [
    "O pagamento abate uma nota automaticamente?",
    "Não. A aplicação do valor à obrigação é uma etapa explícita. Assim, sua equipe pode conferir o que foi abatido e o saldo restante.",
  ],
  [
    "Um fornecedor pode participar de várias lojas?",
    "Sim. O fornecedor pode ter vínculos com diferentes lojas, com acesso limitado às relações autorizadas em cada ambiente.",
  ],
  [
    "Como começo a usar o RotaPay?",
    "Conte como sua loja opera pelo formulário de avaliação. Nossa equipe analisa o perfil e entra em contato para orientar os próximos passos.",
  ],
];
