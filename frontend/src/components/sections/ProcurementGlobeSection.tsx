import { Suspense, useRef, useState, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { ProcurementGlobe } from "@/components/three/ProcurementGlobe";
import { canPin } from "@/components/motion/scroll";

// Floating labels for the globe
const LABELS = [
  { text: "Procurement Records", position: { x: "25%", y: "35%" }, delay: 0 },
  { text: "Supplier Network", position: { x: "70%", y: "30%" }, delay: 0.2 },
  { text: "Contract Intelligence", position: { x: "50%", y: "70%" }, delay: 0.4 },
];

/**
 * Procurement Globe Section (Scene 04).
 *
 * Features:
 * - Signature 3D dot-matrix globe
 * - Scroll-linked scale and rotation
 * - Floating procurement labels
 * - Deep black background with particles
 * - Performance optimized with lazy loading
 * - Context loss handling
 * - Mobile fallback
 */
export function ProcurementGlobeSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [supportsWebGL, setSupportsWebGL] = useState(true);

  // Check WebGL support
  useEffect(() => {
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      if (!gl) {
        setSupportsWebGL(false);
      }
    } catch (e) {
      setSupportsWebGL(false);
    }
  }, []);

  // Scroll progress tracking
  useEffect(() => {
    if (!canPin()) return;

    const section = sectionRef.current;
    if (!section) return;

    const onScroll = () => {
      const rect = section.getBoundingClientRect();
      const windowHeight = window.innerHeight;

      // Calculate progress: 0 when section enters bottom, 1 when it reaches center
      const start = windowHeight;
      const end = windowHeight / 2;
      const current = rect.top;

      const progress = Math.max(0, Math.min(1, 1 - (current - end) / (start - end)));
      setScrollProgress(progress);
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!supportsWebGL) {
    return <GlobeFallback />;
  }

  return (
    <section
      id="globe"
      ref={sectionRef}
      className="relative min-h-[120vh] overflow-hidden bg-ink"
    >
      {/* Star particles */}
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        {Array.from({ length: 30 }).map((_, i) => (
          <div
            key={i}
            className="absolute h-px w-px rounded-full bg-white animate-float-slow"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              opacity: Math.random() * 0.5 + 0.2,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${10 + Math.random() * 8}s`,
            }}
          />
        ))}
      </div>

      {/* Ambient orange glow */}
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 opacity-30"
        style={{
          background: "radial-gradient(circle, rgba(251, 146, 60, 0.3), transparent 60%)",
          filter: "blur(60px)",
        }}
        aria-hidden="true"
      />

      {/* 3D Canvas */}
      <div className="absolute inset-0">
        <Canvas
          camera={{ position: [0, 0, 3], fov: 45 }}
          dpr={[1, 2]} // Cap device pixel ratio for performance
          gl={{
            antialias: true,
            alpha: true,
            powerPreference: "high-performance",
          }}
          onCreated={({ gl }) => {
            // Handle context loss
            gl.domElement.addEventListener("webglcontextlost", (e) => {
              e.preventDefault();
              console.warn("WebGL context lost");
            });

            gl.domElement.addEventListener("webglcontextrestored", () => {
              console.log("WebGL context restored");
            });
          }}
        >
          <Suspense fallback={null}>
            <ProcurementGlobe scrollProgress={scrollProgress} />
          </Suspense>
        </Canvas>
      </div>

      {/* Floating labels */}
      <div className="relative z-10 h-full">
        {LABELS.map((label) => (
          <div
            key={label.text}
            className="absolute animate-rise"
            style={{
              left: label.position.x,
              top: label.position.y,
              animationDelay: `${1000 + label.delay * 1000}ms`,
            }}
          >
            <div className="glass rounded-lg px-4 py-2 backdrop-blur-md">
              <span className="text-[12px] font-medium text-muted-foreground">{label.text}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Note */}
      <div className="absolute bottom-8 left-1/2 z-10 -translate-x-1/2 text-center">
        <p className="text-[11px] text-subtle">
          Conceptual visualization — EPI is self-hosted and does not maintain a global network.
        </p>
      </div>
    </section>
  );
}

/**
 * Fallback for unsupported WebGL.
 */
function GlobeFallback() {
  return (
    <section className="relative min-h-[100vh] overflow-hidden bg-ink px-5 py-24">
      <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center text-center">
        <div className="mb-8 h-40 w-40 rounded-full border-2 border-white/10 bg-white/[0.02]" />
        <h2 className="text-section text-balance">Global Procurement Network</h2>
        <p className="mt-4 text-[14px] leading-relaxed text-muted-foreground">
          Procurement records, supplier relationships, and contract intelligence connected across your organization.
        </p>
        <p className="mt-6 text-[11px] text-subtle">
          (3D visualization requires WebGL support)
        </p>
      </div>
    </section>
  );
}
