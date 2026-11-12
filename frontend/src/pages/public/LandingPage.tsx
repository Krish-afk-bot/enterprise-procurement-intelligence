import { useState } from "react";
import { Loader } from "@/components/sections/Loader";
import { HeroSection } from "@/components/sections/HeroSection";
import { ExplainerSection } from "@/components/sections/ExplainerSection";
import { FeatureBentoSection } from "@/components/sections/FeatureBentoSection";
import { ProcurementGlobeSection } from "@/components/sections/ProcurementGlobeSection";
import { EvidenceDemoSection } from "@/components/sections/EvidenceDemoSection";
import { UseCasesSection } from "@/components/sections/UseCasesSection";
import { FAQSection } from "@/components/sections/FAQSection";
import { SunriseCTASection } from "@/components/sections/SunriseCTASection";
import { ProductCrossSellSection } from "@/components/sections/ProductCrossSellSection";
import { AdaptiveNav } from "@/components/navigation/AdaptiveNav";
import { ScrollProgress } from "@/components/motion/ScrollProgress";

/**
 * Redesigned Landing Page - 11 Animated Scenes.
 *
 * Complete frame-by-frame motion experience with:
 * - Loader (ring → brand → curtain)
 * - Enhanced hero with word reveals and circuit animation
 * - Light explainer section with marquee chips
 * - Feature bento grid with mouse tilt
 * - Signature 3D procurement globe
 * - Evidence demo with pinned scroll
 * - Use cases grid
 * - FAQ accordion
 * - Sunrise CTA with orange gradient
 * - Product cross-sell
 * - Adaptive navigation pill
 */
export function LandingPage() {
  const [loaderComplete, setLoaderComplete] = useState(false);

  return (
    <>
      {/* Scene 00: Loader */}
      {!loaderComplete && <Loader onComplete={() => setLoaderComplete(true)} />}

      {/* Main content */}
      <div className="bg-ink text-foreground">
        <ScrollProgress />
        <AdaptiveNav />

        {/* Scene 01: Hero */}
        <HeroSection />

        {/* Scene 02: Explainer (light section) */}
        <ExplainerSection />

        {/* Scene 03: Feature Bento */}
        <FeatureBentoSection />

        {/* Scene 04: 3D Globe */}
        <ProcurementGlobeSection />

        {/* Scene 05: Evidence Demo */}
        <EvidenceDemoSection />

        {/* Scene 06: Use Cases (light section) */}
        <UseCasesSection />

        {/* Scene 08: FAQ */}
        <FAQSection />

        {/* Scene 09: Sunrise CTA */}
        <SunriseCTASection />

        {/* Scene 10: Product Cross-Sell */}
        <ProductCrossSellSection />

        {/* Scene 11: Footer is in PublicLayout */}
      </div>
    </>
  );
}
