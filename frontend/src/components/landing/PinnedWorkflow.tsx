import { useEffect, useRef, useState } from "react";
import {
  BadgeCheck,
  Bot,
  Check,
  FileSearch,
  FileText,
  GitBranch,
  Layers,
  Search,
  Sparkles,
} from "lucide-react";

import { canPin, loadScroll } from "@/components/motion/scroll";
import { cn } from "@/lib/utils";

/**
 * Pinned storytelling: Discover → Retrieve → Analyze → Verify.
 *
 * On a desktop with motion enabled the section pins for roughly three
 * viewport-heights and the scroll position selects the stage, so the sequence
 * reverses exactly when the reader scrolls back up. Everywhere else (tablet,
 * phone, reduced motion) the same four stages render as an ordinary vertical
 * list — no pin, no hijacked scrolling, nothing hidden.
 */
const STAGES = [
  {
    step: "01",
    title: "Discover",
    icon: FileSearch,
    body: "One query searches procurement records and the documents behind them, not a single index or a single file.",
    caption: "Search across records and documents",
  },
  {
    step: "02",
    title: "Retrieve",
    icon: Layers,
    body: "Hybrid retrieval fuses structured rows and document passages, then reranks them against the question.",
    caption: "Fuse and rerank the candidates",
  },
  {
    step: "03",
    title: "Analyze",
    icon: GitBranch,
    body: "Buyer, supplier, award and contract references are resolved to one another, so an answer can cross records.",
    caption: "Resolve the relationships",
  },
  {
    step: "04",
    title: "Verify",
    icon: BadgeCheck,
    body: "Each statement is checked against the passage it cites, and the evidence is shown with the answer.",
    caption: "Attach the evidence",
  },
];

export function PinnedWorkflow() {
  const sectionRef = useRef<HTMLElement>(null);
  const fillRef = useRef<HTMLSpanElement>(null);
  const [pinned, setPinned] = useState(false);
  const [active, setActive] = useState(0);

  // Pin only when the environment supports it. The state decides the layout:
  // pinned stages overlap in one frame; unpinned stages stack.
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
          end: "+=280%",
          pin: true,
          anticipatePin: 1,
          onUpdate: (self) => {
            if (fillRef.current) fillRef.current.style.transform = `scaleY(${self.progress})`;
            const next = Math.min(STAGES.length - 1, Math.floor(self.progress * STAGES.length));
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
      id="how-it-works"
      ref={sectionRef}
      className="relative scroll-mt-24 overflow-hidden border-t border-white/[0.07] bg-ink-2 px-5 py-20 lg:px-8"
    >
      <div className="pointer-events-none absolute inset-0 grid-lines opacity-40" aria-hidden="true" />
      <div
        className="pointer-events-none absolute left-1/2 top-1/3 h-[520px] w-[820px] -translate-x-1/2 halo opacity-60"
        aria-hidden="true"
      />

      <div
        className={cn(
          "relative mx-auto flex w-full max-w-7xl flex-col justify-center",
          pinned && "h-[calc(100svh-0px)] py-16",
        )}
      >
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-2xl">
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-subtle">How EPI works</p>
            <h2 className="mt-4 text-display-sm text-balance">From a record to a verified answer.</h2>
          </div>
          <p className="hidden font-mono text-[11px] tracking-[0.2em] text-subtle lg:block">
            {STAGES[active].step} / {String(STAGES.length).padStart(2, "0")}
          </p>
        </div>

        <div className="mt-10 grid gap-8 lg:mt-14 lg:grid-cols-[minmax(0,260px)_minmax(0,1fr)] lg:gap-14">
          {/* The rail exists only in the pinned layout; stacked stages carry
              their own headings on smaller screens. */}
          <ol className="relative hidden lg:block" aria-label="Workflow stages">
            <span className="absolute left-0 top-2 h-[calc(100%-1rem)] w-px bg-white/10" aria-hidden="true" />
            <span
              ref={fillRef}
              className="absolute left-0 top-2 h-[calc(100%-1rem)] w-px origin-top bg-white/70"
              style={{ transform: "scaleY(0)" }}
              aria-hidden="true"
            />
            {STAGES.map((stage, index) => {
              const current = index === active;
              return (
                <li key={stage.step} className="relative pl-6">
                  <span
                    aria-hidden="true"
                    className={cn(
                      "absolute -left-[3px] top-2.5 h-[7px] w-[7px] rounded-full border transition-colors duration-500",
                      current
                        ? "border-white bg-white shadow-[0_0_16px_2px_rgba(255,255,255,0.35)]"
                        : index < active
                          ? "border-white/60 bg-white/50"
                          : "border-white/25 bg-ink-2",
                    )}
                  />
                  <div className={cn("py-2 transition-opacity duration-500", current ? "opacity-100" : "opacity-45")}>
                    <p className="font-mono text-[10px] tracking-[0.2em] text-subtle">{stage.step}</p>
                    <p className="mt-1 text-[15px] font-medium tracking-tight">{stage.title}</p>
                    <p className="mt-1.5 text-[12px] leading-relaxed text-muted-foreground">{stage.body}</p>
                  </div>
                </li>
              );
            })}
          </ol>

          <div className={cn(pinned ? "relative h-[420px]" : "space-y-6")}>
            {STAGES.map((stage, index) => {
              const current = index === active;
              return (
                <article
                  key={stage.step}
                  className={cn(
                    "glass overflow-hidden rounded-2xl p-5 sm:p-6",
                    pinned &&
                      "absolute inset-0 transition-[opacity,transform] duration-500 ease-out",
                    pinned && (current ? "z-10 opacity-100" : "pointer-events-none z-0 translate-y-3 opacity-0"),
                  )}
                >
                  <div className="flex items-center gap-2.5 lg:hidden">
                    <span className="font-mono text-[10px] tracking-[0.2em] text-subtle">{stage.step}</span>
                    <stage.icon className="h-3.5 w-3.5 text-white/60" aria-hidden="true" />
                    <p className="text-[13px] font-medium">{stage.title}</p>
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-3 lg:mt-0">
                    <p className="text-[11px] uppercase tracking-[0.16em] text-subtle">{stage.caption}</p>
                    <span className="flex items-center gap-1.5 rounded-full border border-white/10 px-2 py-0.5 text-[9px] uppercase tracking-[0.14em] text-subtle">
                      <span className="h-1 w-1 rounded-full bg-white/60" aria-hidden="true" />
                      live surface
                    </span>
                  </div>
                  <div className="mt-4">
                    <StageVisual index={index} />
                  </div>
                </article>
              );
            })}
          </div>
        </div>

        <p className="mt-6 hidden items-center gap-2 text-[11px] text-subtle lg:flex" aria-hidden="true">
          <Sparkles className="h-3 w-3" />
          Scroll to advance the sequence; it reverses when you scroll back.
        </p>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------- visuals */

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/10 bg-ink/70 p-3 shadow-[0_1px_0_0_rgba(255,255,255,0.05)_inset] sm:p-4">
      {children}
    </div>
  );
}

