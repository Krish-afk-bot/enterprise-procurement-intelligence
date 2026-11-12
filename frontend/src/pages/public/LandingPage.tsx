import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BadgeCheck,
  ChartNoAxesColumn,
  ChevronDown,
  FileSearch,
  FileStack,
  GitBranch,
  Layers,
  Link2,
  ScanText,
  ShieldCheck,
  ShieldQuestion,
  Sparkles,
  TriangleAlert,
  Users,
} from "lucide-react";

import { EvidenceTrace } from "@/components/landing/EvidenceTrace";
import { Reveal } from "@/components/motion/Reveal";
import { canPin, loadScroll } from "@/components/motion/scroll";
import { LazyWaveHero } from "@/components/three/hero/LazyWaveHero";
import { Button } from "@/components/ui/button";

const PILLARS = [
  {
    icon: ChartNoAxesColumn,
    title: "Procurement Intelligence",
    body: "Structured procurement data, tender and award analysis, and buyer and supplier insight in one place.",
    points: ["Structured procurement records", "Tender and award analysis", "Buyer and supplier insight"],
  },
  {
    icon: Link2,
    title: "Evidence-Based RAG",
    body: "Retrieval that answers from the documents you hold, and shows the page each statement came from.",
    points: ["Document retrieval", "Source-backed answers", "Citation traceability"],
  },
  {
    icon: GitBranch,
    title: "Relationship Intelligence",
    body: "Suppliers, contracts, amendments and awards modelled as a network you can traverse from any record.",
    points: ["Supplier relationships", "Procurement networks", "Contract and award connections"],
  },
];

const CAPABILITIES = [
  {
    icon: FileSearch,
    title: "Procurement Search",
    body: "One query across agreements, pricing schedules, amendments and compliance records, with the passage and page attached.",
    preview: <SearchPreview />,
  },
  {
    icon: FileStack,
    title: "Document Intelligence",
    body: "Ingestion reports its stage, the pages it extracted, and whether OCR or a vision model was used.",
    preview: <DocumentPreview />,
  },
  {
    icon: Users,
    title: "Supplier Intelligence",
    body: "Contracts, price rows, documents and certificates that reference a supplier, resolved to one record.",
    preview: <SupplierPreview />,
  },
  {
    icon: ShieldCheck,
    title: "Evidence & Citation Tracking",
    body: "Each statement is checked against the passage it cites, and the outcome is shown as supported, partial or refused.",
    preview: <EvidencePreview />,
  },
];

/**
 * A dozen static dust motes with different speeds and depths. Hand-placed rather
 * than random so the layer is identical on every paint and never flickers.
 */
const PARTICLES = [
  { left: "12%", top: "32%", size: 2, opacity: 0.55, delay: 0, duration: 11 },
  { left: "22%", top: "64%", size: 1, opacity: 0.35, delay: 1.4, duration: 14 },
  { left: "31%", top: "24%", size: 1, opacity: 0.3, delay: 2.8, duration: 12 },
  { left: "44%", top: "18%", size: 2, opacity: 0.4, delay: 0.7, duration: 16 },
  { left: "57%", top: "28%", size: 1, opacity: 0.5, delay: 3.4, duration: 13 },
  { left: "68%", top: "56%", size: 2, opacity: 0.3, delay: 1.1, duration: 15 },
  { left: "78%", top: "34%", size: 1, opacity: 0.45, delay: 2.2, duration: 12 },
  { left: "88%", top: "62%", size: 1, opacity: 0.3, delay: 4, duration: 17 },
  { left: "18%", top: "78%", size: 1, opacity: 0.25, delay: 2.5, duration: 18 },
  { left: "36%", top: "82%", size: 2, opacity: 0.4, delay: 0.4, duration: 15 },
  { left: "63%", top: "76%", size: 1, opacity: 0.3, delay: 3, duration: 13 },
  { left: "82%", top: "80%", size: 1, opacity: 0.35, delay: 1.8, duration: 16 },
];

const TRUST = [
  {
    icon: Layers,
    title: "Numbers come from the database",
    body: "Document, page, chunk, supplier, contract and price counts are read from the workspace database. A value that does not exist is labelled as not recorded rather than shown as zero.",
  },
  {
    icon: Sparkles,
    title: "Model availability is stated",
    body: "When no language model is configured, answers are composed from retrieved passages in extractive mode and the workspace says so on screen.",
  },
  {
    icon: TriangleAlert,
    title: "Refusals instead of guesses",
    body: "If the corpus does not support a question, the platform returns no verified evidence and explains what it could not find.",
  },
];

