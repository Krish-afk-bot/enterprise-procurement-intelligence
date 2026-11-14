import { useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { gsap } from "gsap";
import { MotionPathPlugin } from "gsap/MotionPathPlugin";
import { LANDING_CONTENT } from "@/content/landing";
import { useMotionMode } from "@/motion/motion";
import {
  FileText,
  Search,
  Network,
  Building2,
  TrendingUp,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Cpu,
} from "lucide-react";

gsap.registerPlugin(MotionPathPlugin);

const ICON_MAP: Record<string, React.ReactNode> = {
  FileText: <FileText className="w-4 h-4 text-[#FF4D00]" />,
  Search: <Search className="w-4 h-4 text-[#FF4D00]" />,
  Network: <Network className="w-4 h-4 text-[#FF4D00]" />,
  Building2: <Building2 className="w-4 h-4 text-[#FF4D00]" />,
  TrendingUp: <TrendingUp className="w-4 h-4 text-[#FF4D00]" />,
  ShieldCheck: <ShieldCheck className="w-4 h-4 text-[#FF4D00]" />,
};

// Precise symmetrical card top target coordinates in 1000px coordinate system:
// 6 columns across 1000px: center of each column
const CARD_CENTERS = [78, 247, 416, 584, 753, 922];

export function HeroSection() {
  const containerRef = useRef<HTMLElement>(null);
  const motionMode = useMotionMode();
  const [flashedCardIdx, setFlashedCardIdx] = useState<number | null>(null);

  useLayoutEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    const full = motionMode === "full";

    // Immediately mark ready — elements are visible by default via CSS
    // Animation only adds y-slide, never hides anything (use .from not .fromTo)
    root.setAttribute("data-ready", "true");

    if (motionMode === "off") {
      return;
    }

    // Safety net: clear any stuck GSAP transform props after 2s (NOT all — preserve inline styles like font-size)
    const timer = setTimeout(() => {
      gsap.set(
        ".hero-eyebrow, .hero-cta, .hero-card, .hero-sub, .hero-chip-container, .hero-trace",
        { clearProps: "transform,opacity,visibility" }
      );
    }, 2000);

    const ctx = gsap.context(() => {
      // .from() animates FROM a state TO the natural CSS state
      // Elements are never invisible — GSAP only adds the slide-up motion
      if (full) {
        const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
        tl.from(".hero-eyebrow", { y: 10, duration: 0.5 }, 0)
          .from(".hero-headline-span", { y: 14, stagger: 0.1, duration: 0.6 }, 0.15)
          .from(".hero-sub", { y: 12, duration: 0.6 }, 0.35)
          .from(".hero-cta", { y: 12, stagger: 0.08, duration: 0.5 }, 0.5)
          .from(".hero-chip-container", { scale: 0.94, duration: 0.6 }, 0.65)
          .from(".hero-card", { y: 16, stagger: 0.06, duration: 0.5 }, 0.9);
      }

      // Ambient breathing animations in full motion mode
      if (full) {
        gsap.to(".hero-beam", {
          x: 20,
          rotate: 1.5,
          opacity: 0.85,
          duration: 6.5,
          ease: "sine.inOut",
          yoyo: true,
          repeat: -1,
        });

        gsap.to(".hero-chip-badge", {
          y: -3,
          duration: 2.8,
          ease: "sine.inOut",
          yoyo: true,
          repeat: -1,
        });

        // 6 Travelling Pulses with Glow Trails (3 left, 3 right, fanning out)
        // Staggered durations (2.4s to 3.8s) looping continuously
        const durations = [3.4, 2.8, 2.5, 2.6, 2.9, 3.5];
        const delays = [0.1, 0.4, 0.2, 0.5, 0.3, 0.6];

        for (let i = 0; i < 6; i++) {
          const pathId = `#hero-trace-${i}`;
          const lead = root.querySelector(`.hero-pulse-lead-${i}`);
          const trail = root.querySelector(`.hero-pulse-trail-${i}`);
          const path = root.querySelector<SVGPathElement>(pathId);

          if (lead && path) {
            // Lead pulse
            gsap.to(lead, {
              motionPath: {
                path: path,
                align: path,
                alignOrigin: [0.5, 0.5],
              },
              duration: durations[i],
              ease: "none",
              repeat: -1,
              repeatDelay: 0.5,
              delay: 1.0 + delays[i],
              onRepeat: () => {
                // Flash the card top border when pulse reaches terminal
                setFlashedCardIdx(i);
                setTimeout(() => {
                  setFlashedCardIdx((curr) => (curr === i ? null : curr));
                }, 400);
              },
            });

            // Opacity fade at start and finish
            gsap.to(lead, {
              keyframes: { opacity: [0, 1, 1, 0] },
              duration: durations[i],
              repeat: -1,
              repeatDelay: 0.5,
              delay: 1.0 + delays[i],
              ease: "none",
            });
          }

          if (trail && path) {
            // Trail pulse following ~60ms behind
            gsap.to(trail, {
              motionPath: {
                path: path,
                align: path,
                alignOrigin: [0.5, 0.5],
              },
              duration: durations[i],
              ease: "none",
              repeat: -1,
              repeatDelay: 0.5,
              delay: 1.06 + delays[i],
            });

            gsap.to(trail, {
              keyframes: { opacity: [0, 0.5, 0.5, 0] },
              duration: durations[i],
              repeat: -1,
              repeatDelay: 0.5,
              delay: 1.06 + delays[i],
              ease: "none",
            });
          }
        }
      }
    }, root);

    return () => {
      clearTimeout(timer);
      ctx.revert();
    };
  }, [motionMode]);

  return (
    <section
      ref={containerRef}
      id="hero"
      data-ready="true"
      className="relative flex flex-col items-center justify-start pt-36 sm:pt-40 lg:pt-44 pb-20 px-6 overflow-hidden bg-[#050505] text-white scroll-mt-[112px]"
    >
      {/* Background ambient light */}
      <div className="hero-beam pointer-events-none absolute -top-40 -right-40 w-[600px] h-[600px] bg-gradient-to-br from-[#FF4D00]/20 via-[#FF7A1A]/8 to-transparent rounded-full blur-[140px] transform -rotate-12 opacity-80" />

      {/* Main hero content stacked with tight, calibrated vertical rhythm */}
      <div className="relative z-10 max-w-5xl mx-auto text-center flex flex-col items-center w-full">
        {/* 1. Eyebrow badge (24px mb = exactly 24px gap above headline) */}
        <div
          className="hero-eyebrow inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider uppercase bg-white/5 border border-white/10 text-white/80 backdrop-blur-md mb-6 shadow-sm"
          style={{ opacity: 1, visibility: "visible", display: "inline-flex" }}
        >
          <Sparkles className="w-3.5 h-3.5 text-[#FF4D00]" />
          <span>{LANDING_CONTENT.hero.eyebrow}</span>
        </div>

        {/* 2. Headline: Two lines on desktop, clamp font-size, no descender clipping (24px mb) */}
        <h1
          className="hero-headline font-bold tracking-[-0.03em] text-white leading-[1.08] text-center mb-6 max-w-5xl"
          style={{ fontSize: "clamp(2.5rem, 6vw, 5.5rem)", textWrap: "nowrap" as React.CSSProperties["textWrap"] }}
        >
          <span className="hero-headline-span block md:whitespace-nowrap pb-1.5">
            Procurement Intelligence.
          </span>
          <span className="hero-headline-span block md:whitespace-nowrap pb-2">
            Powered by Evidence.
          </span>
        </h1>

        {/* 3. Subtitle (32px mb) */}
        <p className="hero-sub text-base sm:text-lg text-white/65 max-w-2xl font-normal leading-relaxed mb-8">
          {LANDING_CONTENT.hero.subtitle}
        </p>

        {/* 4. Action CTAs (36px mb) */}
        <div className="flex flex-wrap items-center justify-center gap-4 mb-9">
          <a
            href={LANDING_CONTENT.hero.primaryCta.href}
            className="hero-cta hero-cta-primary inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-semibold tracking-wide bg-[#FF4D00] text-white hover:bg-[#FF7A1A] transition-all duration-200 shadow-[0_0_25px_rgba(255,77,0,0.35)] hover:scale-[1.02]"
          >
            <span>{LANDING_CONTENT.hero.primaryCta.text}</span>
            <ArrowRight className="w-4 h-4" />
          </a>

          <Link
            to={LANDING_CONTENT.hero.secondaryCta.href}
            className="hero-cta inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-semibold tracking-wide bg-white/5 text-white/90 border border-white/10 hover:bg-white/10 hover:text-white transition-all duration-200 backdrop-blur-sm"
          >
            <span>{LANDING_CONTENT.hero.secondaryCta.text}</span>
          </Link>
        </div>

        {/* 5. Central Intelligence Engine Chip */}
        <div className="hero-chip-container relative z-20 flex flex-col items-center">
          <div className="hero-chip-badge relative flex items-center gap-3 px-5 py-2.5 rounded-2xl bg-[#0B0B0C] border border-[#FF4D00]/50 shadow-[0_0_35px_rgba(255,77,0,0.25)]">
            <span className="w-8 h-8 rounded-xl bg-[#FF4D00] flex items-center justify-center text-white shrink-0">
              <Cpu className="w-4 h-4" />
            </span>
            <div className="text-left">
              <span className="text-xs font-bold text-white block">EPI REASONING ENGINE</span>
              <span className="text-[10px] text-white/50 block">Hybrid RAG • Entity Graph • Verification</span>
            </div>
          </div>
        </div>

        {/* 6. Traces Bridge (SVG connecting chip bottom to each of the 6 cards' top edge) */}
        <div className="relative w-full max-w-5xl h-14 -mt-1 pointer-events-none">
          <svg
            viewBox="0 0 1000 56"
            fill="none"
            className="w-full h-full"
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="trace-grad-left" x1="100%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#FF4D00" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#FF7A1A" stopOpacity="0.3" />
              </linearGradient>
              <linearGradient id="trace-grad-right" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FF4D00" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#FF7A1A" stopOpacity="0.3" />
              </linearGradient>
              <filter id="pulse-glow" x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="0" stdDeviation="2.5" floodColor="#FF4D00" floodOpacity="0.9" />
              </filter>
            </defs>

            {/* Symmetrical Traces connecting chip center (500, 0) to 6 card anchors (CARD_CENTERS, 56) */}
            <path
              id="hero-trace-0"
              className="hero-trace"
              d={`M 500 0 C 460 18, 160 22, ${CARD_CENTERS[0]} 56`}
              stroke="url(#trace-grad-left)"
              strokeWidth="1.5"
            />
            <path
              id="hero-trace-1"
              className="hero-trace"
              d={`M 500 0 C 470 18, 300 22, ${CARD_CENTERS[1]} 56`}
              stroke="url(#trace-grad-left)"
              strokeWidth="1.5"
            />
            <path
              id="hero-trace-2"
              className="hero-trace"
              d={`M 500 0 C 480 18, 430 22, ${CARD_CENTERS[2]} 56`}
              stroke="url(#trace-grad-left)"
              strokeWidth="1.5"
            />
            <path
              id="hero-trace-3"
              className="hero-trace"
              d={`M 500 0 C 520 18, 570 22, ${CARD_CENTERS[3]} 56`}
              stroke="url(#trace-grad-right)"
              strokeWidth="1.5"
            />
            <path
              id="hero-trace-4"
              className="hero-trace"
              d={`M 500 0 C 530 18, 700 22, ${CARD_CENTERS[4]} 56`}
              stroke="url(#trace-grad-right)"
              strokeWidth="1.5"
            />
            <path
              id="hero-trace-5"
              className="hero-trace"
              d={`M 500 0 C 540 18, 840 22, ${CARD_CENTERS[5]} 56`}
              stroke="url(#trace-grad-right)"
              strokeWidth="1.5"
            />

            {/* Terminal anchor dots at each card connection */}
            {CARD_CENTERS.map((cx, idx) => (
              <circle
                key={idx}
                cx={cx}
                cy={54}
                r={flashedCardIdx === idx ? 3.5 : 2.5}
                fill={flashedCardIdx === idx ? "#FFFFFF" : "#FF4D00"}
                className="transition-all duration-300"
              />
            ))}

            {/* 6 Pairs of Travelling Pulses (Lead + 60ms Glow Trail) */}
            {[0, 1, 2, 3, 4, 5].map((idx) => (
              <g key={idx}>
                {/* Trail pulse */}
                <circle
                  className={`hero-pulse-trail-${idx}`}
                  r="2.2"
                  fill="#FF7A1A"
                  opacity="0"
                />
                {/* Lead pulse */}
                <circle
                  className={`hero-pulse-lead-${idx}`}
                  r="3.5"
                  fill="#FF4D00"
                  filter="url(#pulse-glow)"
                  opacity="0"
                />
              </g>
            ))}
          </svg>
        </div>

        {/* 7. Connected 6 Capability Cards directly below the traces */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5 w-full max-w-5xl">
          {LANDING_CONTENT.hero.chips.map((chip, idx) => {
            const isFlashed = flashedCardIdx === idx;
            return (
              <div
                key={chip.id}
                className={`hero-card group relative flex flex-col items-center text-center p-3.5 rounded-2xl bg-[#0B0B0C] border transition-all duration-300 backdrop-blur-md shadow-md hover:-translate-y-1 ${isFlashed
                  ? "border-t-[#FF4D00] border-white/20 shadow-[0_-4px_18px_rgba(255,77,0,0.5)]"
                  : "border-white/[0.08] hover:border-[#FF4D00]/60"
                  }`}
              >
                <div className="w-8 h-8 rounded-xl bg-white/5 flex items-center justify-center mb-2 group-hover:scale-110 transition-transform">
                  {ICON_MAP[chip.icon] ?? <FileText className="w-4 h-4 text-[#FF4D00]" />}
                </div>
                <span className="text-xs font-semibold text-white/90 mb-0.5">{chip.label}</span>
                <span className="text-[10px] text-white/50 leading-tight">{chip.description}</span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
