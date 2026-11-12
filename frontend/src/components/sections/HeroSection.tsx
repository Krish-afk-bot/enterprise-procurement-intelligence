import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ChevronDown } from "lucide-react";

import { WordReveal } from "@/components/animations/WordReveal";
import { CircuitAnimation, createChipPaths } from "@/components/animations/CircuitAnimation";
import { MagneticButton } from "@/components/motion/MagneticButton";
import { canPin, loadScroll } from "@/components/motion/scroll";
import { LazyWaveHero } from "@/components/three/hero/LazyWaveHero";
import { Button } from "@/components/ui/button";

// Six capability tiles surrounding the chip
const CAPABILITY_TILES = [
  { label: "Documents", icon: "📄", delay: 0.1 },
  { label: "Retrieval", icon: "🔍", delay: 0.2 },
  { label: "Graph", icon: "🕸️", delay: 0.3 },
  { label: "Suppliers", icon: "🏢", delay: 0.4 },
  { label: "Pricing", icon: "💰", delay: 0.5 },
  { label: "Verification", icon: "✓", delay: 0.6 },
];

/**
 * Enhanced Hero Section (Scene 01).
 *
 * Features:
 * - Word-by-word headline reveal
 * - Animated procurement chip with circuit traces
 * - Orange pulses traveling through circuits
 * - Floating capability tiles
 * - Diagonal orange light beam
 * - Ambient particle field
 * - Pinned scroll sequence (desktop)
 */
export function HeroSection() {
  const wrapRef = useRef<HTMLDivElement>(null);
  const sectionRef = useRef<HTMLElement>(null);
  const sceneRef = useRef<HTMLDivElement>(null);
  const copyRef = useRef<HTMLDivElement>(null);
  const chipRef = useRef<HTMLDivElement>(null);

  // Pinned scroll: hero stays in place while copy scales back
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
          .to(chipRef.current, { scale: 1.2, ease: "none" }, 0);
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
        {/* Background scene */}
        <div ref={sceneRef} className="absolute inset-[-16px] origin-center" aria-hidden="true">
          {/* 3D wave background */}
          <div className="absolute inset-0">
            <LazyWaveHero />
          </div>

          {/* Diagonal orange beam */}
          <div
            className="pointer-events-none absolute right-0 top-0 h-[120%] w-[60%] opacity-40 mix-blend-overlay"
            style={{
              background: "linear-gradient(135deg, transparent 30%, #FB923C 70%, transparent 90%)",
              filter: "blur(60px)",
              transform: "rotate(-15deg) translateY(-20%)",
            }}
          />

          {/* Subtle grid */}
          <div className="pointer-events-none absolute inset-0 grid-lines opacity-70" />

          {/* Central chip */}
          <div ref={chipRef} className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
            <HeroChip />
          </div>

          {/* Floating capability tiles */}
          <CapabilityTiles />
        </div>

        {/* Scrim above scene, below copy */}
        <div className="pointer-events-none absolute inset-0 hero-scrim" aria-hidden="true" />

        {/* Ambient halo */}
        <div
          className="pointer-events-none absolute left-1/2 top-1/2 h-[680px] w-[680px] -translate-x-1/2 -translate-y-1/2 halo animate-pulse-soft"
          aria-hidden="true"
        />

        {/* Hero copy */}
        <div ref={copyRef} className="relative mx-auto w-full max-w-5xl text-center will-change-transform">
          {/* Eyebrow */}
          <div className="animate-rise">
            <p className="mx-auto inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.04] px-3.5 py-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse-soft" aria-hidden="true" />
              Enterprise procurement intelligence
            </p>
          </div>

          {/* Headline with word reveal */}
          <div className="mt-7">
            <WordReveal mode="time" delay={300} stagger={0.08} as="h1" className="text-display text-balance">
              Procurement Intelligence. Powered by Evidence.
            </WordReveal>
          </div>

          {/* Subtitle */}
          <div className="animate-rise" style={{ animationDelay: "900ms" }}>
            <p className="mx-auto mt-7 max-w-2xl text-[15px] leading-relaxed text-muted-foreground sm:text-base">
              Connect procurement records, documents, pricing and supplier relationships. Find the evidence behind every
              decision.
            </p>
          </div>

          {/* CTAs */}
          <div className="animate-rise" style={{ animationDelay: "1100ms" }}>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <MagneticButton className="w-full sm:w-auto" strength={0.4} radius={100}>
                <Button size="lg" variant="glow" asChild className="w-full sm:w-auto">
                  <Link to="/login">
                    Explore Intelligence
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                </Button>
              </MagneticButton>
              <MagneticButton className="w-full sm:w-auto" strength={0.3} radius={90}>
                <Button size="lg" variant="outline" asChild className="w-full sm:w-auto">
                  <a href="#platform">View Platform</a>
                </Button>
              </MagneticButton>
            </div>
          </div>

          {/* Note */}
          <div className="animate-rise" style={{ animationDelay: "1300ms" }}>
            <p className="mt-6 text-[11px] leading-relaxed text-subtle">
              Sign-in is required: every lookup is scoped to a tenant and to the document access level of the account.
            </p>
          </div>
        </div>

        {/* Scroll indicator */}
        <a
          href="#platform"
          className="absolute bottom-7 left-1/2 -translate-x-1/2 rounded-full p-2 text-subtle transition-all duration-300 hover:text-foreground hover:scale-110 focus-visible:text-foreground focus-visible:scale-110"
          aria-label="Scroll to the platform overview"
        >
          <ChevronDown className="h-5 w-5 animate-float-slow motion-reduce:animate-none" aria-hidden="true" />
        </a>
      </section>
    </div>
  );
}

