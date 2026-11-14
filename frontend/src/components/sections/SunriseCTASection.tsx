import { useLayoutEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { LANDING_CONTENT } from "@/content/landing";
import { WordReveal } from "@/components/animations/WordReveal";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { useMotionMode } from "@/motion/motion";

gsap.registerPlugin(ScrollTrigger);

export function SunriseCTASection() {
  const cardRef = useRef<HTMLDivElement>(null);
  const motionMode = useMotionMode();

  useLayoutEffect(() => {
    const card = cardRef.current;
    if (!card || motionMode === "off") return;

    const ctx = gsap.context(() => {
      // Scale to 0.94 with rounded corners as the next section arrives
      gsap.to(card, {
        scale: 0.94,
        ease: "none",
        scrollTrigger: {
          trigger: card,
          start: "center center",
          end: "bottom top",
          scrub: true,
        },
      });
    }, card);

    return () => ctx.revert();
  }, [motionMode]);

  return (
    <section id="cta" className="relative py-16 sm:py-20 px-4 sm:px-6 bg-[#050505] text-white scroll-mt-[112px]">
      {/* Full-width card with 28px rounded corners, inset 16px from viewport sides */}
      <div
        ref={cardRef}
        className="relative w-full max-w-7xl mx-auto rounded-[28px] overflow-hidden border border-white/15 shadow-[0_24px_80px_rgba(255,77,0,0.22)] py-24 sm:py-32 px-6 sm:px-12 flex flex-col items-center text-center will-change-transform"
        style={{
          background:
            "radial-gradient(120% 90% at 50% 120%, #FFF3E6 0%, #FF9A3D 18%, #FF4D00 38%, #7A1F00 62%, #050505 80%)",
        }}
      >
        {/* Soft atmospheric ambient glow shimmer */}
        <div className="absolute inset-0 bg-gradient-to-t from-white/10 via-transparent to-black/40 pointer-events-none" />

        {/* Content */}
        <div className="relative z-10 max-w-4xl mx-auto text-center flex flex-col items-center">
          <WordReveal
            as="h2"
            mode="scroll"
            className="text-4xl sm:text-6xl font-bold tracking-tight text-white mb-6 leading-tight max-w-2xl drop-shadow-md"
          >
            {LANDING_CONTENT.sunriseCta.heading}
          </WordReveal>

          <p className="text-base sm:text-lg text-white/80 max-w-xl font-normal leading-relaxed mb-10 drop-shadow-sm">
            {LANDING_CONTENT.sunriseCta.subtitle}
          </p>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              to={LANDING_CONTENT.sunriseCta.cta.href}
              className="inline-flex items-center gap-2 px-8 py-4 rounded-full text-sm font-semibold tracking-wide bg-[#FF4D00] text-white hover:bg-[#FF7A1A] transition-all duration-200 shadow-2xl shadow-[#FF4D00]/50 hover:shadow-[#FF4D00]/70 hover:scale-[1.02]"
            >
              <span>{LANDING_CONTENT.sunriseCta.cta.text}</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <Link
              to={LANDING_CONTENT.sunriseCta.secondaryCta.href}
              className="inline-flex items-center gap-2 px-8 py-4 rounded-full text-sm font-semibold tracking-wide bg-black/40 text-white border border-white/25 hover:bg-black/60 transition-all duration-200 backdrop-blur-md"
            >
              <ShieldCheck className="w-4 h-4 text-[#FF7A1A]" />
              <span>{LANDING_CONTENT.sunriseCta.secondaryCta.text}</span>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
