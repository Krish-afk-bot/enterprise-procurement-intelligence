import { useEffect, useRef, useState } from "react";
import { ChartNoAxesColumn, FileSearch, GitBranch, Layers } from "lucide-react";

import { EvidenceVerificationDemo } from "./capability-demos/EvidenceVerificationDemo";
import { ProcurementSearchDemo } from "./capability-demos/ProcurementSearchDemo";
import { RelationshipGraphDemo } from "./capability-demos/RelationshipGraphDemo";
import { RetrievalFlowDemo } from "./capability-demos/RetrievalFlowDemo";
import { Reveal } from "@/components/motion/Reveal";
import { canPin, loadScroll } from "@/components/motion/scroll";
import { cn } from "@/lib/utils";

/**
 * Interactive capabilities showcase with scroll-driven activation.
 *
 * On desktop with motion enabled, the section pins and scrolling activates each
 * capability in sequence, revealing its working demonstration. On mobile and
 * reduced-motion, capabilities stack vertically with static previews.
 */
const CAPABILITIES = [
  {
    id: "procurement-intelligence",
    icon: ChartNoAxesColumn,
    title: "Procurement Intelligence",
    description: "Search agreements, pricing schedules, amendments and records in one pass.",
    features: ["Structured records", "Tender & award data", "Price analysis"],
    Demo: ProcurementSearchDemo,
  },
  {
    id: "evidence-retrieval",
    icon: Layers,
    title: "Evidence-Based RAG",
    description: "Hybrid retrieval fuses structured rows with document passages and reranks them.",
    features: ["Dense + sparse fusion", "Cross-encoder rerank", "Refusal handling"],
    Demo: RetrievalFlowDemo,
  },
  {
    id: "relationship-intelligence",
    icon: GitBranch,
    title: "Relationship Intelligence",
    description: "Buyers, suppliers, awards and contracts resolved as a traversable network.",
    features: ["Entity resolution", "Graph traversal", "Cross-record queries"],
    Demo: RelationshipGraphDemo,
  },
  {
    id: "evidence-verification",
    icon: FileSearch,
    title: "Evidence Verification",
    description: "Every claim is checked against its cited passage and marked as supported or refused.",
    features: ["Claim-passage matching", "Citation tracking", "Verification scores"],
    Demo: EvidenceVerificationDemo,
  },
];

export function InteractiveCapabilities() {
  const sectionRef = useRef<HTMLElement>(null);
  const progressRef = useRef<HTMLSpanElement>(null);
  const [pinned, setPinned] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    setPinned(canPin());
  }, []);

  useEffect(() => {
    if (!pinned) return;
    const node = sectionRef.current;
    if (!node) return;

    let cancelled = false;
    let context: { revert: () => void } | undefined;

    void loadScroll().then(({ gsap, ScrollTrigger }) => {
      if (cancelled) return;
      context = gsap.context(() => {
        ScrollTrigger.create({
          trigger: node,
          start: "top top",
          end: `+=${CAPABILITIES.length * 100}%`,
          pin: true,
          anticipatePin: 1,
          onUpdate: (self) => {
            if (progressRef.current) {
              progressRef.current.style.transform = `scaleX(${self.progress})`;
            }
            const next = Math.min(CAPABILITIES.length - 1, Math.floor(self.progress * CAPABILITIES.length));
            setActiveIndex((prev) => (prev === next ? prev : next));
          },
        });
      }, node);
    });

    return () => {
      cancelled = true;
      context?.revert();
    };
  }, [pinned]);

  return (
    <section
      id="capabilities-interactive"
      ref={sectionRef}
      className="relative scroll-mt-24 overflow-hidden border-t border-white/[0.07] bg-ink-2 px-5 py-20 lg:px-8"
    >
      <div
        className="pointer-events-none absolute left-1/2 top-1/3 h-[600px] w-[900px] -translate-x-1/2 halo opacity-50"
        aria-hidden="true"
      />

      <div
        className={cn(
          "relative mx-auto flex w-full max-w-7xl flex-col",
          pinned ? "h-[100svh] justify-center py-16" : "justify-start",
        )}
      >
        {/* Header */}
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-2xl">
            {!pinned && <Reveal>
              <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-subtle">Interactive platform</p>
              <h2 className="mt-4 text-display-sm text-balance">Built for the evidence, not the demo.</h2>
              <p className="mt-4 text-[14px] leading-relaxed text-muted-foreground">
                Each demonstration below shows a working system interaction, not a sample result. Scroll to explore.
              </p>
            </Reveal>}
            {pinned && (
              <>
                <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-subtle">Interactive platform</p>
                <h2 className="mt-4 text-display-sm text-balance">Built for the evidence, not the demo.</h2>
                <p className="mt-4 text-[14px] leading-relaxed text-muted-foreground">
                  Each demonstration shows a working system interaction, not a sample result. Scroll to explore.
                </p>
              </>
            )}
          </div>
          {pinned && (
            <p className="hidden font-mono text-[11px] tracking-[0.2em] text-subtle lg:block">
              {String(activeIndex + 1).padStart(2, "0")} / {String(CAPABILITIES.length).padStart(2, "0")}
            </p>
          )}
        </div>

        {/* Progress bar (desktop pinned only) */}
        {pinned && (
          <div className="mt-8 hidden h-px w-full overflow-hidden bg-white/10 lg:block" aria-hidden="true">
            <span
              ref={progressRef}
              className="block h-px w-full origin-left bg-white/70"
              style={{ transform: "scaleX(0)" }}
            />
          </div>
        )}

        {/* Capabilities grid/stack */}
        <div
          className={cn(
            pinned
              ? "relative mt-10 h-[520px]"
              : "mt-12 grid gap-6 md:grid-cols-2",
          )}
        >
          {CAPABILITIES.map((capability, index) => {
            const isActive = pinned ? index === activeIndex : true;
            const Demo = capability.Demo;

            return (
              <article
                key={capability.id}
                className={cn(
                  "glass flex flex-col overflow-hidden rounded-2xl p-6",
                  pinned &&
                    "absolute inset-0 transition-all duration-700 ease-out",
                  pinned && (isActive
                    ? "z-10 translate-y-0 opacity-100"
                    : index < activeIndex
                      ? "pointer-events-none z-0 -translate-y-8 opacity-0"
                      : "pointer-events-none z-0 translate-y-8 opacity-0"),
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2.5">
                      <capability.icon className="h-4 w-4 text-white/60" aria-hidden="true" />
                      <h3 className="text-lg font-medium tracking-tight">{capability.title}</h3>
                    </div>
                    <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">
                      {capability.description}
                    </p>
                  </div>
                  {pinned && (
                    <span className="shrink-0 font-mono text-[10px] tracking-[0.2em] text-subtle">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                  )}
                </div>

                <ul className="mt-4 flex flex-wrap gap-2">
                  {capability.features.map((feature) => (
                    <li
                      key={feature}
                      className="rounded-full border border-white/12 bg-white/[0.04] px-2.5 py-1 text-[10px] text-muted-foreground"
                    >
                      {feature}
                    </li>
                  ))}
                </ul>

                <div className="mt-6 flex-1">
                  <Demo active={isActive} />
                </div>
              </article>
            );
          })}
        </div>

        {/* Navigation hint */}
        {pinned && (
          <p className="mt-6 hidden items-center gap-2 text-[11px] text-subtle lg:flex" aria-hidden="true">
            <span className="h-1 w-1 rounded-full bg-white/40" />
            Scroll to advance through capabilities
          </p>
        )}
      </div>
    </section>
  );
}
