import { useEffect, useRef, useState } from "react";
import {
  BadgeCheck,
  Banknote,
  FileSearch,
  FileText,
  GitBranch,
  Layers,
  Users,
} from "lucide-react";

import { canPin, loadScroll } from "@/components/motion/scroll";
import { cn } from "@/lib/utils";

/**
 * Pinned horizontal showcase of the platform's five surfaces.
 *
 * The track is translated by its measured overflow — never a fixed guess — and
 * the scroll distance is recalculated whenever the layout invalidates. On touch
 * and reduced-motion the same panels stack vertically, which is why the base
 * layout is a column and the desktop rail is opted into.
 */
const PANELS = [
  {
    step: "01",
    icon: FileSearch,
    title: "Procurement Intelligence",
    body: "Search agreements, pricing schedules, amendments and procurement records in one pass, with the passage and page attached to every hit.",
    meta: "records · tenders · awards",
  },
  {
    step: "02",
    icon: Layers,
    title: "Evidence-Based RAG",
    body: "Hybrid retrieval fuses structured rows with document passages, reranks them, and answers only from what it retrieved.",
    meta: "retrieval · rerank · refusal",
  },
  {
    step: "03",
    icon: GitBranch,
    title: "Relationship Intelligence",
    body: "Buyers, suppliers, awards and contracts are resolved to one another, so a question can cross records without losing the thread.",
    meta: "buyer · supplier · award",
  },
  {
    step: "04",
    icon: FileText,
    title: "Document Intelligence",
    body: "Ingestion reports its stage, the pages it extracted, whether OCR or a vision model was used, and whether a file was ever downloaded.",
    meta: "ingest · extract · cite",
  },
  {
    step: "05",
    icon: Banknote,
    title: "Procurement Analytics",
    body: "Counts, coverage and activity read from the workspace database. A value the records do not carry is labelled, not filled in.",
    meta: "coverage · activity · value",
  },
];

