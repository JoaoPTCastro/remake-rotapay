"use client";
import { useEffect, useRef } from "react";
import Image from "next/image";
import { Check, Link2, FileCheck2 } from "lucide-react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import s from "./PaymentStory.module.css";
export default function PaymentStory() {
  const root = useRef<HTMLElement>(null);
  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);
    const media = gsap.matchMedia();
    media.add("(prefers-reduced-motion: no-preference) and (min-height: 720px)", () => {
      const context = gsap.context(() => {
        const timeline = gsap.timeline({scrollTrigger:{trigger:root.current,start:"top top",end:"+=180%",pin:true,scrub:0.6,invalidateOnRefresh:true}});
        timeline.to('[data-scene]',{scale:1.07,duration:3},0)
          .to('[data-stage="link"]',{opacity:0,y:-30,duration:0.4},0.7)
          .fromTo('[data-stage="pay"]',{opacity:0,y:40},{opacity:1,y:0,duration:0.5},0.9)
          .to('[data-stage="pay"]',{opacity:0,y:-30,duration:0.4},1.8)
          .fromTo('[data-stage="receipt"]',{opacity:0,y:40},{opacity:1,y:0,duration:0.5},2)
          .to('[data-progress]',{scaleX:1,duration:3,ease:"none"},0);
      },root);
      return () => context.revert();
    });
    return () => media.revert();
  },[]);
  return <section id="pagamento-em-movimento" ref={root} className={s.story} aria-label="Animação ilustrativa: link enviado, pagamento da cliente e comprovante organizado">
    <div className={s.scene} data-scene><Image src="/brand/rotapay-cena-porta-a-porta.jpg" alt="Vendedor atendendo a cliente na porta de casa, com pagamento pelo celular" fill sizes="100vw" /></div>
    <div className={s.shade}/>
    <div className={s.content}>
      <h2>Da porta da cliente<br />ao controle da loja.</h2>
      <p>Acompanhe o caminho do pagamento ao rolar.</p>
      <div className={s.stages}>
        <div className={s.stage} data-stage="link"><Link2/><span>O vendedor envia o link.</span><strong>Uma cobrança. Um caminho claro.</strong><small>Valor definido pela loja ou informado pela cliente.</small></div>
        <div className={s.stage} data-stage="pay"><div className={s.phone}><span>Loja Exemplo</span><strong>R$ 500,00</strong><div className={s.confirm}><Check/> Pagamento ilustrado</div></div><span>A cliente paga no celular.</span><small>Sem precisar criar uma conta.</small></div>
        <div className={s.stage} data-stage="receipt"><FileCheck2/><span>O comprovante ganha contexto.</span><strong>Ligado ao pagamento certo.</strong><small>A loja acompanha e organiza o acerto com o fornecedor.</small></div>
      </div>
      <div className={s.track}><span data-progress/></div>
      <small className={s.disclaimer}>Cena ilustrativa · não realiza pagamento nem confirma PIX pelo banco.</small>
    </div>
  </section>;
}