export function LandingPage() {
  return (
    <div className="bg-ink text-foreground">
      <Hero />
      <Platform />
      <Capabilities />
      <EvidenceTrace />
      <Trust />
      <ClosingCta />
    </div>
  );
}

/* ------------------------------------------------------------------ hero */

/**
 * A very small pointer parallax: the scene shifts by at most 14px. It is
desktop-only, pointer-driven through a ref so React never re-renders on move,
and disabled entirely for reduced motion or a coarse pointer.
 */
function useSceneParallax<T extends HTMLElement>() {
  const ref = useRef<T>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fine || reduce) return;

    let frame = 0;
    let targetX = 0;
    let targetY = 0;

    const apply = () => {
      frame = 0;
      node.style.transform = `translate3d(${targetX.toFixed(1)}px, ${targetY.toFixed(1)}px, 0)`;
    };

    const onMove = (event: PointerEvent) => {
      targetX = (event.clientX / window.innerWidth - 0.5) * -14;
      targetY = (event.clientY / window.innerHeight - 0.5) * -10;
      if (!frame) frame = window.requestAnimationFrame(apply);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, []);

  return ref;
}

function Hero() {
  const parallaxRef = useSceneParallax<HTMLDivElement>();
  const wrapRef = useRef<HTMLDivElement>(null);
  const sectionRef = useRef<HTMLElement>(null);
  const sceneRef = useRef<HTMLDivElement>(null);
  const copyRef = useRef<HTMLDivElement>(null);
  const gridRef = useRef<HTMLDivElement>(null);

  // The hero is pinned for a short runway so the copy can scale back and the
  // environment can push forward, handing off to the introduction instead of
  // simply scrolling away. Pinning is desktop-only and off for reduced motion,
  // where the hero behaves as a normal first screen.
  useEffect(() => {
    if (!canPin()) return;
    const wrap = wrapRef.current;
    if (!wrap || !sectionRef.current) return;

    let cancelled = false;
    let context: { revert: () => void } | undefined;

    void loadScroll().then(({ gsap }) => {
      if (cancelled) return;
      context = gsap.context(() => {
        gsap
          .timeline({
            scrollTrigger: {
              trigger: sectionRef.current,
              start: "top top",
              end: "+=65%",
              pin: true,
              scrub: 0.6,
              anticipatePin: 1,
            },
          })
          .to(copyRef.current, { yPercent: -14, scale: 0.93, opacity: 0.12, ease: "none" }, 0)
          .to(sceneRef.current, { scale: 1.14, yPercent: 3, ease: "none" }, 0)
          .to(gridRef.current, { scale: 1.18, opacity: 0.2, ease: "none" }, 0);
      }, wrap);
    });

    return () => {
      cancelled = true;
      context?.revert();
    };
  }, []);

  return (
    <div ref={wrapRef} className="relative">
      <section
        id="hero"
        ref={sectionRef}
        className="relative isolate flex min-h-[100svh] flex-col justify-center overflow-hidden px-5 pb-20 pt-32 lg:px-8"
      >
        <div ref={sceneRef} className="absolute inset-[-16px] origin-center" aria-hidden="true">
          <div
            ref={parallaxRef}
            className="absolute inset-0 transition-transform duration-300 ease-out motion-reduce:transition-none"
          >
            <LazyWaveHero />
          </div>
        </div>
      {/* The grid and scrim sit above the canvas and below the copy. */}
      <div ref={gridRef} className="pointer-events-none absolute inset-0 grid-lines opacity-70" aria-hidden="true" />
      <div className="pointer-events-none absolute inset-0 hero-scrim" aria-hidden="true" />
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[680px] w-[680px] -translate-x-1/2 -translate-y-1/2 halo animate-pulse-soft"
        aria-hidden="true"
      />
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        {PARTICLES.map((particle) => (
          <span
            key={`${particle.left}-${particle.top}`}
            className="absolute rounded-full bg-white animate-float-slow motion-reduce:animate-none"
            style={{
              left: particle.left,
              top: particle.top,
              width: particle.size,
              height: particle.size,
              opacity: particle.opacity,
              animationDelay: `${particle.delay}s`,
              animationDuration: `${particle.duration}s`,
              boxShadow: "0 0 6px rgba(255,255,255,0.5)",
            }}
          />
        ))}
      </div>

      <div ref={copyRef} className="relative mx-auto w-full max-w-5xl text-center will-change-transform">
        {/* The hero uses CSS entrances rather than the scroll observer: this copy
            is above the fold on every screen, and waiting for JavaScript to
            reveal it would delay the largest paint for no benefit. */}
        <div className="animate-rise">
          <p className="mx-auto inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.04] px-3.5 py-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse-soft" aria-hidden="true" />
            Enterprise procurement intelligence
          </p>
        </div>

        <div className="animate-rise" style={{ animationDelay: "90ms" }}>
          <h1 className="mx-auto mt-7 max-w-[1120px] text-display text-balance">
            Procurement Intelligence.
            <span className="mt-1 block text-white/55">Powered by Evidence.</span>
          </h1>
        </div>

        <div className="animate-rise" style={{ animationDelay: "180ms" }}>
          <p className="mx-auto mt-7 max-w-2xl text-[15px] leading-relaxed text-muted-foreground sm:text-base">
            Search supplier agreements, pricing schedules, amendments and compliance documents — then open the exact
            page every answer was built from. What was retrieved, what was verified and what could not be found is
            shown, not implied.
          </p>
        </div>

        <div className="animate-rise" style={{ animationDelay: "260ms" }}>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button size="lg" variant="glow" asChild className="w-full sm:w-auto">
              <Link to="/login">
                Explore Intelligence
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild className="w-full sm:w-auto">
              <a href="#platform">View Platform</a>
            </Button>
          </div>
        </div>

        <div className="animate-rise" style={{ animationDelay: "340ms" }}>
          <p className="mt-6 text-[11px] leading-relaxed text-subtle">
            Sign-in is required: every lookup is scoped to a tenant and to the document access level of the account.
          </p>
        </div>
      </div>

      <a
        href="#platform"
        className="absolute bottom-7 left-1/2 -translate-x-1/2 rounded-full p-2 text-subtle transition-colors hover:text-foreground focus-visible:text-foreground"
        aria-label="Scroll to the platform overview"
      >
        <ChevronDown className="h-5 w-5 animate-float-slow motion-reduce:animate-none" aria-hidden="true" />
      </a>
      </section>
    </div>
  );
}

