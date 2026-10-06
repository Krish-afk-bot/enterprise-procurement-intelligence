import { Component, createContext, useContext, type ErrorInfo, type ReactNode } from "react";

import { useReducedDetail, useSmallScreen } from "@/lib/useMediaQuery";

/**
 * Whether the workspace's shared canvas is available.
 *
 *   `null`  — no world stage at all (the public pages), so a page may open its
 *             own canvas.
 *   `true`  — the shared canvas is running: 3D surfaces must draw into it.
 *   `false` — the shared canvas is off (no WebGL, a phone, or the workspace was
 *             dropped to the static tier): show the written alternative.
 *
 * This module deliberately imports nothing from three.js. It is the only piece
 * of the world layer the initial bundle has to carry.
 */
export const WorldCanvasContext = createContext<boolean | null>(null);

export function useWorldCanvasAvailable(): boolean | null {
  return useContext(WorldCanvasContext);
}

/** Sizes of the band of workspace the 3D layer is allowed to draw in. */
export const BAND_CONTROL_ROW = 34;

export interface WorldBand {
  /** Height of the 3D rectangle itself. */
  height: number;
  /** The controls strip above it. */
  control: number;
  /** Everything the band occupies, so page content can be padded clear of it. */
  total: number;
  /** True on a phone, which gets the SVG band instead of the canvas. */
  small: boolean;
}

export function useWorldBand(): WorldBand {
  const small = useSmallScreen();
  const tablet = useReducedDetail();
  const height = small ? 64 : tablet ? 80 : 96;
  return { height, control: BAND_CONTROL_ROW, total: height + BAND_CONTROL_ROW, small };
}

/**
 * Catches a failure of the 3D layer (a context that cannot be created, a driver
 * that refuses) and reports it so the band falls back to its written version
 * rather than showing an empty rectangle.
 */
export class WorldErrorBoundary extends Component<
  { onFail: () => void; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surfaced in the console on purpose: an empty 3D layer is a defect worth
    // seeing, not something to swallow.
    console.warn("The 3D world could not start; showing the written band instead.", error, info);
    this.props.onFail();
  }

  render() {
    return this.state.failed ? null : this.props.children;
  }
}
