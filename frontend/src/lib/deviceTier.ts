/**
 * The quality tier a device starts at.
 *
 * Signals are only used when the browser really exposes them; nothing here is
 * guessed and presented as measured. The tier is a starting point — the canvas
 * lowers it when frames actually take too long, and raises it back if they recover.
 */
export type DeviceTier = "high" | "medium" | "low";

interface NavigatorWithMemory extends Navigator {
  deviceMemory?: number;
}

export function initialTier(): DeviceTier {
  if (typeof window === "undefined") return "medium";

  const nav = navigator as NavigatorWithMemory;
  const cores = nav.hardwareConcurrency ?? 4;
  const memory = nav.deviceMemory ?? null;
  const width = window.innerWidth;
  const dpr = window.devicePixelRatio || 1;

  // A phone-sized screen gets the lightest scene regardless of its specifications.
  if (width < 768) return "low";

  // 4 GB of RAM or fewer is reported by the browser as 4; treat it as a constraint.
  if (memory !== null && memory <= 4) return "medium";
  if (cores <= 4) return "medium";

  // A very dense display pays for its extra pixels in the pixel-ratio cap.
  if (dpr >= 3) return "medium";

  if (width < 1280) return "medium";
  return "high";
}

/** Pixel-ratio caps per tier. The world never renders above 1.5 device pixels. */
export const DPR_CAP: Record<DeviceTier, number> = { high: 1.5, medium: 1.25, low: 1 };

/** How many decorative objects each tier may draw. */
export const OBJECT_BUDGET: Record<DeviceTier, { paper: number; shadows: boolean; particles: number }> = {
  high: { paper: 26, shadows: true, particles: 60 },
  medium: { paper: 14, shadows: false, particles: 26 },
  low: { paper: 7, shadows: false, particles: 10 },
};

/**
 * Frame budget: the tier drops when the rolling average frame time stays above this
 * for two seconds, and recovers when it stays comfortably below for ten.
 */
export const FRAME_BUDGET_MS = 22;
export const FRAME_RECOVER_MS = 12;
