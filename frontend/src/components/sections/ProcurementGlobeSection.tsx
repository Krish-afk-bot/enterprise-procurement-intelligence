import { Suspense, lazy } from "react";
import { LANDING_CONTENT } from "@/content/landing";
import { WordReveal } from "@/components/animations/WordReveal";
import { Globe } from "lucide-react";

const ProcurementGlobe = lazy(() =>
  import("@/components/three/ProcurementGlobe").then((m) => ({ default: m.ProcurementGlobe }))
);

export function ProcurementGlobeSection() {
  return (
    <section id="globe" className="relative pt-16 lg:pt-20 pb-28 px-6 bg-[#050505] text-white scroll-mt-[112px]">
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

        <p className="text-sm sm:text-base text-white/60 max-w-xl mb-8">
          {LANDING_CONTENT.globe.subtitle}
        </p>

        {/* Non-numeric category chips (Replaced unverified numeric stats) */}
        <div className="flex flex-wrap items-center justify-center gap-3 mb-10">
          {["Contracts", "Suppliers", "Amendments"].map((chip) => (
            <div
              key={chip}
              className="px-5 py-2 rounded-full bg-white/[0.04] border border-white/10 backdrop-blur-md flex items-center gap-2"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-[#FF4D00]" />
              <span className="text-xs font-semibold text-white/90 tracking-wide">{chip}</span>
            </div>
          ))}
        </div>

        {/* 3D WebGL Globe Container: min-h-[640px] with generous no-clip padding & soft outer halo */}
        <div className="relative w-full max-w-3xl min-h-[640px] h-[640px] flex items-center justify-center mt-2 mb-8">
          {/* Soft outer amber-to-orange glow halo */}
          <div className="absolute w-[440px] h-[440px] rounded-full bg-gradient-to-tr from-[#FF4D00]/20 via-[#FF7A1A]/8 to-transparent blur-3xl pointer-events-none -z-10" />

          <Suspense
            fallback={
              <div className="w-56 h-56 rounded-full border border-white/10 animate-pulse flex items-center justify-center text-white/40 text-xs font-mono">
                INITIALIZING NETWORK TOPOLOGY...
              </div>
            }
          >
            <ProcurementGlobe className="w-full h-full" />
          </Suspense>
        </div>

        {/* Conceptual visualization caption (explicitly states no real coverage/location claims) */}
        <p className="text-xs text-white/50 max-w-lg mt-2 block font-medium">
          Conceptual visualization — Nodes represent document entity connections, not geographic locations.
        </p>
        <p className="text-[11px] text-white/35 max-w-md mt-1 block font-mono">
          {LANDING_CONTENT.globe.disclaimer}
        </p>
      </div>
    </section>
  );
}
