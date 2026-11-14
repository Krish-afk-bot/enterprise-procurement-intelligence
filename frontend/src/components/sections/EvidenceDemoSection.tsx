import { useState } from "react";
import { LANDING_CONTENT, DemoOption } from "@/content/landing";
import { CurtainTransition } from "@/components/animations/CurtainTransition";
import { WordReveal } from "@/components/animations/WordReveal";
import { cn } from "@/lib/utils";
import {
  Sparkles,
  FileText,
  Search,
  CheckCircle2,
} from "lucide-react";

export function EvidenceDemoSection() {
  const [selectedOption, setSelectedOption] = useState<DemoOption>(
    LANDING_CONTENT.demo.options[0]
  );
  const [isTyping, setIsTyping] = useState(false);

  const handleSelect = (option: DemoOption) => {
    if (option.id === selectedOption.id) return;
    setIsTyping(true);
    setSelectedOption(option);
    setTimeout(() => {
      setIsTyping(false);
    }, 400);
  };

  return (
    <CurtainTransition from="dark" to="light" id="demo">
      <div className="relative py-28 px-6 max-w-7xl mx-auto">
        {/* Soft pastel dome background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-64 bg-gradient-to-b from-[#CFE6F7]/40 to-transparent blur-3xl pointer-events-none" />

        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 relative z-10">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider uppercase bg-black/5 border border-black/10 text-black/70 mb-6">
            <Sparkles className="w-3.5 h-3.5 text-[#FF4D00]" />
            <span>{LANDING_CONTENT.demo.badge}</span>
          </div>

          <WordReveal
            as="h2"
            mode="scroll"
            className="text-3xl sm:text-5xl font-bold tracking-tight text-[#0A0A0A] mb-6 leading-tight"
          >
            {LANDING_CONTENT.demo.heading}
          </WordReveal>

          <p className="text-base sm:text-lg text-[#6B6B6B] leading-relaxed max-w-2xl mx-auto">
            {LANDING_CONTENT.demo.subtitle}
          </p>
        </div>

        {/* Main Pinned Interactive Demo Card */}
        <div className="relative z-10 max-w-5xl mx-auto rounded-3xl bg-white border border-black/10 shadow-2xl p-6 sm:p-10 overflow-hidden">
          {/* Top Label & Disclaimer */}
          <div className="flex items-center justify-between pb-6 border-b border-black/5 mb-8">
            <div className="flex items-center gap-2.5">
              <span className="w-3 h-3 rounded-full bg-[#FF4D00]" />
              <span className="font-semibold text-sm text-[#0A0A0A] tracking-tight">
                EPI Evidence Traceability Console
              </span>
            </div>
            <span className="text-xs font-mono font-medium px-2.5 py-1 rounded-full bg-black/5 text-[#6B6B6B]">
              {LANDING_CONTENT.demo.label}
            </span>
          </div>

          {/* 2x2 Option Selector Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
            {LANDING_CONTENT.demo.options.map((option) => {
              const isSelected = selectedOption.id === option.id;
              return (
                <button
                  key={option.id}
                  onClick={() => handleSelect(option)}
                  className={cn(
                    "flex flex-col text-left p-4 rounded-2xl border transition-all duration-200 text-xs",
                    isSelected
                      ? "border-[#FF4D00] bg-[#FF4D00]/5 shadow-sm"
                      : "border-black/5 bg-[#FAFAFA] hover:border-black/20 text-[#6B6B6B]"
                  )}
                >
                  <span
                    className={cn(
                      "font-semibold mb-1 text-sm tracking-tight",
                      isSelected ? "text-[#FF4D00]" : "text-[#0A0A0A]"
                    )}
                  >
                    {option.title}
                  </span>
                  <span className="text-[11px] text-[#6B6B6B] leading-tight line-clamp-2">
                    {option.description}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Simulated Query Bar */}
          <div className="flex items-center gap-3 p-3.5 rounded-2xl bg-[#FAFAFA] border border-black/10 mb-8 shadow-inner">
            <Search className="w-5 h-5 text-[#FF4D00] shrink-0 ml-1" />
            <span className="text-sm font-mono text-[#0A0A0A] grow">
              {selectedOption.prompt}
            </span>
            <button
              className="px-4 py-2 rounded-xl bg-[#0A0A0A] text-white text-xs font-semibold hover:bg-black transition-colors shrink-0"
              aria-label="Execute illustrative search"
            >
              Trace Evidence
            </button>
          </div>

          {/* Dual Panel: Synthesized Answer + Highlighted Source Evidence */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left: Synthesized Answer */}
            <div className="lg:col-span-6 p-6 rounded-2xl bg-[#FAFAFA] border border-black/5 flex flex-col justify-between min-h-[260px]">
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span className="text-xs font-mono uppercase tracking-wider text-[#6B6B6B]">
                    SYNTHESIZED GROUNDED ANSWER
                  </span>
                </div>
                <p className={cn("text-sm text-[#0A0A0A] leading-relaxed transition-opacity duration-300", isTyping ? "opacity-30" : "opacity-100")}>
                  {selectedOption.answer}
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-black/5 flex items-center justify-between">
                <span className="text-xs font-mono text-[#6B6B6B]">
                  Confidence: {selectedOption.evidence.confidence}
                </span>
                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[#FF4D00]">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>100% Grounded</span>
                </span>
              </div>
            </div>

            {/* Right: Evidence Passage & Citation */}
            <div className="lg:col-span-6 p-6 rounded-2xl bg-[#0B0B0C] text-white border border-black/10 min-h-[260px] flex flex-col justify-between shadow-lg">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-[#FF4D00]" />
                    <span className="text-xs font-mono text-white/80 truncate max-w-[220px]">
                      {selectedOption.evidence.source}
                    </span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-white/10 text-white/70">
                    Page {selectedOption.evidence.page}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-white/5 border border-[#FF4D00]/30 text-xs font-serif leading-relaxed text-white/90 italic">
                  "{selectedOption.evidence.quote}"
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs">
                <span className="text-white/50 font-mono">BBox Coordinates: [142, 280, 520, 390]</span>
                <span className="text-[#FF7A1A] font-semibold flex items-center gap-1">
                  Verified Citation
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </CurtainTransition>
  );
}
