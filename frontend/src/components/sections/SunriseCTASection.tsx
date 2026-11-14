import { Link } from "react-router-dom";
import { LANDING_CONTENT } from "@/content/landing";
import { WordReveal } from "@/components/animations/WordReveal";
import { ArrowRight, ShieldCheck } from "lucide-react";

export function SunriseCTASection() {
  return (
    <section id="cta" className="relative py-32 px-6 overflow-hidden bg-[#050505] text-white">
      {/* Signature Sunrise Radial Gradient (Warm White Core to Orange to Deep Red to Black) */}
      <div
        className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[1100px] h-[550px] pointer-events-none transform translate-y-1/3"
        style={{
          background:
            "radial-gradient(ellipse 65% 55% at 50% 100%, #FFF3E6 0%, #FF7A1A 22%, #FF4D00 45%, #7A1F00 70%, transparent 100%)",
          opacity: 0.85,
          filter: "blur(40px)",
        }}
      />

      {/* Film grain atmospheric overlay */}
      <div className="absolute inset-0 bg-noise opacity-4 pointer-events-none" />

      {/* Content */}
      <div className="relative z-10 max-w-4xl mx-auto text-center flex flex-col items-center">
        <WordReveal
          as="h2"
          mode="scroll"
          className="text-4xl sm:text-6xl font-bold tracking-tight text-white mb-6 leading-tight max-w-2xl"
        >
          {LANDING_CONTENT.sunriseCta.heading}
        </WordReveal>

        <p className="text-base sm:text-lg text-white/70 max-w-xl font-normal leading-relaxed mb-10">
          {LANDING_CONTENT.sunriseCta.subtitle}
        </p>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            to={LANDING_CONTENT.sunriseCta.cta.href}
            className="inline-flex items-center gap-2 px-8 py-4 rounded-full text-sm font-semibold tracking-wide bg-[#FF4D00] text-white hover:bg-[#FF7A1A] transition-all duration-200 shadow-xl shadow-[#FF4D00]/40 hover:shadow-[#FF4D00]/60 hover:scale-[1.02]"
          >
            <span>{LANDING_CONTENT.sunriseCta.cta.text}</span>
            <ArrowRight className="w-4 h-4" />
          </Link>

          <Link
            to={LANDING_CONTENT.sunriseCta.secondaryCta.href}
            className="inline-flex items-center gap-2 px-8 py-4 rounded-full text-sm font-semibold tracking-wide bg-white/10 text-white border border-white/20 hover:bg-white/20 transition-all duration-200 backdrop-blur-md"
          >
            <ShieldCheck className="w-4 h-4 text-[#FF7A1A]" />
            <span>{LANDING_CONTENT.sunriseCta.secondaryCta.text}</span>
          </Link>
        </div>
      </div>
    </section>
  );
}
