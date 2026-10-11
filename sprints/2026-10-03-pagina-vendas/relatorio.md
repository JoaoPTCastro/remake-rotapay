# Página de vendas RotaPay — entrega

03/10/2026. Pedido: construir página pronta com copy revisada, identidade local, referências, parallax e GSAP. Entrega publicada no ambiente de testes previamente autorizado; sem promover operação real.

## Onde acessar

https://rotapay.site/conheca, pública com ou sem sessão. Na raiz sem sessão, a página é exibida por rewrite; com sessão, a raiz preserva o painel. /login permanece entrada do sistema.

## O que foi feito

Hero petróleo/ciano e ilustração autoral do link PIX, comprovante e acerto. Caminho loja→vendedor→cliente→fornecedor explicado em etapas. Parallax de duas camadas/órbita com scroll, rota desenhada pelo ScrollTrigger. Sem scroll artificial ou bloqueio da leitura. Visões por participante em tabs com teclado, FAQ nativo, menu mobile, exemplo de abatimento reversível e CTA para demo com credenciais sintéticas. Ilustrações identificadas, sem fingir screenshots do produto. Nenhuma promessa de integração bancária ou abatimento automático. Nenhuma oferta, depoimento ou métrica inventada.

Next/React/TypeScript/CSSModules; GSAP adicionado ao lockfile. Fontes locais conforme identidade. Módulos separados por seção e hook com limpeza GSAP; prefers-reduced-motion desativa animações. Metadados de página/canonical. Sem formulário de leads ou envio a terceiros.

## Verificação

Lint sem erros/avisos; TypeScript aprovado. Lint tipado: zero erros e 200 avisos preexistentes, sem avisos nas fontes da página. Build inicial local aprovado; build FINAL remoto com refatoração aprovado,56rotas. HTTP público: raiz e /conheca200,13assetsJS/CSS200, conta exige login, login e conta/root autenticados preservados. Browserdesktop e390×844: headline/contraste/hierarquia conferidos, semoverflowhorizontal,1H1. Tabs fornecedor, simulação500→saldo1500, FAQ, menuabre/fecha e retornoao início aprovados. Transform da rota acompanha scroll. Redução de movimento verificada no código, não emulada neste browser.

Detector Impeccable apontou border-bottom3px; é indicador de seleção em tabs SEM cantos arredondados, não borda emcard. Não suprimido globalmente. npm audit reportou6vulnerabilidadeshigh na árvore jáexistente após instalação; não aplicada atualização ampla/forçada fora deste escopo. Sem nova auditoria de dependências declarada.

## Publicação e retorno

Somente web da homologação recriado; API/bancos preservados. Imagem rotapay-s18-web:lp-final-20261003, manifest c4e3711e20917bc6b233e1cbfee2c61ba8dd0b8aaaf39feb4fbe7c0cc36c7acf. Pasta /srv/rotapay-homologacao-s18/lp-final. Compose anterior em compose.pre-lp.yml. Retorno: validar configuração anterior e subir apenasweb com --no-deps/--no-build. Imagem anterior rotapay-s18-web:homologacao preservada. Containersoperacionaispix seguem ativos háduassemanas; não reiniciados. Semcommit/push, alteraçãoCaddy/DNS adicional, seed ou dadosreais.

## Continuidade

Página funciona e aguarda avaliação visual/comercial do usuário. Headernoindex do ambiente de testes permanece até aprovação pública definitiva. Captação comercial (canal/equipe/contato), preço, prova social real e indexação podem ser definidos depois; CTAs atuais abrem a demo. Aceiteoperacional, migração, Checkto e demais pendências S18 continuam separados.

Referências: https://saaslandingpage.com/ (estrutura), https://www.dark.design/ (contraste), https://gsap.com/showcase/ (movimento), https://gsap.com/docs/v3/GSAP/gsap.matchMedia()/ (implementação). Skills ReferênciasWeb,Impeccable,Fullstack; copyrevisada anteriormente comdoug-copy. Identidade docs/design-system.md prevalece.
