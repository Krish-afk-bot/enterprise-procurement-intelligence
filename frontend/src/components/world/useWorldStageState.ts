import { useEffect, useState } from "react";

import { useReducedMotion } from "@/lib/useReducedMotion";
import { hasWebGL } from "@/lib/useMediaQuery";
import { useWorld, type QualityTier } from "@/store/world";

import { useWorldBand, type WorldBand } from "./context";

/**
 * The one place that decides whether the workspace draws its 3D layer, and why
 * when it does not. The shell needs the answer before the canvas exists — it
 * has to provide the context the page scenes read — so the decision lives here
 * rather than inside the lazy chunk.
 */
export interface WorldStageState {
  band: WorldBand;
  /** `null` until the deferred WebGL probe answers. */
  webgl: boolean | null;
  /** The 3D layer threw; drop to the written band for this session. */
  failed: boolean;
  fail: () => void;
  quality: QualityTier;
  /** Reduced motion or "Reduce effects": the world draws, but does not move. */
  calm: boolean;
  reducedMotion: boolean;
  hideBuddy: boolean;
  reduceEffects: boolean;
  drawCanvas: boolean;
}

export function useWorldStageState(): WorldStageState {
  const band = useWorldBand();
  const [webgl, setWebgl] = useState<boolean | null>(null);
  const [failed, setFailed] = useState(false);
  const reducedMotion = useReducedMotion();
  const reduceEffects = useWorld((state) => state.reduceEffects);
  const hideBuddy = useWorld((state) => state.hideBuddy);
  const quality = useWorld((state) => state.quality);

  // Deferred so the first paint is never blocked by a driver probe.
  useEffect(() => {
    setWebgl(hasWebGL());
  }, []);

  return {
    band,
    webgl,
    failed,
    fail: () => setFailed(true),
    quality,
    calm: reducedMotion || reduceEffects,
    reducedMotion,
    hideBuddy,
    reduceEffects,
    drawCanvas: webgl === true && !band.small && quality !== "static" && !failed,
  };
}
