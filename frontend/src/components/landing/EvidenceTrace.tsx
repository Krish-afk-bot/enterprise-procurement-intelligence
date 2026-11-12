import { useEffect, useRef, useState } from "react";
import { BadgeCheck, FileText, Link2, Quote, ScrollText, Table2 } from "lucide-react";

import { FlowParticles } from "@/components/motion/FlowParticles";
import { canPin, loadScroll } from "@/components/motion/scroll";
import { cn } from "@/lib/utils";

/**
 * The evidence chain, drawn as the reader scrolls:
 * record → document → retrieved passage → verified claim → citation.
 *
 * The connector line is an SVG path whose dash offset is driven by scroll
 * progress, so the drawing reverses when the reader scrolls back up. Pinned on
 * desktop only; on touch and reduced-motion the five steps stack and the path
 * is drawn in full.
 */
const STEPS = [
  { key: "record", label: "Procurement record", icon: Table2 },
  { key: "document", label: "Document", icon: FileText },
  { key: "passage", label: "Retrieved passage", icon: Quote },
  { key: "claim", label: "Verified claim", icon: BadgeCheck },
  { key: "citation", label: "Citation", icon: Link2 },
];

export function EvidenceTrace() {
  const sectionRef = useRef<HTMLElement>(null);
  const pathRef = useRef<SVGPathElement>(null);
  const barRef = useRef<HTMLSpanElement>(null);
  const [pinned, setPinned] = useState(false);
  const [active, setActive] = useState(STEPS.length - 1);

  useEffect(() => {
    setPinned(canPin());
  }, []);

  useEffect(() => {
    if (!pinned) return;
    const node = sectionRef.current;
    if (!node) return;

    let cancelled = false;
    let context: { revert: () => void } | undefined;
    setActive(0);

    void loadScroll().then(({ gsap, ScrollTrigger }) => {
      if (cancelled) return;
      context = gsap.context(() => {
        ScrollTrigger.create({
          trigger: node,
          start: "top top",
          end: "+=200%",
          pin: true,
          anticipatePin: 1,
          onUpdate: (self) => {
            if (pathRef.current) {
              pathRef.current.style.strokeDashoffset = String(100 - self.progress * 100);
            }
            if (barRef.current) barRef.current.style.transform = `scaleX(${self.progress})`;
            const next = Math.min(STEPS.length - 1, Math.floor(self.progress * STEPS.length));
            setActive((previous) => (previous === next ? previous : next));
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
      id="evidence"
      ref={sectionRef}
      className="relative scroll-mt-24 overflow-hidden border-t border-white/[0.07] bg-ink px-5 py-20 lg:px-8"
    >
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[520px] w-[860px] -translate-x-1/2 -translate-y-1/2 halo opacity-50"
        aria-hidden="true"
      />
      <div
        className={cn(
          "relative mx-auto flex w-full max-w-7xl flex-col justify-center",
          pinned && "h-[100svh] py-16",
        )}
      >
        <div className="max-w-3xl">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-subtle">Evidence chain</p>
          <h2 className="mt-4 text-display-sm text-balance">Every answer can be walked back to its page.</h2>
          <p className="mt-4 text-[14px] leading-relaxed text-muted-foreground">
            The platform records what it retrieved, which passage was used and what was verified. A claim that the
            corpus cannot support is refused rather than guessed.
          </p>
        </div>

        {/* Progress: a hairline that fills with scroll progress. */}
        <div className="mt-10 hidden h-px w-full overflow-hidden bg-white/10 lg:block" aria-hidden="true">
          <span ref={barRef} className="block h-px w-full origin-left bg-white/70" style={{ transform: "scaleX(0)" }} />
        </div>

        <div className="mt-8 grid items-stretch gap-4 lg:mt-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
          <div className="glass relative overflow-hidden rounded-2xl p-5 sm:p-6">
            <div className="flex items-center justify-between">
              <p className="text-[10px] uppercase tracking-[0.16em] text-subtle">source document</p>
              <span className="rounded-sm border border-white/12 px-1.5 py-0.5 font-mono text-[9px] text-subtle">
                page 4
              </span>
            </div>

            {/* The page: real structure, no invented text — the highlighted
                passage stands in for the quote that would be shown. */}
            <div className="relative mt-4 rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <div className="space-y-2">
                {["92%", "84%", "88%", "70%"].map((width) => (
                  <span key={width} className="block h-1.5 rounded-full bg-white/[0.07]" style={{ width }} />
                ))}
              </div>
              <div
                className={cn(
                  "mt-3 rounded-md border-l-2 py-2 pl-3 transition-all duration-500",
                  active >= 1 ? "border-l-white/80 bg-white/[0.08]" : "border-l-white/20 bg-transparent",
                )}
              >
                <span className="mb-2 flex items-center gap-1.5 text-[9px] uppercase tracking-[0.14em] text-subtle">
                  <Quote className="h-2.5 w-2.5" aria-hidden="true" />
                  retrieved passage
                </span>
                <div className="space-y-1.5">
                  <span className="block h-1.5 w-[86%] rounded-full bg-white/35" />
                  <span className="block h-1.5 w-[64%] rounded-full bg-white/25" />
                </div>
              </div>
              <div className="mt-3 space-y-2">
                {["78%", "58%"].map((width) => (
                  <span key={width} className="block h-1.5 rounded-full bg-white/[0.07]" style={{ width }} />
                ))}
              </div>

              {/* The connector emerges from the highlighted passage. */}
              <svg
                className="pointer-events-none absolute -right-16 top-1/2 hidden h-16 w-16 lg:block"
                viewBox="0 0 64 64"
                aria-hidden="true"
              >
                <path
                  ref={pathRef}
                  d="M0 32H64"
                  stroke="rgba(255,255,255,0.6)"
                  strokeWidth="1"
                  pathLength={100}
                  strokeDasharray={100}
                  strokeDashoffset={100}
                  style={{ transition: "stroke-dashoffset 120ms linear" }}
                />
              </svg>
              <FlowParticles
                pathRef={pathRef}
                active={pinned && active >= 2}
                particleCount={4}
                className="-right-16 top-1/2 hidden h-16 w-16 lg:block"
              />
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {STEPS.slice(0, 4).map((step, index) => (
                <div
                  key={step.key}
                  className={cn(
                    "rounded-lg border px-2.5 py-2 transition-colors duration-500",
                    active >= index ? "border-white/20 bg-white/[0.05]" : "border-white/[0.07] bg-transparent",
                  )}
                >
                  <step.icon
                    className={cn("h-3 w-3 transition-colors", active >= index ? "text-white/80" : "text-white/30")}
                    aria-hidden="true"
                  />
                  <p className="mt-1.5 text-[9px] uppercase leading-tight tracking-[0.1em] text-subtle">{step.label}</p>
                </div>
              ))}
            </div>
          </div>

          <div
            className={cn(
              "glass flex flex-col justify-between rounded-2xl p-5 transition-[opacity,transform] duration-500 sm:p-6",
              pinned && active < 2 ? "opacity-30" : "opacity-100",
            )}
          >
            <div>
              <p className="text-[10px] uppercase tracking-[0.16em] text-subtle">extractive answer</p>
              <p
                className={cn(
                  "mt-3 text-[13px] leading-relaxed transition-opacity duration-500",
                  pinned && active < 2 ? "opacity-40" : "opacity-100 text-foreground/90",
                )}
              >
                The amendment schedule sets the applicable unit price for the period; the superseded annex no longer
                governs that line.
              </p>
            </div>

            <div className="mt-5 space-y-2">
              <div
                className={cn(
                  "flex items-center gap-2 rounded-lg border px-2.5 py-2 transition-all duration-500",
                  active >= 3 ? "border-white/20 bg-white/[0.06]" : "border-white/[0.07] bg-transparent",
                )}
              >
                <BadgeCheck
                  className={cn("h-3.5 w-3.5", active >= 3 ? "text-success" : "text-white/25")}
                  aria-hidden="true"
                />
                <span className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground">supported</span>
                <span className="ml-auto font-mono text-[9px] text-subtle">2 passages</span>
              </div>
              <div
                className={cn(
                  "rounded-lg border px-2.5 py-2 transition-all duration-500",
                  active >= 4 ? "border-white/20 bg-white/[0.06]" : "border-white/[0.07] bg-transparent",
                )}
              >
                <span className="flex items-center gap-1.5 text-[9px] uppercase tracking-[0.12em] text-subtle">
                  <ScrollText className="h-2.5 w-2.5" aria-hidden="true" />
                  citation
                </span>
                <p className="mt-1 flex items-center gap-1.5 text-[10.5px] text-muted-foreground">
                  <FileText className="h-2.5 w-2.5" aria-hidden="true" />
                  amendment 2 · p.4 · clause 2.1
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-x-4 gap-y-2">
          {STEPS.map((step, index) => (
            <span
              key={step.key}
              className={cn(
                "flex items-center gap-1.5 text-[10px] uppercase tracking-[0.12em] transition-colors duration-500",
                active >= index ? "text-foreground" : "text-subtle",
              )}
            >
              <span
                className={cn(
                  "h-1 w-1 rounded-full transition-colors",
                  active >= index ? "bg-white" : "bg-white/25",
                )}
                aria-hidden="true"
              />
              {step.label}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
