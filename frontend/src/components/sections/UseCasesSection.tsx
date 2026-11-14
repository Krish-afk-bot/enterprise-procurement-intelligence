import { LANDING_CONTENT } from "@/content/landing";
import { WordReveal } from "@/components/animations/WordReveal";
import { Sparkles, Check } from "lucide-react";
import { useMotionMode } from "@/motion/motion";
import { cn } from "@/lib/utils";

function UseCaseIllustration({ id, motionMode }: { id: string; motionMode: string }) {
  const isReduced = motionMode === "reduced" || motionMode === "off";

  switch (id) {
    case "uc-1":
      // Clause extraction: clause lines with a highlight bar sliding across
      return (
        <div className="w-full h-20 rounded-2xl bg-black/[0.02] border border-black/[0.06] p-3 flex flex-col justify-center gap-2 overflow-hidden mb-5 relative">
          <div className="w-3/4 h-2 rounded bg-black/10" />
          <div className="relative w-full h-2.5 rounded bg-black/10 overflow-hidden">
            <div
              className={cn(
                "absolute top-0 bottom-0 w-1/3 rounded bg-[#FF4D00]",
                !isReduced && "animate-[slideRight_2.4s_easeInOut_infinite]"
              )}
              style={isReduced ? { left: "25%" } : undefined}
            />
          </div>
          <div className="w-1/2 h-2 rounded bg-black/10" />
        </div>
      );

    case "uc-2":
      // Entity graph: entity nodes linking with an active pulse
      return (
        <div className="w-full h-20 rounded-2xl bg-black/[0.02] border border-black/[0.06] px-4 flex items-center justify-between mb-5 relative overflow-hidden">
          <svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
            <line x1="20%" y1="50%" x2="50%" y2="50%" stroke="rgba(0,0,0,0.15)" strokeWidth="1.5" strokeDasharray="3 3" />
            <line x1="50%" y1="50%" x2="80%" y2="50%" stroke="rgba(0,0,0,0.15)" strokeWidth="1.5" strokeDasharray="3 3" />
          </svg>
          <div className="relative z-10 flex flex-col items-center">
            <div className="w-6 h-6 rounded-lg bg-black/5 border border-black/15 flex items-center justify-center text-[10px] font-bold text-black/60">B</div>
            <span className="text-[9px] text-black/40 mt-1">Buyer</span>
          </div>
          <div className="relative z-10 flex flex-col items-center">
            <div className="w-7 h-7 rounded-lg bg-[#FF4D00]/10 border border-[#FF4D00] flex items-center justify-center text-[10px] font-bold text-[#FF4D00]">
              <span className={cn("w-2 h-2 rounded-full bg-[#FF4D00]", !isReduced && "animate-ping")} />
            </div>
            <span className="text-[9px] text-[#FF4D00] font-semibold mt-1">Award</span>
          </div>
          <div className="relative z-10 flex flex-col items-center">
            <div className="w-6 h-6 rounded-lg bg-black/5 border border-black/15 flex items-center justify-center text-[10px] font-bold text-black/60">S</div>
            <span className="text-[9px] text-black/40 mt-1">Supplier</span>
          </div>
        </div>
      );

    case "uc-3":
      // Pricing benchmarks: a price line drawing itself
      return (
        <div className="w-full h-20 rounded-2xl bg-black/[0.02] border border-black/[0.06] p-3 flex items-center justify-center mb-5 relative overflow-hidden">
          <svg className="w-full h-12" viewBox="0 0 200 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <line x1="10" y1="40" x2="190" y2="40" stroke="rgba(0,0,0,0.08)" strokeWidth="1" />
            <line x1="10" y1="20" x2="190" y2="20" stroke="rgba(0,0,0,0.04)" strokeDasharray="2 4" strokeWidth="1" />
            <path
              d="M 15 36 Q 60 34 85 24 T 140 18 T 185 10"
              stroke="#FF4D00"
              strokeWidth="2.5"
              strokeLinecap="round"
              className={cn(!isReduced && "animate-[dash_3s_ease-in-out_infinite]")}
              style={{ strokeDasharray: 200, strokeDashoffset: isReduced ? 0 : undefined }}
            />
            <circle cx="185" cy="10" r="3.5" fill="#FF4D00" />
            <circle cx="185" cy="10" r="6" stroke="#FF4D00" strokeWidth="1" opacity="0.4" className={cn(!isReduced && "animate-ping")} />
          </svg>
        </div>
      );

    case "uc-4":
      // Audit trail: audit log rows appearing one after another
      return (
        <div className="w-full h-20 rounded-2xl bg-black/[0.02] border border-black/[0.06] p-2.5 flex flex-col justify-center gap-1.5 mb-5 relative overflow-hidden">
          <div className="flex items-center justify-between px-2.5 py-1 rounded bg-black/5 text-[9px] font-mono text-black/60">
            <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-black/30" />QUERY_ISSUED</span>
            <span>12:04:01</span>
          </div>
          <div className="flex items-center justify-between px-2.5 py-1 rounded bg-black/5 text-[9px] font-mono text-black/60">
            <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-black/30" />CHUNKS_RETRIEVED</span>
            <span>12:04:02</span>
          </div>
          <div className={cn("flex items-center justify-between px-2.5 py-1 rounded bg-[#FF4D00]/10 border border-[#FF4D00]/30 text-[9px] font-mono text-[#FF4D00]", !isReduced && "animate-pulse")}>
            <span className="flex items-center gap-1.5 font-bold"><span className="w-1.5 h-1.5 rounded-full bg-[#FF4D00]" />CITATION_VERIFIED</span>
            <span>12:04:03</span>
          </div>
        </div>
      );

    case "uc-5":
      // Variation history: a version timeline with dots lighting in sequence
      return (
        <div className="w-full h-20 rounded-2xl bg-black/[0.02] border border-black/[0.06] px-4 flex items-center justify-between mb-5 relative overflow-hidden">
          <div className="absolute left-6 right-6 top-1/2 -translate-y-1/2 h-0.5 bg-black/10 -z-0" />
          {[
            { v: "v1.0", active: false, label: "Original" },
            { v: "v1.1", active: false, label: "Addendum" },
            { v: "v2.0", active: true, label: "Ceiling Ext" },
          ].map((item, idx) => (
            <div key={idx} className="relative z-10 flex flex-col items-center">
              <div
                className={cn(
                  "w-5 h-5 rounded-full border flex items-center justify-center text-[8px] font-bold transition-all",
                  item.active
                    ? "bg-[#FF4D00] text-white border-[#FF4D00] shadow-[0_0_10px_rgba(255,77,0,0.5)]"
                    : "bg-white text-black/60 border-black/20"
                )}
              >
                {item.v.slice(1)}
              </div>
              <span className={cn("text-[9px] mt-1 font-mono", item.active ? "text-[#FF4D00] font-bold" : "text-black/40")}>
                {item.label}
              </span>
            </div>
          ))}
        </div>
      );

    case "uc-6":
      // Network analytics: a mini network with a pulse
      return (
        <div className="w-full h-20 rounded-2xl bg-black/[0.02] border border-black/[0.06] flex items-center justify-center mb-5 relative overflow-hidden">
          <svg className="w-40 h-16" viewBox="0 0 160 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <line x1="80" y1="32" x2="35" y2="18" stroke="rgba(0,0,0,0.12)" strokeWidth="1" />
            <line x1="80" y1="32" x2="35" y2="46" stroke="rgba(0,0,0,0.12)" strokeWidth="1" />
            <line x1="80" y1="32" x2="125" y2="20" stroke="rgba(0,0,0,0.12)" strokeWidth="1" />
            <line x1="80" y1="32" x2="125" y2="44" stroke="rgba(0,0,0,0.12)" strokeWidth="1" />
            <circle cx="35" cy="18" r="4" fill="rgba(0,0,0,0.2)" />
            <circle cx="35" cy="46" r="4" fill="rgba(0,0,0,0.2)" />
            <circle cx="125" cy="20" r="4" fill="rgba(0,0,0,0.2)" />
            <circle cx="125" cy="44" r="4" fill="rgba(0,0,0,0.2)" />
            <circle cx="80" cy="32" r="14" stroke="#FF4D00" strokeWidth="1" opacity="0.3" className={cn(!isReduced && "animate-ping")} />
            <circle cx="80" cy="32" r="7" fill="#FF4D00" />
            <circle cx="80" cy="32" r="3" fill="#FFFFFF" />
          </svg>
        </div>
      );

    default:
      return null;
  }
}

