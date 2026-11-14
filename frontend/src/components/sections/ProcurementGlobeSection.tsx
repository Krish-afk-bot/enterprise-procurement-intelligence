import { Suspense, lazy } from "react";
import { LANDING_CONTENT } from "@/content/landing";
import { WordReveal } from "@/components/animations/WordReveal";
import { Globe } from "lucide-react";

const ProcurementGlobe = lazy(() =>
  import("@/components/three/ProcurementGlobe").then((m) => ({ default: m.ProcurementGlobe }))
);

export function ProcurementGlobeSection() {
  return (
    <section id="globe" className="relative py-28 px-6 bg-[#050505] text-white">
      <div className="relative z-10 max-w-6xl mx-auto flex flex-col items-center text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider uppercase bg-white/5 border border-white/10 text-white/80 mb-6">
          <Globe className="w-3.5 h-3.5 text-[#FF4D00]" />
          <span>{LANDING_CONTENT.globe.badge}</span>
        </div>

        {/* Heading */}
        <WordReveal
          as="h2"
          mode="scroll"
          className="text-3xl sm:text-5xl font-bold tracking-tight text-white mb-6 max-w-2xl"
        >
          {LANDING_CONTENT.globe.heading}
        </WordReveal>

        <p className="text-sm sm:text-base text-white/60 max-w-xl mb-12">
          {LANDING_CONTENT.globe.subtitle}
        </p>

        {/* Conceptual Metrics Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-2xl mb-14">
          {LANDING_CONTENT.globe.nodes.map((node) => (
            <div
              key={node.id}
              className="p-4 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-md flex flex-col items-center"
            >
              <span className="text-xl sm:text-2xl font-bold text-white mb-1">{node.count}</span>
              <span className="text-xs text-white/50">{node.label}</span>
            </div>
          ))}
        </div>

        {/* 3D WebGL Globe Container: min-h-[640px] with generous no-clip padding */}
        <div className="relative w-full max-w-3xl min-h-[640px] h-[640px] flex items-center justify-center mt-6 mb-12">
          <Suspense
            fallback={
              <div className="w-56 h-56 rounded-full border border-white/10 animate-pulse flex items-center justify-center text-white/40 text-xs">
                INITIALIZING NETWORK TOPOLOGY...
              </div>
            }
          >
            <ProcurementGlobe className="w-full h-full" />
          </Suspense>
        </div>

        {/* Disclaimer with clear top margin */}
        <p className="text-[11px] text-white/35 max-w-md mt-4 block font-mono">
          {LANDING_CONTENT.globe.disclaimer}
        </p>
      </div>
    </section>
  );
}
