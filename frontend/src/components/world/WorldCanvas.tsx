import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { View } from "@react-three/drei";
import * as THREE from "three";

import { scenePalette } from "@/components/three/palette";
import { DPR_CAP, FRAME_BUDGET_MS, FRAME_RECOVER_MS, initialTier, type DeviceTier } from "@/lib/deviceTier";
import { getInteractiveElement, subscribeWorld } from "@/lib/worldBus";
import { useWorld, type QualityTier } from "@/store/world";

/**
 * The one WebGL canvas of the workspace.
 *
 * It is lazy: this module is the only place three.js is imported eagerly, and it
 * is fetched when the workspace first renders. Everything page-shaped is drawn
 * by `<View />` regions that live on the page itself; what lives here is the
 * infrastructure they share — the framebuffer, the frame budget, the pause when
 * the tab is hidden, and the hand-off of pointer events to whichever region is
 * interactive.
 *
 * It is `pointer-events: none` and `aria-hidden`: nothing on it can be clicked
 * and nothing on it is read out. All of the real interaction happens in the DOM
 * around it.
 *
 * The `style` set on `<Canvas>` is load-bearing. r3f writes
 * `pointerEvents: "auto"` on its own wrapper element, which would override the
 * `pointer-events-none` of the overlay above it and put an invisible surface
 * across the whole application: every button, link and table beneath the world
 * would stop responding to the mouse. r3f spreads a caller's `style` after its
 * own defaults, so passing `pointerEvents: "none"` here is what keeps the world
 * decorative. Bands and scenes receive input through their own DOM elements,
 * never through the canvas.
 */

const TIER_ORDER: QualityTier[] = ["high", "medium", "low", "static"];
/** Antialiasing is a context-creation decision, so it is made once, not per frame. */
const ANTIALIAS = initialTier() === "high";
/** Recovery needs sustained headroom; one good second proves nothing. */
const RECOVER_AFTER_MS = 10_000;

/**
 * The framebuffer is never cleared by three here: every draw is a scissored
 * `View`. Clearing once at the top of the frame, before any view renders, is
 * what stops a moving sheet from smearing across the band.
 */
function FrameClear() {
  const gl = useThree((state) => state.gl);
  useFrame(() => {
    gl.setScissorTest(false);
    gl.autoClear = true;
    gl.clear(true, true, true);
  }, -1000);
  return null;
}

/**
 * Measures real frame times and moves the quality tier when the budget is missed
 * for two seconds straight, or when ten seconds of headroom say the tier can be
 * given back — never beyond what the device started at. The rolling window is
 * the only input, so nothing here is claimed that was not measured.
 */
function FrameMeter({ quality, metering }: { quality: QualityTier; metering: boolean }) {
  const sample = useRef({ sum: 0, frames: 0, fastest: Infinity, overSince: 0, underSince: 0 });

  useFrame((_state, delta) => {
    if (!metering) return;
    const s = sample.current;
    s.sum += delta;
    s.frames += 1;
    if (delta < s.fastest) s.fastest = delta;
    if (s.frames < 30) return;
    // `delta` arrives in seconds while the budgets are named in milliseconds, so
    // the conversion happens once, here. Comparing seconds against a
    // millisecond budget made the budget 22 seconds long, and no frame this
    // machine will ever draw could miss it: the whole ladder was unreachable.
    const averageMs = (s.sum / s.frames) * 1000;
    const fastestMs = s.fastest * 1000;
    s.sum = 0;
    s.frames = 0;
    s.fastest = Infinity;
    const now = performance.now();
    const world = useWorld.getState();

    if (averageMs > FRAME_BUDGET_MS) {
      s.underSince = 0;
      if (!s.overSince) s.overSince = now;
      if (now - s.overSince >= 2000) {
        s.overSince = 0;
        const index = Math.min(TIER_ORDER.indexOf(quality) + 1, TIER_ORDER.length - 1);
        const next = TIER_ORDER[index];
        if (next !== quality) world.setQuality(next);
      }
      return;
    }

    s.overSince = 0;
    // Headroom is judged against what this display can actually deliver: a
    // vsync-locked 60Hz screen never reports a frame below 16.7ms, so a fixed
    // floor alone would make recovery impossible on the most ordinary display
    // there is. Recovery still requires the budget itself to be met, so a
    // machine that is genuinely too slow cannot promote itself.
    const floorMs = Math.max(FRAME_RECOVER_MS, fastestMs * 1.4);
    if (averageMs <= FRAME_BUDGET_MS && averageMs < floorMs) {
      if (!s.underSince) s.underSince = now;
      if (now - s.underSince >= RECOVER_AFTER_MS) {
        s.underSince = 0;
        const ceiling = TIER_ORDER.indexOf(initialTier() as QualityTier);
        const next = TIER_ORDER[Math.max(Math.min(TIER_ORDER.indexOf(quality) - 1, ceiling), 0)];
        if (next !== quality) world.setQuality(next);
      }
      return;
    }
    s.underSince = 0;
  }, -100);

  return null;
}