export function CapabilityRail() {
  const sectionRef = useRef<HTMLElement>(null);
  const trackRef = useRef<HTMLOListElement>(null);
  const barRef = useRef<HTMLSpanElement>(null);
  const [pinned, setPinned] = useState(false);

  useEffect(() => {
    setPinned(canPin());
  }, []);

  useEffect(() => {
    if (!pinned) return;
    const section = sectionRef.current;
    const track = trackRef.current;
    if (!section || !track) return;

    let cancelled = false;
    let context: { revert: () => void } | undefined;

    void loadScroll().then(({ gsap }) => {
      if (cancelled) return;
      context = gsap.context(() => {
        const travel = () => Math.max(0, track.scrollWidth - window.innerWidth);
        gsap.to(track, {
          x: () => -travel(),
          ease: "none",
          scrollTrigger: {
            trigger: section,
            start: "top top",
            end: () => `+=${travel()}`,
            pin: true,
            scrub: 0.5,
            anticipatePin: 1,
            invalidateOnRefresh: true,
            onUpdate: (self) => {
              if (barRef.current) barRef.current.style.transform = `scaleX(${self.progress})`;
            },
          },
        });
      }, section);
    });

    return () => {
      cancelled = true;
      context?.revert();
    };
  }, [pinned]);

  return (
    <section
      id="capabilities"
      ref={sectionRef}
      className={cn(
        "relative scroll-mt-24 overflow-hidden border-t border-white/[0.07] bg-ink-2",
        pinned ? "h-[100svh]" : "py-20 lg:py-24",
      )}
    >
      <div className="pointer-events-none absolute inset-0 grid-lines opacity-30" aria-hidden="true" />
      <div className={cn("relative flex h-full min-h-0 flex-col", pinned && "pt-16")}>
        <div className="mx-auto flex w-full max-w-7xl flex-wrap items-end justify-between gap-4 px-5 lg:px-8">
          <div className="max-w-2xl">
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-subtle">Platform capabilities</p>
            <h2 className="mt-3 text-display-sm text-balance">One layer, five surfaces.</h2>
          </div>
          <p className="hidden max-w-xs text-[12px] leading-relaxed text-muted-foreground lg:block">
            Each panel is a layout preview of a working surface. Figures are never invented to fill a card.
          </p>
        </div>

        <ol
          ref={trackRef}
          className={cn(
            "will-change-transform",
            pinned
              ? "mt-8 flex items-center gap-6 px-[6vw]"
              : "mx-auto mt-10 grid w-full max-w-7xl gap-5 px-5 md:grid-cols-2 lg:grid-cols-3 lg:px-8",
          )}
        >
          {PANELS.map((panel) => (
            <li
              key={panel.title}
              className={cn(
                "glass flex flex-col overflow-hidden rounded-2xl",
                pinned ? "w-[min(62vw,700px)] shrink-0 p-6" : "p-5",
              )}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] tracking-[0.2em] text-subtle">{panel.step}</span>
                <panel.icon className="h-4 w-4 text-white/50" aria-hidden="true" />
              </div>
              <h3 className="mt-5 text-xl font-medium tracking-tight">{panel.title}</h3>
              <p className="mt-2.5 max-w-lg text-[13px] leading-relaxed text-muted-foreground">{panel.body}</p>
              <div className="mt-6 flex-1 rounded-xl border border-white/[0.08] bg-ink/60 p-4">
                <RailPreview index={Number(panel.step) - 1} />
              </div>
              <p className="mt-4 text-[10px] uppercase tracking-[0.14em] text-subtle">{panel.meta}</p>
            </li>
          ))}
        </ol>

        <div className={cn("mx-auto mt-auto w-full max-w-7xl px-5 pt-6 lg:px-8", !pinned && "mt-6")}>
          <div className="flex items-center gap-4">
            <span className="hidden h-px flex-1 overflow-hidden bg-white/10 lg:block" aria-hidden="true">
              <span ref={barRef} className="block h-px w-full origin-left bg-white/60" style={{ transform: "scaleX(0)" }} />
            </span>
            <p className="hidden text-[10px] uppercase tracking-[0.16em] text-subtle lg:block">scroll to advance</p>
            <p className="text-[10px] uppercase tracking-[0.16em] text-subtle lg:hidden">
              {PANELS.length} surfaces · one vocabulary
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------- previews */

function RailPreview({ index }: { index: number }) {
  if (index === 0) return <SearchSurface />;
  if (index === 1) return <RetrievalSurface />;
  if (index === 2) return <NetworkSurface />;
  if (index === 3) return <DocumentSurface />;
  return <AnalyticsSurface />;
}

function SearchSurface() {
  return (
    <div>
      <div className="flex items-center gap-2 rounded-lg border border-white/12 bg-white/[0.04] px-3 py-2">
        <FileSearch className="h-3.5 w-3.5 text-white/45" aria-hidden="true" />
        <span className="text-[11px] text-muted-foreground">indemnity cap in the master agreement</span>
      </div>
      <div className="mt-3 space-y-2">
        {[
          ["master agreement · p.18", "0.94"],
          ["amendment 1 · p.3", "0.77"],
          ["terms · p.2", "0.41"],
        ].map(([label, score]) => (
          <div key={label} className="flex items-center gap-3 rounded-lg border border-white/[0.07] bg-white/[0.02] px-3 py-2">
            <FileText className="h-3 w-3 text-white/40" aria-hidden="true" />
            <span className="flex-1 truncate text-[10.5px] text-muted-foreground">{label}</span>
            <span className="font-mono text-[9px] text-subtle">{score}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RetrievalSurface() {
  return (
    <div className="space-y-2">
      <div className="rounded-lg border border-white/12 bg-white/[0.04] px-3 py-2">
        <p className="text-[9px] uppercase tracking-[0.12em] text-subtle">question</p>
        <p className="mt-1 text-[10.5px] text-muted-foreground">Does the cap survive the amendment?</p>
      </div>
      {[
        ["dense · 14 passages", 82],
        ["sparse · 9 passages", 61],
        ["structured · 3 rows", 38],
      ].map(([label, width]) => (
        <div key={String(label)} className="rounded-lg border border-white/[0.07] px-3 py-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground">{label}</span>
            <span className="text-[9px] uppercase tracking-wider text-subtle">kept</span>
          </div>
          <span className="mt-1.5 block h-1 rounded-full bg-white/25" style={{ width: `${width}%` }} />
        </div>
      ))}
    </div>
  );
}

function NetworkSurface() {
  return (
    <div className="relative h-[150px]">
      <svg className="absolute inset-0 h-full w-full" aria-hidden="true">
        <line x1="20%" y1="30%" x2="50%" y2="50%" stroke="rgba(255,255,255,0.22)" />
        <line x1="50%" y1="50%" x2="80%" y2="28%" stroke="rgba(255,255,255,0.22)" />
        <line x1="50%" y1="50%" x2="74%" y2="78%" stroke="rgba(255,255,255,0.14)" />
        <line x1="50%" y1="50%" x2="24%" y2="76%" stroke="rgba(255,255,255,0.14)" />
      </svg>
      <span className="absolute left-1/2 top-1/2 flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/25 bg-white/[0.08] text-[8px] uppercase tracking-[0.1em] text-white/80">
        award
      </span>
      {[
        ["buyer", "18%", "26%"],
        ["supplier", "80%", "24%"],
        ["contract", "74%", "74%"],
        ["price rows", "22%", "72%"],
      ].map(([label, left, top]) => (
        <span
          key={label}
          className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/12 bg-ink px-2 py-0.5 text-[8.5px] uppercase tracking-[0.1em] text-muted-foreground"
          style={{ left, top }}
        >
          {label}
        </span>
      ))}
    </div>
  );
}

function DocumentSurface() {
  return (
    <div className="flex gap-3">
      <div className="w-16 shrink-0 rounded border border-white/12 bg-white/[0.03] p-2">
        {["100%", "82%", "90%", "64%", "88%", "72%"].map((width) => (
          <span key={width} className="mb-1 block h-1 rounded-full bg-white/15" style={{ width }} />
        ))}
      </div>
      <div className="min-w-0 flex-1 space-y-2">
        {[
          ["extracted", "12 pages"],
          ["ocr", "used on p.4"],
          ["downloaded", "local file"],
        ].map(([label, value]) => (
          <div key={label} className="flex items-center justify-between rounded-lg border border-white/[0.07] px-2.5 py-1.5">
            <span className="text-[9.5px] uppercase tracking-[0.1em] text-subtle">{label}</span>
            <span className="text-[10px] text-muted-foreground">{value}</span>
          </div>
        ))}
        <div className="flex items-center gap-1.5 pt-1">
          <BadgeCheck className="h-3 w-3 text-white/50" aria-hidden="true" />
          <span className="text-[9.5px] text-muted-foreground">citable</span>
        </div>
      </div>
    </div>
  );
}

function AnalyticsSurface() {
  const bars = [38, 62, 48, 76, 58, 88, 70];
  return (
    <div>
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[9px] uppercase tracking-[0.12em] text-subtle">documents searchable</p>
          <p className="mt-1 flex items-center gap-2 text-lg font-medium tnum">
            9 <span className="text-[10px] font-normal text-subtle">of 9</span>
          </p>
        </div>
        <Users className="h-4 w-4 text-white/40" aria-hidden="true" />
      </div>
      <div className="mt-3 flex h-16 items-end gap-1.5">
        {bars.map((height, index) => (
          <span
            key={index}
            className="flex-1 rounded-sm bg-gradient-to-t from-white/10 to-white/40"
            style={{ height: `${height}%` }}
          />
        ))}
      </div>
      <div className="mt-2 flex items-center justify-between border-t border-white/[0.07] pt-2 text-[9px] uppercase tracking-[0.1em] text-subtle">
        <span>14 days</span>
        <span>from the database</span>
      </div>
    </div>
  );
}