/* -------------------------------------------------------------- platform */

function Platform() {
  return (
    <section id="platform" className="relative scroll-mt-24 border-t border-white/[0.07] bg-ink px-5 py-24 lg:px-8 lg:py-32">
      <div className="mx-auto w-full max-w-7xl">
        <Reveal className="max-w-3xl">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-subtle">The platform</p>
          <h2 className="mt-4 text-display-sm text-balance">One Intelligence Layer for Procurement.</h2>
          <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-muted-foreground">
            Records, documents and the relationships between them are held in one system, so a question resolves to an
            answer and to the evidence that supports it — rather than to a second tool.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-5 lg:grid-cols-3">
          {PILLARS.map((pillar, index) => (
            <Reveal key={pillar.title} delay={index * 90}>
              <article className="glass sheen card-interactive group flex h-full flex-col rounded-2xl p-7">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/12 bg-white/[0.05] text-white transition-transform duration-300 group-hover:-translate-y-0.5">
                  <pillar.icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="mt-6 text-lg font-medium tracking-tight">{pillar.title}</h3>
                <p className="mt-2.5 text-[13px] leading-relaxed text-muted-foreground">{pillar.body}</p>
                <ul className="mt-6 space-y-2.5 border-t border-white/[0.08] pt-5 text-[12.5px] text-muted-foreground">
                  {pillar.points.map((point) => (
                    <li key={point} className="flex items-center gap-2.5">
                      <span className="h-px w-3 bg-white/40" aria-hidden="true" />
                      {point}
                    </li>
                  ))}
                </ul>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------- workflow */

/* ---------------------------------------------------------- capabilities */

function Capabilities() {
  return (
    <section id="features" className="scroll-mt-24 border-t border-white/[0.07] bg-ink px-5 py-24 lg:px-8 lg:py-32">
      <div className="mx-auto w-full max-w-7xl">
        <Reveal className="flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-2xl">
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-subtle">Platform capabilities</p>
            <h2 className="mt-4 text-display-sm text-balance">Built for the evidence, not the demo.</h2>
          </div>
          <p className="max-w-sm text-[13px] leading-relaxed text-muted-foreground">
            Each panel below is a layout preview of a surface in the working application, not a sample result. Figures
            are never invented to fill a card.
          </p>
        </Reveal>

        <ul className="mt-14 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((capability, index) => (
            <Reveal as="li" key={capability.title} delay={(index % 3) * 80}>
              <article className="glass card-interactive group flex h-full flex-col overflow-hidden rounded-2xl">
                <div className="relative h-[152px] overflow-hidden border-b border-white/[0.08] bg-ink-2/80">
                  <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(255,255,255,0.08),transparent_65%)]" />
                  <div aria-hidden="true" className="absolute inset-x-4 top-5 origin-top scale-[0.98]">
                    {capability.preview}
                  </div>
                </div>
                <div className="flex flex-1 flex-col p-6">
                  <div className="flex items-center gap-2.5">
                    <capability.icon className="h-4 w-4 text-white/70" aria-hidden="true" />
                    <h3 className="text-[15px] font-medium tracking-tight">{capability.title}</h3>
                  </div>
                  <p className="mt-2 text-[12.5px] leading-relaxed text-muted-foreground">{capability.body}</p>
                </div>
              </article>
            </Reveal>
          ))}

        </ul>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- trust */

function Trust() {
  return (
    <section className="border-t border-white/[0.07] bg-ink-2 px-5 py-24 lg:px-8 lg:py-28">
      <div className="mx-auto w-full max-w-7xl">
        <Reveal className="max-w-3xl">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-subtle">How to read what you see</p>
          <h2 className="mt-4 text-display-sm text-balance">A value is never invented to fill a space.</h2>
        </Reveal>

        <div className="mt-12 grid gap-8 lg:grid-cols-3">
          {TRUST.map((item, index) => (
            <Reveal key={item.title} delay={index * 80}>
              <div className="flex gap-4 border-t border-white/10 pt-6">
                <item.icon className="mt-0.5 h-4 w-4 shrink-0 text-white/60" aria-hidden="true" />
                <div>
                  <h3 className="text-[15px] font-medium">{item.title}</h3>
                  <p className="mt-2 text-[12.5px] leading-relaxed text-muted-foreground">{item.body}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>

        <Reveal delay={120}>
          <p className="mt-12 max-w-3xl rounded-xl border border-white/10 bg-white/[0.03] p-5 text-[12px] leading-relaxed text-muted-foreground">
            The corpus shipped with this build is 20 public procurement notices imported from the UK Find a Tender
            Service (OCDS) under the Open Government Licence, with each document&apos;s source URL and licence recorded.
            Files uploaded and marked as demo content are labelled in the interface, so they are never mistaken for
            imported records. Quality claims are reported only as evaluation runs over a hand-labelled question set.
          </p>
        </Reveal>
      </div>
    </section>
  );
}

/* --------------------------------------------------------------- closing */

function ClosingCta() {
  return (
    <section className="relative overflow-hidden border-t border-white/[0.07] bg-ink px-5 py-28 lg:px-8 lg:py-36">
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[560px] w-[900px] -translate-x-1/2 -translate-y-1/2 halo"
        aria-hidden="true"
      />
      <div className="relative mx-auto max-w-3xl text-center">
        <Reveal>
          <ShieldQuestion className="mx-auto h-6 w-6 text-white/50" aria-hidden="true" />
          <h2 className="mt-6 text-display-sm text-balance">Start with the evidence.</h2>
          <p className="mx-auto mt-4 max-w-xl text-[14px] leading-relaxed text-muted-foreground">
            Ask a question, open the page it came from, and decide for yourself. If the records do not support the
            answer, the platform will say so.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button size="lg" variant="glow" asChild className="w-full sm:w-auto">
              <Link to="/login">
                Open workspace
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
            <Button size="lg" variant="ghost" asChild className="w-full sm:w-auto">
              <Link to="/security">Read the security model</Link>
            </Button>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* --------------------------------------------------------------- previews
 *
 * These are interface layouts, drawn from the same tokens as the product. They
 * contain structure — rows, labels, emphasis — and no procurement figures, so a
 * preview can never be read as a sample of someone's data.
 */

function PreviewFrame({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <div className="rounded-t-lg border border-white/10 bg-ink-3/95 shadow-[0_-1px_0_0_rgba(255,255,255,0.06)_inset]">
      <div className="flex items-center gap-1.5 border-b border-white/[0.07] px-3 py-2">
        <span className="h-1.5 w-1.5 rounded-full bg-white/20" />
        <span className="h-1.5 w-1.5 rounded-full bg-white/15" />
        <span className="h-1.5 w-1.5 rounded-full bg-white/10" />
        <span className="ml-2 text-[9px] uppercase tracking-[0.14em] text-subtle">{label}</span>
      </div>
      <div className="p-3">{children}</div>
    </div>
  );
}

function Bar({ width, className = "" }: { width: string; className?: string }) {
  return <span className={`block h-1.5 rounded-full bg-white/12 ${className}`} style={{ width }} />;
}

function SearchPreview() {
  return (
    <PreviewFrame label="Search">
      <div className="flex items-center gap-2 rounded-md border border-white/12 bg-white/[0.04] px-2.5 py-1.5">
        <FileSearch className="h-3 w-3 text-white/45" aria-hidden="true" />
        <Bar width="52%" />
      </div>
      <div className="mt-2 space-y-1.5">
        {["68%", "84%", "57%"].map((width, index) => (
          <div key={width} className="rounded-md border border-white/[0.07] bg-white/[0.02] px-2.5 py-1.5">
            <div className="flex items-center gap-2">
              <span className="rounded-sm border border-white/15 px-1 text-[7px] uppercase tracking-wider text-subtle">
                page
              </span>
              <Bar width={width} />
            </div>
            {index === 0 ? <Bar width="40%" className="mt-1.5 h-1 bg-white/[0.07]" /> : null}
          </div>
        ))}
      </div>
    </PreviewFrame>
  );
}

function DocumentPreview() {
  return (
    <PreviewFrame label="Document">
      <div className="flex gap-3">
        <div className="w-12 shrink-0 rounded-sm border border-white/12 bg-white/[0.03] p-1.5">
          <Bar width="100%" className="h-1" />
          <Bar width="80%" className="mt-1 h-1" />
          <Bar width="90%" className="mt-1 h-1" />
          <Bar width="60%" className="mt-1 h-1" />
        </div>
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex items-center gap-1.5">
            <ScanText className="h-3 w-3 text-white/45" aria-hidden="true" />
            <Bar width="45%" />
          </div>
          <div className="rounded-sm border-l-2 border-l-white/60 bg-white/[0.06] py-1 pl-2">
            <Bar width="88%" className="h-1" />
            <Bar width="72%" className="mt-1 h-1" />
          </div>
          <div className="flex gap-1.5 pt-1">
            <span className="rounded-full border border-white/12 px-1.5 py-0.5 text-[7px] uppercase tracking-wider text-subtle">
              extracted
            </span>
            <span className="rounded-full border border-white/12 px-1.5 py-0.5 text-[7px] uppercase tracking-wider text-subtle">
              cited
            </span>
          </div>
        </div>
      </div>
    </PreviewFrame>
  );
}

function SupplierPreview() {
  return (
    <PreviewFrame label="Supplier">
      <div className="flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-full border border-white/15 bg-white/[0.06]">
          <Users className="h-3 w-3 text-white/55" aria-hidden="true" />
        </span>
        <Bar width="42%" />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        {["w-full", "w-4/5", "w-2/3"].map((width) => (
          <div key={width} className="rounded-md border border-white/[0.07] bg-white/[0.02] p-2">
            <Bar width={width} className="h-1" />
            <Bar width="55%" className="mt-1.5 h-2.5 bg-white/20" />
          </div>
        ))}
      </div>
      <div className="mt-2 space-y-1">
        <Bar width="76%" className="h-1" />
        <Bar width="64%" className="h-1" />
      </div>
    </PreviewFrame>
  );
}

function EvidencePreview() {
  return (
    <PreviewFrame label="Evidence">
      <div className="space-y-1.5">
        {[0, 1].map((row) => (
          <div key={row} className="rounded-md border border-white/[0.07] bg-white/[0.02] p-2">
            <div className="flex items-center gap-1.5">
              <BadgeCheck className="h-3 w-3 text-white/50" aria-hidden="true" />
              <Bar width="48%" className="h-1" />
              <span className="ml-auto rounded-sm border border-white/15 px-1 text-[7px] uppercase tracking-wider text-subtle">
                cited
              </span>
            </div>
            <Bar width="86%" className="mt-1.5 h-1 bg-white/[0.07]" />
          </div>
        ))}
      </div>
      <div className="mt-2 flex items-center gap-1.5">
        <span className="h-1 w-1 rounded-full bg-white/50" />
        <Bar width="40%" className="h-1" />
      </div>
    </PreviewFrame>
  );
}