/**
 * Pointer events reach r3f through exactly one DOM element. The canvas cannot be
 * that element — it has to ignore the pointer so the application stays clickable
 * — so the event layer is moved onto whichever region has asked to be
 * interactive, and moved back when that region goes away.
 */
function EventBridge() {
  const get = useThree((state) => state.get);
  const connect = useThree((state) => state.events.connect);
  const element = useSyncExternalStore(subscribeWorld, getInteractiveElement, () => null);

  useEffect(() => {
    if (!element || !connect) return;
    const previous = get().events.connected;
    connect(element);
    return () => {
      if (previous) connect(previous);
    };
  }, [element, connect, get]);

  return null;
}

/**
 * With the loop in `demand` mode nothing is drawn until something asks. These
 * are the things that can: a cursor, a click, a scroll, a resize, or another
 * region publishing itself. Each ask is coalesced into one animation frame, so
 * following the cursor never turns into a render loop.
 */
function DemandInvalidation({ enabled }: { enabled: boolean }) {
  const invalidate = useThree((state) => state.invalidate);
  const queued = useRef(false);

  useEffect(() => {
    if (!enabled) return;
    const ask = () => {
      if (queued.current) return;
      queued.current = true;
      requestAnimationFrame(() => {
        queued.current = false;
        invalidate();
      });
    };
    ask();
    window.addEventListener("pointermove", ask, { passive: true });
    window.addEventListener("pointerdown", ask, { passive: true });
    window.addEventListener("scroll", ask, { passive: true });
    window.addEventListener("resize", ask);
    const unsubscribe = subscribeWorld(ask);
    return () => {
      window.removeEventListener("pointermove", ask);
      window.removeEventListener("pointerdown", ask);
      window.removeEventListener("scroll", ask);
      window.removeEventListener("resize", ask);
      unsubscribe();
    };
  }, [enabled, invalidate]);

  return null;
}

/** True while the tab is not the one being looked at: rendering stops entirely. */
function useVisibility(): boolean {
  const [hidden, setHidden] = useState(
    () => typeof document !== "undefined" && document.visibilityState === "hidden",
  );

  useEffect(() => {
    const update = () => setHidden(document.visibilityState === "hidden");
    update();
    document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);

  return hidden;
}

export interface WorldCanvasProps {
  quality: QualityTier;
  calm: boolean;
}

export default function WorldCanvas({ quality, calm }: WorldCanvasProps) {
  const palette = useMemo(() => scenePalette(), []);
  const tier: DeviceTier = quality === "static" ? "low" : quality;
  const dpr = useMemo<[number, number]>(() => [1, DPR_CAP[tier]], [tier]);
  const hidden = useVisibility();
  const frameloop = hidden ? "never" : calm ? "demand" : "always";

  return (
    <div className="pointer-events-none fixed inset-0 z-10" aria-hidden="true">
      <Canvas
        dpr={dpr}
        frameloop={frameloop}
        style={{ pointerEvents: "none" }}
        gl={{ alpha: true, antialias: ANTIALIAS, powerPreference: "low-power" }}
        onCreated={({ gl }) => gl.setClearColor(new THREE.Color(palette.background), 0)}
      >
        <View.Port />
        <FrameClear />
        <FrameMeter quality={quality} metering={frameloop === "always"} />
        <EventBridge />
        <DemandInvalidation enabled={frameloop === "demand"} />
      </Canvas>
    </div>
  );
}
