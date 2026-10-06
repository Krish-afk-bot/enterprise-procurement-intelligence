import { useThree } from "@react-three/fiber";

import { BAND_ROUTES, type BandRouteKey } from "@/components/world/bandRoutes";
import { Courier } from "@/components/world/Courier";
import { PaperFlow } from "@/components/world/PaperFlow";
import { Watcher } from "@/components/world/Watcher";
import { OBJECT_BUDGET, type DeviceTier } from "@/lib/deviceTier";
import type { QualityTier } from "@/store/world";

/**
 * What the band draws for the page that is open.
 *
 * Every value it reads comes from the route registry and from the tier the
 * device can afford — real application state, never a timer. The registry
 * itself lives in `bandRoutes.ts` because the written band needs it too, and
 * that module must stay free of three.js.
 */
export function BandScene({
  route,
  quality,
  calm,
  hideBuddy,
}: {
  route: BandRouteKey;
  quality: QualityTier;
  calm: boolean;
  hideBuddy: boolean;
}) {
  const size = useThree((state) => state.size);
  const tier: DeviceTier = quality === "static" ? "low" : quality;
  const config = BAND_ROUTES[route] ?? BAND_ROUTES.other;
  const budget = OBJECT_BUDGET[tier];
  const paper = Math.max(4, Math.round(budget.paper * config.paper));
  // The Watcher peeks over the floor of the band: its contact shadow lands on
  // the band's bottom edge at any band height, and it stays clear of the courier.
  const watcherPosition: [number, number] = [-size.width / 2 + 74, -size.height / 2 + 47];

  return (
    <>
      <PaperFlow calm={calm} count={paper} />
      {hideBuddy ? null : <Courier calm={calm} label={config.caseLabel} />}
      {hideBuddy ? null : <Watcher position={watcherPosition} calm={calm} />}
    </>
  );
}
