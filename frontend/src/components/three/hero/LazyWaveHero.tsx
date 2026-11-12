import { Suspense, lazy, useEffect, useRef, useState } from "react";

import { hasWebGL, useReducedDetail, useSmallScreen } from "@/lib/useMediaQuery";
import { useReducedMotion } from "@/lib/useReducedMotion";
import { cn } from "@/lib/utils";

const WaveScene = lazy(() => import("@/components/three/hero/WaveScene"));

/**
 * The hero's cinematic layer, loaded on the client only.
 *
 * The three.js bundle is imported after first paint and only when the browser
 * can actually draw it, the screen is large enough for it to earn its cost, and
 * the reader has not asked for reduced motion. Everything before that point is
 * the CSS field below, which is also what a visitor sees if WebGL is missing or
 * the chunk fails to load — so the hero never depends on the 3D layer.
 *
 * Rendering pauses when the hero scrolls out of view, so a long page costs
 * nothing once the reader has moved on.
 */
export function LazyWaveHero({ className }: { className?: string }) {
  const reducedMotion = useReducedMotion();
  const smallScreen = useSmallScreen();
  const reducedDetail = useReducedDetail();
  const container = useRef<HTMLDivElement>(null);

  const [webgl, setWebgl] = useState<boolean | null>(null);
  const [mounted, setMounted] = useState(false);
  const [inView, setInView] = useState(true);

  // WebGL support is checked after mount so the first paint is never blocked.
  useEffect(() => {
    setWebgl(hasWebGL());
  }, []);

  // The chunk is fetched only once the hero is visible.
  useEffect(() => {
    const node = container.current;
    if (!node || webgl !== true) return;
    if (typeof IntersectionObserver === "undefined") {
      setMounted(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setMounted(true);
            observer.disconnect();
          }
        }
      },
      { rootMargin: "200px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [webgl]);

  // Pause the animation loop when the hero is off screen.
  useEffect(() => {
    const node = container.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) setInView(entry.isIntersecting);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const drawCanvas = webgl === true && !smallScreen;

  return (
    <div ref={container} className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)} aria-hidden="true">
      {/* The static field is both the pre-load state and the permanent fallback. */}
      <StaticWaveField active={!drawCanvas} />
      {drawCanvas && mounted ? (
        <Suspense fallback={null}>
          <div className="absolute inset-0 opacity-0 animate-fade-in [animation-delay:400ms] [animation-fill-mode:forwards] motion-reduce:opacity-100">
            <WaveScene animate={!reducedMotion && inView} detail={!reducedDetail} />
          </div>
        </Suspense>
      ) : null}
    </div>
  );
}

/**
 * A pure-CSS interpretation of the scene: layered contour lines with a soft
 * horizon glow. It is intentionally not a blurred photograph — it reads as a
 * drawn surface, so it is clear that no measurement is being shown.
 */
export function StaticWaveField({ active = true }: { active?: boolean }) {
  return (
    <div
      className={cn(
        "absolute inset-0 transition-opacity duration-1000",
        active ? "opacity-100" : "opacity-0",
      )}
      data-testid="hero-static-field"
    >
      {/* Horizon glow */}
      <div className="absolute left-1/2 top-[42%] h-[520px] w-[900px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(closest-side,rgba(255,255,255,0.10),transparent_70%)] blur-2xl" />

      {/* Contour landscape, drawn as stacked curves. */}
      <svg
        className="absolute inset-x-0 bottom-0 h-[62%] w-full"
        viewBox="0 0 1200 480"
        preserveAspectRatio="none"
        fill="none"
      >
        <defs>
          <linearGradient id="wave-fade" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="white" stopOpacity="0.30" />
            <stop offset="55%" stopColor="white" stopOpacity="0.10" />
            <stop offset="100%" stopColor="white" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="wave-fade-2" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="white" stopOpacity="0.16" />
            <stop offset="100%" stopColor="white" stopOpacity="0" />
          </linearGradient>
        </defs>
        {Array.from({ length: 16 }).map((_, index) => {
          const offset = index * 26;
          const lift = index * 4;
          return (
            <path
              key={index}
              d={`M -80 ${300 + offset - lift} C 180 ${210 + offset - lift}, 320 ${330 + offset - lift}, 520 ${250 + offset - lift} S 900 ${150 + offset - lift}, 1280 ${250 + offset - lift}`}
              stroke={index % 4 === 0 ? "url(#wave-fade)" : "url(#wave-fade-2)"}
              strokeWidth={index % 4 === 0 ? 1.1 : 0.7}
              opacity={1 - index * 0.045}
            />
          );
        })}
      </svg>

      {/* A fine vignette keeps the centre of the viewport dark enough for type. */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_35%,#050505_82%)]" />
    </div>
  );
}
