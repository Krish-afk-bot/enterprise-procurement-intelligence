import { useState, useEffect } from "react";
import { LANDING_CONTENT } from "@/content/landing";
import { CurtainTransition } from "@/components/animations/CurtainTransition";
import { WordReveal } from "@/components/animations/WordReveal";
import { Marquee } from "@/components/animations/Marquee";
import { Sparkles, Database, Layers } from "lucide-react";

export function ExplainerSection() {
  const [captionIndex, setCaptionIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCaptionIndex((prev) => (prev + 1) % LANDING_CONTENT.explainer.rotatingCaptions.length);
    }, 3800);
    return () => clearInterval(timer);
  }, []);

  return (
    <CurtainTransition from="dark" to="light" id="explainer">
      <div className="relative py-28 px-6 max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-20">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider uppercase bg-black/5 border border-black/10 text-black/70 mb-6">
            <Sparkles className="w-3.5 h-3.5 text-[#FF4D00]" />
            <span>{LANDING_CONTENT.explainer.badge}</span>
          </div>

          <WordReveal
            as="h2"
            mode="scroll"
            className="text-3xl sm:text-5xl font-bold tracking-tight text-[#0A0A0A] mb-6 leading-tight"
          >
            {LANDING_CONTENT.explainer.heading}
          </WordReveal>

          <p className="text-base sm:text-lg text-[#6B6B6B] leading-relaxed max-w-2xl mx-auto">
            {LANDING_CONTENT.explainer.supportingStatement}
          </p>
        </div>

        {/* Two-column layout: Dark Media Card (Left) + Capabilities (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center mb-16">
          {/* Left: Tall Dark Media Card */}
          <div className="lg:col-span-5 relative h-[440px] rounded-3xl bg-[#0B0B0C] text-white p-8 overflow-hidden shadow-2xl border border-black/10 flex flex-col justify-between group">
            {/* Ambient generated orange lighting streaks */}
            <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-br from-[#FF4D00]/30 to-transparent rounded-full blur-3xl pointer-events-none transform translate-x-10 -translate-y-10 group-hover:scale-110 transition-transform duration-700" />
            <div className="absolute bottom-0 left-0 w-64 h-64 bg-gradient-to-tr from-[#FF7A1A]/20 to-transparent rounded-full blur-2xl pointer-events-none" />

            {/* Top decorative icons */}
            <div className="relative z-10 flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-widest text-[#FF4D00]">
                EPI REASONING ENGINE
              </span>
              <div className="flex gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-white/20" />
                <span className="w-2.5 h-2.5 rounded-full bg-white/20" />
                <span className="w-2.5 h-2.5 rounded-full bg-[#FF4D00]" />
              </div>
            </div>

            {/* Middle floating diagram preview */}
            <div className="relative z-10 flex flex-col items-center justify-center my-auto">
              <div className="w-20 h-20 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center shadow-xl mb-4 transform group-hover:rotate-6 transition-transform duration-500">
                <Layers className="w-10 h-10 text-[#FF4D00]" />
              </div>
              <div className="flex items-center gap-3 text-xs font-mono text-white/70 bg-white/5 px-3 py-1.5 rounded-lg border border-white/10">
                <Database className="w-3.5 h-3.5 text-[#FF7A1A]" />
                <span>RAG + Knowledge Graph</span>
              </div>
            </div>

            {/* Bottom rotating caption card */}
            <div className="relative z-10 bg-white/5 border border-white/10 rounded-2xl p-4 backdrop-blur-md">
              <span className="text-[11px] uppercase tracking-wider text-white/50 block mb-1">
                SYNCHRONIZED INSIGHT
              </span>
              <p className="text-sm font-medium text-white transition-opacity duration-300">
                {LANDING_CONTENT.explainer.rotatingCaptions[captionIndex]}
              </p>
            </div>
          </div>

          {/* Right: Architectural description + Triple Staggered Marquee */}
          <div className="lg:col-span-7 flex flex-col justify-center">
            <h3 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#0A0A0A] mb-4">
              Grounding Every Calculation in Verifiable Source Filings.
            </h3>
            <p className="text-sm sm:text-base text-[#6B6B6B] leading-relaxed mb-8">
              Legacy procurement search tools return disconnected keyword hits without verification.
              EPI ingests complex multi-lot tenders, amendment addenda, and pricing schedules into
              a unified knowledge layer, linking structured procurement metrics directly to original
              document pages.
            </p>

            {/* Three staggered marquee rows */}
            <div className="flex flex-col gap-3 overflow-hidden">
              <Marquee
                items={LANDING_CONTENT.explainer.capabilitiesMarquee.slice(0, 4)}
                direction="left"
                speed={32}
              />
              <Marquee
                items={LANDING_CONTENT.explainer.capabilitiesMarquee.slice(3, 7)}
                direction="right"
                speed={28}
              />
              <Marquee
                items={LANDING_CONTENT.explainer.capabilitiesMarquee.slice(6, 10)}
                direction="left"
                speed={35}
              />
            </div>
          </div>
        </div>
      </div>
    </CurtainTransition>
  );
}
