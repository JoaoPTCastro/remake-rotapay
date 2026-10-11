"use client";
import { useEffect, type RefObject } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
export function useSalesMotion(root: RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      const ctx = gsap.context(() => {
        gsap.from("[data-hero]", {
          y: 28,
          opacity: 0,
          duration: 1,
          stagger: 0.12,
          ease: "expo.out",
        });
        gsap.to('[data-float="one"]', {
          y: -65,
          rotation: -3,
          ease: "none",
          scrollTrigger: {
            trigger: "[data-hero-section]",
            start: "top top",
            end: "bottom top",
            scrub: 1,
          },
        });
        gsap.to('[data-float="two"]', {
          y: 85,
          rotation: 3,
          ease: "none",
          scrollTrigger: {
            trigger: "[data-hero-section]",
            start: "top top",
            end: "bottom top",
            scrub: 1,
          },
        });
        gsap.to("[data-orbit]", {
          rotation: 35,
          ease: "none",
          scrollTrigger: {
            trigger: "[data-hero-section]",
            start: "top top",
            end: "bottom top",
            scrub: 1.5,
          },
        });
        gsap.from("[data-route-line]", {
          scaleY: 0,
          transformOrigin: "top",
          ease: "none",
          scrollTrigger: {
            trigger: "[data-route]",
            start: "top 65%",
            end: "bottom 65%",
            scrub: 0.5,
          },
        });
        for (const el of gsap.utils.toArray<HTMLElement>("[data-step]")) {
          gsap.from(el, {
            x: 24,
            opacity: 0.25,
            duration: 0.8,
            ease: "expo.out",
            scrollTrigger: { trigger: el, start: "top 85%", once: true },
          });
        }
        gsap.from("[data-consequence]", {
          y: 28,
          opacity: 0,
          duration: 0.8,
          stagger: 0.22,
          ease: "power2.out",
          scrollTrigger: { trigger: "[data-consequences]", start: "top 78%", once: true },
        });
        gsap.from("[data-screen]", {
          y: 55,
          rotationX: 6,
          duration: 1,
          ease: "expo.out",
          scrollTrigger: {
            trigger: "[data-screen]",
            start: "top 90%",
            once: true,
          },
        });
      }, root);
      return () => ctx.revert();
    });
    return () => mm.revert();
  }, [root]);
}