/**
 * Central animated chip with circuit traces.
 */
function HeroChip() {
  const circuitPaths = createChipPaths(400, 300, 60);

  return (
    <div className="relative h-[600px] w-[800px]">
      {/* Circuit paths */}
      <div className="absolute inset-0">
        <CircuitAnimation paths={circuitPaths} drawDuration={1.5} delay={1.5} showPulses pulseDuration={4} />
      </div>

      {/* Central chip */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <div className="flex h-20 w-20 items-center justify-center rounded-2xl border-2 border-orange-400/50 bg-gradient-to-br from-orange-500/20 to-orange-600/10 shadow-[0_0_40px_rgba(251,146,60,0.3)] backdrop-blur-sm animate-rise">
          <div className="text-3xl">🔷</div>
        </div>
      </div>
    </div>
  );
}

/**
 * Six floating capability tiles around the chip.
 */
function CapabilityTiles() {
  const positions = [
    { x: "20%", y: "30%", rotation: -3 },
    { x: "75%", y: "25%", rotation: 2 },
    { x: "15%", y: "65%", rotation: 4 },
    { x: "80%", y: "70%", rotation: -2 },
    { x: "35%", y: "15%", rotation: 3 },
    { x: "60%", y: "80%", rotation: -4 },
  ];

  return (
    <>
      {CAPABILITY_TILES.map((tile, index) => {
        const pos = positions[index];
        return (
          <div
            key={tile.label}
            className="absolute animate-rise"
            style={{
              left: pos.x,
              top: pos.y,
              animationDelay: `${1800 + tile.delay * 1000}ms`,
            }}
          >
            <div
              className="glass group flex items-center gap-2 rounded-lg px-3 py-2 transition-transform duration-300 hover:scale-105 hover:-translate-y-1"
              style={{ transform: `rotate(${pos.rotation}deg)` }}
            >
              <span className="text-lg" aria-hidden="true">
                {tile.icon}
              </span>
              <span className="text-[11px] font-medium text-muted-foreground group-hover:text-foreground">{tile.label}</span>
            </div>
          </div>
        );
      })}
    </>
  );
}
