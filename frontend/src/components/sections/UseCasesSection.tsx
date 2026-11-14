import { LANDING_CONTENT } from "@/content/landing";
import { WordReveal } from "@/components/animations/WordReveal";
import { Sparkles, Check } from "lucide-react";

export function UseCasesSection() {
  return (
    <section id="use-cases" className="relative py-28 px-6 bg-[#FAFAFA] text-[#0A0A0A]">
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