function StageVisual({ index }: { index: number }) {
  if (index === 0) return <DiscoverVisual />;
  if (index === 1) return <RetrieveVisual />;
  if (index === 2) return <AnalyzeVisual />;
  return <VerifyVisual />;
}

function DiscoverVisual() {
  return (
    <Shell>
      <div className="flex items-center gap-2 rounded-lg border border-white/12 bg-white/[0.04] px-3 py-2">
        <Search className="h-3.5 w-3.5 text-white/45" aria-hidden="true" />
        <span className="text-[11px] text-muted-foreground">price schedule for industrial equipment</span>
      </div>
      <div className="mt-3 space-y-2">
        {["master agreement", "pricing schedule · page 12", "amendment 2 · clause 4"].map((label, row) => (
          <div
            key={label}
            className={cn(
              "flex items-center gap-3 rounded-lg border px-3 py-2.5",
              row === 0 ? "border-white/20 bg-white/[0.05]" : "border-white/[0.07] bg-white/[0.015]",
            )}
          >
            <FileText className="h-3.5 w-3.5 shrink-0 text-white/45" aria-hidden="true" />
            <span className="min-w-0 flex-1 text-[11px] text-muted-foreground">{label}</span>
            <span className="rounded-sm border border-white/15 px-1.5 py-0.5 text-[8px] uppercase tracking-wider text-subtle">
              {row === 0 ? "record" : "document"}
            </span>
          </div>
        ))}
      </div>
    </Shell>
  );
}

