import { useState, useRef, useEffect } from "react";
import { Search, FileText, CheckCircle2, ChevronRight } from "lucide-react";
import { WordReveal } from "@/components/animations/WordReveal";
import { CurtainTransition } from "@/components/animations/CurtainTransition";
import { canPin, loadScroll } from "@/components/motion/scroll";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const DEMO_OPTIONS = [
  {
    id: "contract",
    icon: FileText,
    label: "Contract Analysis",
    description: "Search terms and obligations",
  },
  {
    id: "supplier",
    icon: Search,
    label: "Supplier Intelligence",
    description: "Find supplier relationships",
  },
  {
    id: "pricing",
    icon: DollarSign,
    label: "Pricing Analysis",
    description: "Compare unit prices",
  },
  {
    id: "document",
    icon: FileText,
    label: "Document Search",
    description: "Full-text retrieval",
  },
];

const EXAMPLE_PROMPTS = [
  "Which supplier has the lowest unit price for this product?",
  "What changed in the latest contract amendment?",
  "Which documents support this payment term?",
  "Find contracts associated with this supplier.",
];

// Illustrative demo data
const DEMO_RESPONSE = {
  answer: "Based on the procurement records, TechSupply Ltd offers the lowest unit price at £24.50 per unit for the specified product category.",
  evidence: [
    {
      id: "chunk_142",
      text: "TechSupply Ltd: Unit price £24.50 per unit as of Q2 2024. Volume discount available for orders exceeding 500 units.",
      document: "Supplier_Pricing_Schedule_2024.pdf",
      page: 7,
    },
    {
      id: "chunk_89",
      text: "Comparative analysis shows pricing range between £24.50 and £32.00 across approved suppliers for this category.",
      document: "Procurement_Analysis_Report.pdf",
      page: 12,
    },
  ],
  citation: "TechSupply Ltd pricing verified in Supplier_Pricing_Schedule_2024.pdf, page 7",
};

function DollarSign(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <line x1="12" x2="12" y1="2" y2="22" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  );
}

/**
 * Evidence Demo Section (Scene 05).
 *
 * Features:
 * - Pinned scroll interaction (desktop)
 * - 2x2 selectable demo options
 * - Typed prompt animation
 * - Evidence panel reveal
 * - Citation highlighting
 * - Clearly labeled as illustrative
 */
