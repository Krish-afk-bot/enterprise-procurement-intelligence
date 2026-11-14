import { LANDING_CONTENT } from "@/content/landing";
import { CurtainTransition } from "@/components/animations/CurtainTransition";
import { WordReveal } from "@/components/animations/WordReveal";
import { Shield, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export function CapabilitiesSection() {
  return (
    <CurtainTransition from="light" to="dark" id="capabilities">
      <div className="relative py-28 px-6 max-w-7xl mx-auto">
        {/* Header Stack */}
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-20 gap-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider uppercase bg-white/5 border border-white/10 text-white/80">
            <Shield className="w-3.5 h-3.5 text-[#FF4D00]" />
            <span>{LANDING_CONTENT.capabilities.badge}</span>
          </div>

          <WordReveal
            as="h2"
            mode="scroll"
            className="text-3xl sm:text-5xl font-bold tracking-tight text-white leading-tight w-full"
          >
            {LANDING_CONTENT.capabilities.heading}
          </WordReveal>

          <p className="text-base sm:text-lg text-white/60 leading-relaxed max-w-2xl mx-auto">
            {LANDING_CONTENT.capabilities.subtitle}
          </p>
        </div>

        {/* 3 Capabilities Glass Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
          {LANDING_CONTENT.capabilities.tiers.map((tier) => (
            <div
              key={tier.id}
              className={cn(
                "relative rounded-3xl p-8 flex flex-col justify-between transition-all duration-300",
                tier.highlighted
                  ? "bg-[#111111] border-2 border-[#FF4D00]/60 shadow-[0_0_60px_rgba(255,77,0,0.18)] scale-100 lg:-translate-y-2"
                  : "bg-[#0B0B0C] border border-white/10 hover:border-white/20"
              )}
            >
              {/* F6.3: Non-wrapping Recommended Pill */}
              {tier.highlighted && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-[#FF4D00] text-white text-[11px] font-bold uppercase tracking-wider whitespace-nowrap shadow-md">
                  RECOMMENDED ARCHITECTURE
                </div>
              )}

              <div>
                <span className="text-xs font-mono uppercase tracking-wider text-[#FF4D00] font-semibold block mb-2">
                  {tier.badge}
                </span>

                <h3 className="text-2xl font-bold text-white mb-3 tracking-tight">
                  {tier.title}
                </h3>
                <p className="text-sm text-white/60 mb-8 leading-relaxed">
                  {tier.description}
                </p>

                <div className="flex flex-col gap-3.5 pt-6 border-t border-white/10">
                  {tier.features.map((feature, idx) => (
                    <div key={idx} className="flex items-start gap-3 text-xs text-white/80">
                      <CheckCircle className="w-4 h-4 text-[#FF4D00] shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </CurtainTransition>
  );
}
