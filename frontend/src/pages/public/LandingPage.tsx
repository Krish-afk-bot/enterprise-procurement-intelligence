import { useState } from "react";
import { Loader } from "@/components/sections/Loader";
import { HeroSection } from "@/components/sections/HeroSection";
import { ExplainerSection } from "@/components/sections/ExplainerSection";
import { FeatureBentoSection } from "@/components/sections/FeatureBentoSection";
import { ProcurementGlobeSection } from "@/components/sections/ProcurementGlobeSection";
import { EvidenceDemoSection } from "@/components/sections/EvidenceDemoSection";
import { UseCasesSection } from "@/components/sections/UseCasesSection";
import { CapabilitiesSection } from "@/components/sections/CapabilitiesSection";
import { FAQSection } from "@/components/sections/FAQSection";
import { SunriseCTASection } from "@/components/sections/SunriseCTASection";
import { ProductCrossSellSection } from "@/components/sections/ProductCrossSellSection";
import { SmoothScrollProvider } from "@/components/animations/SmoothScrollProvider";
import { MotionDebugOverlay } from "@/components/animations/MotionDebugOverlay";

export function LandingPage() {
  const [loaderComplete, setLoaderComplete] = useState(false);

  return (
    <SmoothScrollProvider>
      <MotionDebugOverlay />
      {/* Scene 00: Initial First-Visit Loader */}
      {!loaderComplete && <Loader onComplete={() => setLoaderComplete(true)} />}

      <div className="relative min-h-screen bg-[#050505] text-white">
        {/* Scene 01: Hero (Dark) */}
        <HeroSection />

        {/* Scene 02: Explainer (Light Section) */}
        <ExplainerSection />

        {/* Scene 03: Feature Bento (Dark) */}
        <FeatureBentoSection />

        {/* Scene 04: Signature 3D Globe (Dark) */}
        <ProcurementGlobeSection />

        {/* Scene 05: Evidence Demo (Light Section) */}
        <EvidenceDemoSection />

        {/* Scene 06: Use Cases (Light Section) */}
        <UseCasesSection />

        {/* Scene 07: Capabilities / Enterprise Tiers (Dark) */}
        <CapabilitiesSection />

        {/* Scene 08: FAQ Accordion (Dark) */}
        <FAQSection />

        {/* Scene 09: Sunrise CTA (Dark + Orange Sunrise) */}
        <SunriseCTASection />

        {/* Scene 10: Cross-Sell Grid (Dark) */}
        <ProductCrossSellSection />
      </div>
    </SmoothScrollProvider>
  );
}
