import { Suspense, lazy, useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { bandCaseLabel, bandRouteKey } from "@/components/world/bandRoutes";
import { StaticBand } from "@/components/world/StaticBand";
import { WorldCanvasContext, useWorldBand } from "@/components/world/context";
import { useWorldStageState } from "@/components/world/useWorldStageState";
import { MICROCOPY, WATCHER_CLICKS, pick, type MicrocopyKey } from "@/content/microcopy";
import { initialTier } from "@/lib/deviceTier";
import { installFocusTracking, installPointerTracking, setPointerTracking } from "@/lib/pointer";
import { hitTestBand, nudgeCourier, pokeCourier } from "@/lib/worldBus";
import { useWorld } from "@/store/world";

/**
 * The band of the workspace: the persistent 3D strip every authenticated page
 * shares, the two settings that change it, and the written version used when it
 * cannot be drawn.
 *
 * This module is small and eager on purpose. It is the only piece of the world
 * layer the first paint has to carry; the canvas and every scene behind it are
 * fetched separately, so the initial bundle grows by the size of this file and
 * nothing else.
 */

/**
 * The whole 3D band — renderer, region, characters — is one dynamic import, so
 * three.js never reaches a reader who has not yet had a first paint.
 */
const BandRegion = lazy(() => import("@/components/world/BandRegion"));

interface BandLine {
  say: string;
  plain: string;
}

export function WorldStage({ children }: { children: React.ReactNode }) {
  const stage = useWorldStageState();
  const band = useWorldBand();
  const location = useLocation();
  const bandRef = useRef<HTMLDivElement>(null);
  const [line, setLine] = useState<BandLine | null>(null);
  const lineKey = useRef(0);

  const showKey = useCallback((key: MicrocopyKey) => {
    lineKey.current += 1;
    setLine({ say: MICROCOPY[key].say, plain: MICROCOPY[key].plain });
  }, []);

  // The world is decorative: its two settings are the reader's to make, and the
  // pointer snapshot only exists while something is actually following it.
  useEffect(() => {
    installPointerTracking();
    installFocusTracking();
  }, []);

  useEffect(() => {
    setPointerTracking(!stage.calm);
  }, [stage.calm]);

  // Quality starts from what the device says it can afford, not from a guess.
  useEffect(() => {
    const world = useWorld.getState();
    world.setQuality(world.reduceEffects ? "low" : initialTier());
  }, []);

  useEffect(() => {
    if (!line) return;
    const timer = window.setTimeout(() => setLine(null), 8000);
    return () => window.clearTimeout(timer);
  }, [line]);

  const onBandClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const hit = hitTestBand(event.clientX, event.clientY, rect);
    if (hit === "watcher") {
      useWorld.getState().pokeWatcher();
      showKey(pick(WATCHER_CLICKS, Date.now()));
    } else if (hit === "courier") {
      pokeCourier();
      showKey("courierBusy");
    }
  };

  const onBandMove = (event: React.PointerEvent<HTMLDivElement>) => {
    nudgeCourier(event.clientX, event.currentTarget.getBoundingClientRect());
  };

  const route = bandRouteKey(location.pathname);

  return (
    <WorldCanvasContext.Provider value={stage.webgl === null ? true : stage.drawCanvas}>
      <section aria-label="Workspace miniature" className="mb-5">
        <div className="flex h-[34px] flex-wrap items-center gap-2">
          <p className="text-[11px] text-muted-foreground">
            Miniature workspace
            <span className="mx-1.5" aria-hidden="true">
              ·
            </span>
            <span className="hidden sm:inline">decorative — every record it hints at is listed on the page</span>
          </p>
          <div className="ml-auto flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1.5 px-2 text-[11px]"
              aria-pressed={stage.reduceEffects}
              onClick={() => {
                const world = useWorld.getState();
                const next = !world.reduceEffects;
                world.setReduceEffects(next);
                showKey(next ? "effectsReduced" : "idle");
              }}
            >
              Reduce effects
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1.5 px-2 text-[11px]"
              aria-pressed={stage.hideBuddy}
              onClick={() => {
                const world = useWorld.getState();
                const next = !world.hideBuddy;
                world.setHideBuddy(next);
                if (next) showKey("buddyHidden");
              }}
            >
              Hide buddy
            </Button>
          </div>
        </div>

        <div ref={bandRef} className="relative" style={{ height: band.height }}>
          {stage.drawCanvas ? (
            // The surface behind the canvas. It is painted below the canvas so
            // the sheets and characters have something warm to sit on, and it
            // never sits above them: only the canvas may occupy this rectangle.
            <div
              aria-hidden="true"
              className="absolute inset-0 z-0 overflow-hidden rounded-lg border bg-[hsl(var(--paper))]"
            />
          ) : null}
          {line ? (
            <p
              role="status"
              className="pointer-events-none absolute right-2 top-1 z-10 max-w-[min(78%,26rem)] rounded-md border bg-background/95 px-2 py-1 text-[11px] shadow-sm"
            >
              <span className="block font-medium">{line.say}</span>
              <span className="block text-muted-foreground">{line.plain}</span>
            </p>
          ) : null}

          {stage.drawCanvas ? (
            <Suspense
              fallback={
                <div className="absolute inset-0 z-0">
                  <StaticBand label={bandCaseLabel(route)} hideBuddy={stage.hideBuddy} />
                </div>
              }
            >
              <BandRegion
                height={band.height}
                quality={stage.quality}
                calm={stage.calm}
                hideBuddy={stage.hideBuddy}
                route={route}
                onFail={stage.fail}
                onClick={onBandClick}
                onPointerMove={onBandMove}
              />
            </Suspense>
          ) : (
            <StaticBand label={bandCaseLabel(route)} hideBuddy={stage.hideBuddy} />
          )}        </div>
      </section>

      {children}
    </WorldCanvasContext.Provider>
  );
}
