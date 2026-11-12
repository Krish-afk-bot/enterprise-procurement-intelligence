import { useRef, useState, useEffect } from "react";
import { WordReveal } from "@/components/animations/WordReveal";
import { Marquee, MarqueeChip } from "@/components/animations/Marquee";
import { CurtainTransition } from "@/components/animations/CurtainTransition";
import { useScrollReveal } from "@/components/animations/useScrollReveal";

// Capability chips for marquee rows
const CAPABILITY_CHIPS = [
  "Document Intelligence",
  "Hybrid Retrieval",
  "Knowledge Graph",
  "Supplier Intelligence",
  "Evidence Verification",
  "Contract Analysis",
  "Multi-Agent Planning",
  "Citation Tracing",
  "Temporal Filtering",
  "Cross-Encoder Reranking",
  "RRF Fusion",
  "Claim Binding",
];

// Cycling captions for the media card
const MEDIA_CAPTIONS = [
  "Understand procurement data.",
  "Connect supplier intelligence.",
  "Trace every answer.",
];

/**
 * Explainer Section (Scene 02).
 *
 * Features:
 * - Light curtain transition from dark hero
 * - Word-reveal heading
 * - Animated media card with cycling captions
 * - Three marquee rows of capability chips (alternating directions)
 * - Off-white background with subtle peach glow
 */
export function ExplainerSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const mediaRef = useScrollReveal<HTMLDivElement>({ y: 40, duration: 0.9 });
  const [currentCaption, setCurrentCaption] = useState(0);

  // Cycle captions every 3 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentCaption((prev) => (prev + 1) % MEDIA_CAPTIONS.length);
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <section
      id="platform"
      ref={sectionRef}
      className="relative scroll-mt-24 overflow-hidden bg-[#FAFAF9] px-5 py-24 lg:px-8 lg:py-32"
    >
      {/* Curtain transition */}
      <CurtainTransition theme="light" triggerRef={sectionRef} />

      {/* Subtle peach glow at top */}
      <div
        className="pointer-events-none absolute left-1/2 top-0 h-[400px] w-[800px] -translate-x-1/2"
        style={{
          background: "radial-gradient(ellipse at top, rgba(251, 146, 60, 0.08), transparent 70%)",
        }}
        aria-hidden="true"
      />

      <div className="relative mx-auto w-full max-w-7xl">
        {/* Heading */}
        <div className="max-w-3xl">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">The platform</p>
          <WordReveal mode="scroll" triggerRef={sectionRef} className="mt-4 text-display-sm text-balance text-zinc-900">
            One Intelligence Layer for Procurement.
          </WordReveal>
          <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-zinc-600">
            Records, documents and the relationships between them are held in one system, so a question resolves to an
            answer and to the evidence that supports it.
          </p>
        </div>

        {/* Main content: Media card + Capability chips */}
        <div className="mt-14 grid gap-8 lg:grid-cols-2 lg:gap-12">
          {/* Left: Animated media card */}
          <div ref={mediaRef}>
            <MediaCard caption={MEDIA_CAPTIONS[currentCaption]} />
          </div>

          {/* Right: Marquee rows */}
          <div className="flex flex-col justify-center gap-4">
            <div className="space-y-3">
              <p className="text-[13px] font-medium text-zinc-900">Core Capabilities</p>

              {/* Row 1: Left */}
              <Marquee direction="left" speed={25}>
                {CAPABILITY_CHIPS.slice(0, 4).map((chip) => (
                  <MarqueeChip key={chip} className="border-zinc-200 bg-white/80 text-zinc-700">
                    {chip}
                  </MarqueeChip>
                ))}
              </Marquee>

              {/* Row 2: Right */}
              <Marquee direction="right" speed={30}>
                {CAPABILITY_CHIPS.slice(4, 8).map((chip) => (
                  <MarqueeChip key={chip} className="border-zinc-200 bg-white/80 text-zinc-700">
                    {chip}
                  </MarqueeChip>
                ))}
              </Marquee>

              {/* Row 3: Left */}
              <Marquee direction="left" speed={28}>
                {CAPABILITY_CHIPS.slice(8).map((chip) => (
                  <MarqueeChip key={chip} className="border-zinc-200 bg-white/80 text-zinc-700">
                    {chip}
                  </MarqueeChip>
                ))}
              </Marquee>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * Animated media card with cycling caption.
 */
function MediaCard({ caption }: { caption: string }) {
  return (
    <div className="group relative aspect-[4/3] overflow-hidden rounded-3xl border border-zinc-200 bg-gradient-to-br from-zinc-50 to-zinc-100 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.15)]">
      {/* Animated light streaks */}
      <div className="absolute inset-0 overflow-hidden">
        <div
          className="absolute -left-1/4 top-0 h-full w-1/2 opacity-40 mix-blend-overlay animate-drift"
          style={{
            background: "linear-gradient(90deg, transparent, rgba(251, 146, 60, 0.4), transparent)",
            filter: "blur(40px)",
          }}
        />
      </div>

      {/* Floating procurement icons */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative h-48 w-48">
          <ProcurementIcon icon="📄" position={{ x: "10%", y: "20%" }} delay={0} />
          <ProcurementIcon icon="🏢" position={{ x: "70%", y: "15%" }} delay={0.2} />
          <ProcurementIcon icon="💰" position={{ x: "20%", y: "70%" }} delay={0.4} />
          <ProcurementIcon icon="✓" position={{ x: "75%", y: "75%" }} delay={0.6} />
        </div>
      </div>

      {/* Caption */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-6">
        <p
          key={caption}
          className="text-[15px] font-medium text-white transition-opacity duration-500 animate-fade-in"
        >
          {caption}
        </p>
      </div>
    </div>
  );
}

/**
 * Floating procurement icon.
 */
function ProcurementIcon({
  icon,
  position,
  delay,
}: {
  icon: string;
  position: { x: string; y: string };
  delay: number;
}) {
  return (
    <div
      className="absolute flex h-12 w-12 items-center justify-center rounded-xl border border-zinc-300 bg-white/80 text-2xl shadow-lg backdrop-blur-sm animate-float-slow"
      style={{
        left: position.x,
        top: position.y,
        animationDelay: `${delay}s`,
      }}
    >
      {icon}
    </div>
  );
}
