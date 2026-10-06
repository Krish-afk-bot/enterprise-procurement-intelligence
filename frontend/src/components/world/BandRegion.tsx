import type { MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent } from "react";

import { BandScene } from "@/components/world/BandScene";
import type { BandRouteKey } from "@/components/world/bandRoutes";
import { SceneRegion } from "@/components/world/SceneRegion";
import { WorldErrorBoundary } from "@/components/world/context";
import WorldCanvas from "@/components/world/WorldCanvas";
import type { QualityTier } from "@/store/world";

/**
 * The band's 3D subtree, kept behind one dynamic import.
 *
 * Everything three.js touches — the renderer, the region primitive, the two
 * characters and the paper — is reachable only from here, so the initial bundle
 * carries a loader and an SVG band and nothing else. When this module is still
 * being fetched the written band is on screen, which is why the fallback is a
 * real drawing rather than a spinner.
 */
export interface BandRegionProps {
  height: number;
  quality: QualityTier;
  calm: boolean;
  hideBuddy: boolean;
  route: BandRouteKey;
  onFail: () => void;
  onClick: (event: ReactMouseEvent<HTMLDivElement>) => void;
  onPointerMove: (event: ReactPointerEvent<HTMLDivElement>) => void;
}

export default function BandRegion({
  height,
  quality,
  calm,
  hideBuddy,
  route,
  onFail,
  onClick,
  onPointerMove,
}: BandRegionProps) {
  return (
    <WorldErrorBoundary onFail={onFail}>
      <WorldCanvas quality={quality} calm={calm} />
      <SceneRegion
        className="absolute inset-0"
        height={height}
        decorative
        orthographic
        controls={false}
        onClick={onClick}
        onPointerMove={onPointerMove}
      >
        <BandScene route={route} quality={quality} calm={calm} hideBuddy={hideBuddy} />
      </SceneRegion>
    </WorldErrorBoundary>
  );
}
