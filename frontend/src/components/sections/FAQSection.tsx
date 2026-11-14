import { useState } from "react";
import { LANDING_CONTENT } from "@/content/landing";
import { WordReveal } from "@/components/animations/WordReveal";
import { ChevronDown, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export function FAQSection() {
  // F6.6: First item open by default
  const [openId, setOpenId] = useState<string>(LANDING_CONTENT.faq.items[0]?.id || "faq-1");

  const toggle = (id: string) => {
    setOpenId((prev) => (prev === id ? "" : id));
  };

  return (
    <section id="faq" className="relative py-28 px-6 bg-[#050505] text-white">
      <div className="max-w-4xl mx-auto">
        {/* Header Stack */}
        <div className="flex flex-col items-center text-center max-w-2xl mx-auto mb-16 gap-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider uppercase bg-white/5 border border-white/10 text-white/80">
            <HelpCircle className="w-3.5 h-3.5 text-[#FF4D00]" />
            <span>{LANDING_CONTENT.faq.badge}</span>
          </div>

          <WordReveal
            as="h2"
            mode="scroll"
            className="text-3xl sm:text-5xl font-bold tracking-tight text-white leading-tight w-full"
          >
            {LANDING_CONTENT.faq.heading}
          </WordReveal>
        </div>

        {/* Accordion List with Left Chevron and ARIA tags */}
        <div className="flex flex-col gap-3">
          {LANDING_CONTENT.faq.items.map((item) => {
            const isOpen = openId === item.id;
            return (
              <div
                key={item.id}
                className={cn(
                  "rounded-2xl border transition-all duration-200 overflow-hidden",
                  isOpen
                    ? "bg-[#141414] border-[#FF4D00]/40 shadow-lg"
                    : "bg-[#0B0B0C] border-white/10 hover:border-white/20"
                )}
              >
                <button
                  type="button"
                  onClick={() => toggle(item.id)}
                  aria-expanded={isOpen}
                  aria-controls={`faq-answer-${item.id}`}
                  className="w-full flex items-center justify-between p-6 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-[#FF4D00]"
                >
                  <div className="flex items-center gap-4">
                    <ChevronDown
                      className={cn(
                        "w-5 h-5 text-[#FF4D00] shrink-0 transition-transform duration-300",
                        isOpen ? "transform rotate-180" : ""
                      )}
                    />
                    <span className="text-base sm:text-lg font-semibold text-white tracking-tight">
                      {item.question}
                    </span>
                  </div>
                </button>

                {isOpen && (
                  <div
                    id={`faq-answer-${item.id}`}
                    className="px-6 pb-6 pt-1 text-sm text-white/70 leading-relaxed pl-15"
                  >
                    {item.answer}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