function RetrieveVisual() {
  return (
    <Shell>
      <div className="grid items-center gap-4 sm:grid-cols-[minmax(0,0.8fr)_auto_minmax(0,1.2fr)]">
        <div className="rounded-lg border border-white/12 bg-white/[0.04] p-3">
          <p className="text-[9px] uppercase tracking-[0.14em] text-subtle">question</p>
          <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">Which price applies to the 2024 order?</p>
          <div className="mt-2 flex gap-1">
            {["dense", "sparse", "structured"].map((t) => (
              <span key={t} className="rounded-sm border border-white/12 px-1 py-0.5 text-[8px] text-subtle">
                {t}
              </span>
            ))}
          </div>
        </div>
        <div className="hidden sm:block" aria-hidden="true">
          <svg width="46" height="96" viewBox="0 0 46 96" fill="none">
            <path d="M0 48H45" stroke="rgba(255,255,255,0.18)" strokeWidth="1" />
            <path d="M12 48C24 48 22 12 45 12" stroke="rgba(255,255,255,0.3)" strokeWidth="1" />
            <path d="M12 48C24 48 22 84 45 84" stroke="rgba(255,255,255,0.3)" strokeWidth="1" />
            <circle cx="45" cy="12" r="2" fill="white" fillOpacity="0.7" />
            <circle cx="45" cy="48" r="2" fill="white" fillOpacity="0.4" />
            <circle cx="45" cy="84" r="2" fill="white" fillOpacity="0.25" />
          </svg>
        </div>
        <div className="space-y-2">
          {[
            { label: "page 12 · pricing schedule", score: "0.93", width: "w-[86%]" },
            { label: "amendment 2 · clause 4", score: "0.81", width: "w-[68%]" },
            { label: "master agreement · annex B", score: "0.54", width: "w-[41%]" },
          ].map((row) => (
            <div key={row.label} className="rounded-lg border border-white/[0.07] bg-white/[0.02] px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-[10.5px] text-muted-foreground">{row.label}</span>
                <span className="font-mono text-[9px] text-subtle">{row.score}</span>
              </div>
              <span className={cn("mt-1.5 block h-1 rounded-full bg-white/25", row.width)} />
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}

function AnalyzeVisual() {
  const nodes = [
    { label: "Buyer", x: "14%", y: "22%" },
    { label: "Award", x: "72%", y: "18%" },
    { label: "Contract", x: "20%", y: "74%" },
    { label: "Supplier", x: "76%", y: "72%" },
  ];
  return (
    <Shell>
      <div className="relative h-[168px]">
        <svg className="absolute inset-0 h-full w-full" aria-hidden="true">
          <line x1="24%" y1="30%" x2="76%" y2="70%" stroke="rgba(255,255,255,0.16)" strokeWidth="1" />
          <line x1="24%" y1="76%" x2="50%" y2="50%" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
          <line x1="50%" y1="50%" x2="78%" y2="24%" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
          <line x1="50%" y1="50%" x2="76%" y2="72%" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        </svg>
        <span className="absolute left-1/2 top-1/2 flex h-12 w-12 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/25 bg-white/[0.08] text-[9px] uppercase tracking-[0.12em] text-white/80 shadow-[0_0_28px_-6px_rgba(255,255,255,0.5)]">
          record
        </span>
        {nodes.map((node) => (
          <span
            key={node.label}
            className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/12 bg-ink px-2.5 py-1 text-[9px] uppercase tracking-[0.1em] text-muted-foreground"
            style={{ left: node.x, top: node.y }}
          >
            {node.label}
          </span>
        ))}
      </div>
      <p className="mt-1 flex items-center gap-1.5 text-[9.5px] uppercase tracking-[0.12em] text-subtle">
        <GitBranch className="h-3 w-3" aria-hidden="true" />
        relationships resolved from the same records
      </p>
    </Shell>
  );
}

function VerifyVisual() {
  return (
    <Shell>
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-white/20 bg-white/[0.06]">
          <Bot className="h-3 w-3 text-white/70" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="text-[11.5px] leading-relaxed text-foreground/90">
            The price schedule in amendment 2 applies from 1 April; the earlier annex is superseded for that line.
          </p>
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            <span className="inline-flex items-center gap-1 rounded-full border border-white/15 bg-white/[0.05] px-2 py-0.5 text-[9px] text-muted-foreground">
              <FileText className="h-2.5 w-2.5" aria-hidden="true" />
              amendment 2 · p.4
            </span>
            <span className="inline-flex items-center gap-1 rounded-full border border-white/15 bg-white/[0.05] px-2 py-0.5 text-[9px] text-muted-foreground">
              <FileText className="h-2.5 w-2.5" aria-hidden="true" />
              pricing schedule · p.12
            </span>
          </div>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2 rounded-lg border border-white/12 bg-white/[0.035] px-3 py-2">
        <BadgeCheck className="h-3.5 w-3.5 text-white/70" aria-hidden="true" />
        <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">verified against cited passages</span>
        <Check className="ml-auto h-3 w-3 text-success" aria-hidden="true" />
      </div>
    </Shell>
  );
}