export function UseCasesSection() {
  const motionMode = useMotionMode();

  return (
    <section id="use-cases" className="relative py-28 px-6 bg-[#FAFAFA] text-[#0A0A0A] scroll-mt-[112px]">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-20">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider uppercase bg-black/5 border border-black/10 text-black/70 mb-6">
            <Sparkles className="w-3.5 h-3.5 text-[#FF4D00]" />
            <span>{LANDING_CONTENT.useCases.badge}</span>
          </div>

          <WordReveal
            as="h2"
            mode="scroll"
            className="text-3xl sm:text-5xl font-bold tracking-tight text-[#0A0A0A] mb-6 leading-tight"
          >
            {LANDING_CONTENT.useCases.heading}
          </WordReveal>

          <p className="text-base sm:text-lg text-[#6B6B6B] leading-relaxed max-w-2xl mx-auto">
            {LANDING_CONTENT.useCases.subtitle}
          </p>
        </div>

        {/* 3x2 Grid of Use Case Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {LANDING_CONTENT.useCases.items.map((item) => (
            <div
              key={item.id}
              className="group p-8 rounded-3xl bg-white border border-black/10 shadow-sm hover:shadow-xl hover:border-[#FF4D00]/40 transition-all duration-300 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-[#FF4D00] font-semibold">
                    {item.metricBadge}
                  </span>
                  <span className="w-2 h-2 rounded-full bg-black/20 group-hover:bg-[#FF4D00] transition-colors" />
                </div>

                {/* SVG/CSS Illustration with subtle motion */}
                <UseCaseIllustration id={item.id} motionMode={motionMode} />

                <h3 className="text-xl font-bold tracking-tight text-[#0A0A0A] mb-3">
                  {item.title}
                </h3>
                <p className="text-sm text-[#6B6B6B] leading-relaxed mb-6">
                  {item.description}
                </p>
              </div>

              {/* Three Specific Outcomes */}
              <div className="pt-6 border-t border-black/5 flex flex-col gap-2.5">
                {item.outcomes.map((outcome, idx) => (
                  <div key={idx} className="flex items-start gap-2.5 text-xs text-[#0A0A0A]/80">
                    <Check className="w-3.5 h-3.5 text-[#FF4D00] shrink-0 mt-0.5" />
                    <span>{outcome}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