export function EvidenceDemoSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const demoCardRef = useRef<HTMLDivElement>(null);
  const [selectedOption, setSelectedOption] = useState("pricing");
  const [currentPrompt, setCurrentPrompt] = useState(0);
  const [showEvidence, setShowEvidence] = useState(false);
  const [typedText, setTypedText] = useState("");

  // Typing animation for prompt
  useEffect(() => {
    const prompt = EXAMPLE_PROMPTS[currentPrompt];
    let index = 0;

    const interval = setInterval(() => {
      if (index <= prompt.length) {
        setTypedText(prompt.slice(0, index));
        index++;
      } else {
        clearInterval(interval);
        // Show evidence after typing completes
        setTimeout(() => setShowEvidence(true), 500);
      }
    }, 40);

    return () => clearInterval(interval);
  }, [currentPrompt]);

  // Cycle prompts every 8 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setShowEvidence(false);
      setCurrentPrompt((prev) => (prev + 1) % EXAMPLE_PROMPTS.length);
    }, 8000);

    return () => clearInterval(interval);
  }, []);

  // Pinned scroll (desktop only)
  useEffect(() => {
    if (!canPin()) return;

    const section = sectionRef.current;
    const card = demoCardRef.current;
    if (!section || !card) return;

    let cancelled = false;
    let context: { revert: () => void } | undefined;

    void loadScroll().then(({ gsap }) => {
      if (cancelled) return;

      context = gsap.context(() => {
        gsap.timeline({
          scrollTrigger: {
            trigger: section,
            start: "top top",
            end: "+=100%",
            pin: card,
            pinSpacing: false,
            anticipatePin: 1,
          },
        });
      });
    });

    return () => {
      cancelled = true;
      context?.revert();
    };
  }, []);

  return (
    <section
      id="evidence-demo"
      ref={sectionRef}
      className="relative min-h-[140vh] scroll-mt-24 bg-[#FAFAF9] px-5 py-24 lg:px-8 lg:py-32"
    >
      {/* Curtain transition */}
      <CurtainTransition theme="light" triggerRef={sectionRef} />

      {/* Peach gradient */}
      <div
        className="pointer-events-none absolute left-1/2 top-0 h-[400px] w-[800px] -translate-x-1/2"
        style={{
          background: "radial-gradient(ellipse at top, rgba(251, 146, 60, 0.08), transparent 70%)",
        }}
        aria-hidden="true"
      />

      <div className="relative mx-auto w-full max-w-5xl">
        {/* Heading */}
        <div className="text-center">
          <WordReveal mode="scroll" triggerRef={sectionRef} className="text-display-sm text-balance text-zinc-900">
            Experience Intelligence Through Evidence.
          </WordReveal>
          <p className="mx-auto mt-5 max-w-xl text-[15px] leading-relaxed text-zinc-600">
            Ask a question, inspect the retrieved passage and trace the answer to its source.
          </p>
        </div>

        {/* Technology chips */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-2">
          {["Hybrid Retrieval", "Evidence Binding", "Citation Tracing"].map((tech) => (
            <span
              key={tech}
              className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-[11px] font-medium text-zinc-600 animate-float-slow"
            >
              {tech}
            </span>
          ))}
        </div>

        {/* Demo card */}
        <div ref={demoCardRef} className="relative mt-12">
          <div className="overflow-hidden rounded-3xl border border-zinc-200 bg-white shadow-xl">
            {/* Blue dome background */}
            <div className="relative overflow-hidden bg-gradient-to-b from-blue-50 to-white p-8 pb-12">
              <div
                className="pointer-events-none absolute left-1/2 top-0 h-48 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full opacity-40"
                style={{
                  background: "radial-gradient(circle, rgba(59, 130, 246, 0.3), transparent 70%)",
                }}
                aria-hidden="true"
              />

              {/* Orange icon */}
              <div className="relative mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-400 to-orange-500 shadow-lg">
                <Search className="h-8 w-8 text-white" />
              </div>

              {/* Heading */}
              <h3 className="relative mt-6 text-center text-2xl font-semibold text-zinc-900">
                Explore Procurement Intelligence
              </h3>

              {/* Demo options grid */}
              <div className="relative mt-8 grid grid-cols-2 gap-3">
                {DEMO_OPTIONS.map((option) => (
                  <button
                    key={option.id}
                    onClick={() => setSelectedOption(option.id)}
                    className={cn(
                      "flex items-start gap-3 rounded-xl border-2 bg-white p-4 text-left transition-all duration-300 hover:border-orange-300 hover:shadow-md",
                      selectedOption === option.id
                        ? "border-orange-500 shadow-md ring-2 ring-orange-500/20"
                        : "border-zinc-200"
                    )}
                  >
                    <div
                      className={cn(
                        "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-colors duration-300",
                        selectedOption === option.id
                          ? "bg-orange-100 text-orange-600"
                          : "bg-zinc-100 text-zinc-500"
                      )}
                    >
                      <option.icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1">
                      <div className="text-[14px] font-semibold text-zinc-900">{option.label}</div>
                      <div className="mt-0.5 text-[12px] text-zinc-600">{option.description}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Prompt input */}
            <div className="border-t border-zinc-200 p-6">
              <div className="flex items-center gap-3">
                <div className="flex-1 rounded-xl border border-zinc-300 bg-zinc-50 px-4 py-3">
                  <p className="min-h-[24px] text-[14px] text-zinc-900">
                    {typedText}
                    <span className="animate-pulse">|</span>
                  </p>
                </div>
                <Button
                  size="lg"
                  className="shrink-0 bg-orange-500 hover:bg-orange-600"
                  disabled
                >
                  <ChevronRight className="h-5 w-5" />
                </Button>
              </div>

              {/* Example prompts note */}
              <p className="mt-3 text-[11px] text-zinc-500">
                Example prompts cycle automatically. This is an illustrative demo.
              </p>
            </div>

            {/* Evidence panel */}
            {showEvidence && (
              <div className="animate-rise border-t border-zinc-200 bg-zinc-50 p-6">
                {/* Answer */}
                <div className="rounded-xl border border-zinc-200 bg-white p-4">
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-green-600" />
                    <div>
                      <p className="text-[14px] font-medium text-zinc-900">Answer</p>
                      <p className="mt-2 text-[13px] leading-relaxed text-zinc-700">{DEMO_RESPONSE.answer}</p>
                    </div>
                  </div>
                </div>

                {/* Evidence */}
                <div className="mt-4">
                  <p className="text-[12px] font-medium uppercase tracking-wide text-zinc-500">
                    Source Evidence
                  </p>
                  <div className="mt-3 space-y-3">
                    {DEMO_RESPONSE.evidence.map((evidence, index) => (
                      <div
                        key={evidence.id}
                        className="rounded-lg border-l-2 border-l-orange-500 bg-white p-3 shadow-sm animate-rise"
                        style={{ animationDelay: `${index * 100}ms` }}
                      >
                        <p className="text-[12px] leading-relaxed text-zinc-700">{evidence.text}</p>
                        <div className="mt-2 flex items-center gap-2 text-[11px] text-zinc-500">
                          <FileText className="h-3 w-3" />
                          <span>{evidence.document}</span>
                          <span>•</span>
                          <span>Page {evidence.page}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Citation */}
                <div className="mt-4 rounded-lg bg-orange-50 p-3">
                  <p className="text-[11px] text-orange-900">
                    <strong>Citation:</strong> {DEMO_RESPONSE.citation}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Illustrative notice */}
          <p className="mt-4 text-center text-[11px] text-zinc-500">
            This is an illustrative demonstration. Sign in to query your actual procurement data.
          </p>
        </div>
      </div>
    </section>
  );
}
