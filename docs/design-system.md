# Design System — RotaPay

## Marca e posicionamento

**RotaPay**

> O RotaPay organiza as cobranças, os comprovantes e os pagamentos aos fornecedores

Produto operacional para quem trabalha com pagamentos atravessados. A marca
representa o caminho do dinheiro: origem, destino, comprovante e obrigação.
O nome deve ser escrito **RotaPay**, com R e P maiúsculos; não usar Rota Pay.
PIX continua sendo o nome da forma de pagamento, não da plataforma.

## Direção visual

**Rotas claras.** Interface sóbria, legível e rápida de operar. Azul-petróleo
organiza a estrutura; ciano identifica a marca e os pontos de ação. Verde é
reservado a entradas/sucesso, vermelho a dívida/erro e âmbar a pendências.
A mudança de tema preserva o significado de cada cor.

## Logo

Monograma **R** desenhado como uma rota contínua com dois nós claros:
origem e destino. A curva superior forma a letra, a saída diagonal sinaliza
direção. Sem símbolos bancários ou promessa de liquidação pelo software.

| Arquivo | Uso |
| --- | --- |
| `frontend/public/brand/rotapay-logo.svg` | Assinatura horizontal para fundo claro |
| `frontend/public/brand/rotapay-logo-dark.svg` | Assinatura horizontal para fundo escuro |
| `frontend/public/brand/rotapay-mark.svg` | Símbolo isolado: avatar, ícone, favicons |
| `frontend/app/icon.svg` | Ícone do navegador gerenciado pelo Next.js |
| `frontend/components/BrandMark.tsx` | Símbolo inline, usando tokens do sistema |
| `frontend/public/brand/identidade.html` | Prancha visual de referência |

- Área de respiro mínima: 1/4 da altura do símbolo em cada lado.
- Símbolo mínimo: 24 px; preferir 36–56 px na interface.
- Não esticar, girar, adicionar sombras à logo nem trocar as cores dos nós.
- Manter o nome da loja como identificação secundária; a marca principal é RotaPay.
- O SVG tem fundo transparente fora do símbolo. Para materiais estáticos,
  usar os PNGs exportados com `node scripts/export-brand-assets.mjs`.

## Paleta e tokens

Fonte executável: `frontend/app/globals.css`.

| Token | Claro | Escuro | Papel |
| --- | --- | --- | --- |
| `--bg` | `#F4F8FA` | `#0C1820` | Fundo da aplicação |
| `--surface` | `#FFFFFF` | `#142530` | Cards, tabelas e formulários |
| `--surface-2` | `#EAF1F5` | `#1C3340` | Campos, hover e superfícies secundárias |
| `--text` | `#102D3C` | `#EDF7FA` | Texto principal |
| `--muted` | `#536B78` | `#A1B7C3` | Texto secundário |
| `--border` | `#D5E2E9` | `#304B5A` | Separação entre áreas |
| `--brand` | `#09687F` | `#64D5E8` | Ações primárias, links e foco |
| `--brand-2` | `#DFF3F7` | `#173C49` | Seleção e contexto de marca |
| `--brand-fg` | `#FFFFFF` | `#102D3C` | Texto sobre ação primária |
| `--success` | `#147A4B` | `#72D7A6` | Entradas, disponível e sucesso |
| `--warning` | `#9A6800` | `#F0C86C` | Pendências e saldos em aberto |
| `--danger` | `#B3261E` | `#FF918A` | Dívidas, cancelamentos e erros |

Símbolo: `--logo-bg: #102D3C`, `--logo-route: #64D5E8`,
`--logo-node: #F4FCFE`. A paleta do símbolo é fixa nos dois temas.

## Tipografia

Pilha local: `system-ui, -apple-system, Segoe UI, sans-serif`. Sem download de
fontes externas ou troca tardia de fonte.

- Nome da marca e títulos: peso 750, tracking negativo moderado.
- Título de página: `clamp(24px, 3vw, 34px)`, entrelinha 1,1.
- Título de seção: 18 px; corpo: 15 px/1,5; apoio: 12–13 px.
- Valores financeiros: `tabular-nums`; manter R$, saldo e status por escrito.
- `.pos`, `.neg`, `.pend` destacam a informação sem depender só da cor.

## Layout e componentes

- Raio base: 12 px; cards de destaque: 16 px; login: 18 px.
- Espaçamento em múltiplos de 4/8 px; formulários nunca devem colar os campos.
- Desktop: sidebar persistente; mobile: barra inferior com Início, PIX,
  Cadastro, Controle e Links.
- Conta centraliza perfil, senha, usuários e métricas com navegação de seção.
- Tabelas ficam em `.tablewrap`; no celular viram cartões com `data-label`.
- Logo acima da área de operação, sem competir com os números financeiros.

## Interação, acessibilidade e texto

- Uma ação primária por bloco; texto da ação deve indicar o resultado.
- Erro, sucesso e pendência têm rótulos/ícones além da cor.
- Campos com labels acessíveis; foco visível com contorno de 3 px.
- Contraste mínimo: 4,5:1 para texto normal; 3:1 para texto grande.
- Respeitar `prefers-reduced-motion`; transições curtas e sem animação decorativa contínua.
- Estados vazios indicam o próximo passo e falhas não se passam por dados vazios.
- Tema é preferência local e não modifica os dados nem a API.
- Marca: RotaPay. Vocabulário operacional: cobrança, comprovante, fornecedor,
  saldo disponível, pendência e conciliação. Não prometer que o software
  liquida dinheiro, confirma repasse bancário ou regulariza a origem dos valores.

## Validação da identidade

- Login e painel nos temas claro/escuro.
- Overflow horizontal igual a zero em 390 e 1024 px.
- Logo reconhecível em tamanho pequeno e sem distorção.
- RotaPay em título da aba, login, menu, API e documentação.
- Testes financeiros preservados durante o rebranding.
