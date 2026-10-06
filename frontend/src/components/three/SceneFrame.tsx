import { Suspense, useEffect, useRef, useState, type ElementRef, type ReactNode } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { Compass, Eye, EyeOff, Pause, Play } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SceneRegion } from "@/components/world/SceneRegion";
import { useWorldCanvasAvailable } from "@/components/world/context";
import { useReducedMotion } from "@/lib/useReducedMotion";
import { hasWebGL, useReducedDetail, useSmallScreen } from "@/lib/useMediaQuery";
import { cn } from "@/lib/utils";
import { scenePalette } from "@/components/three/palette";

/**
 * Shared frame for every 3D surface.
 *
 * The rules are enforced here rather than in each scene, so a scene cannot
 * forget one: the canvas only exists when the browser can draw it and the
 * screen is big enough for it, motion stops when the system asks for reduced
 * motion or the reader pauses it, the pixel ratio is capped, and a written
 * description plus a way back to the plain view is always present.
 */
export function SceneFrame({
  title,
  caption,
  ariaLabel,
  fallback,
  children,
  className,
  height = 340,
  showControls = true,
  enablePan = true,
  autoRotateSpeed = 0.3,
  cameraPosition = [0, 1.6, 5.2],
  maxDistance = 9,
  legend,
}: {
  title: string;
  caption: string;
  ariaLabel: string;
  /** Shown instead of the canvas whenever 3D is off, too small, or unsupported. */
  fallback: ReactNode;
  children: ReactNode;
  className?: string;
  height?: number;
  showControls?: boolean;
  enablePan?: boolean;
  autoRotateSpeed?: number;
  cameraPosition?: [number, number, number];
  maxDistance?: number;
  /** Optional key below the canvas: what each colour means. */
  legend?: ReactNode;
}) {
  const reduced = useReducedMotion();
  const smallScreen = useSmallScreen();
  const reducedDetail = useReducedDetail();
  const sharedCanvas = useWorldCanvasAvailable();
  const [webgl, setWebgl] = useState<boolean | null>(null);
  const [hidden, setHidden] = useState(false);
  const [paused, setPaused] = useState(false);
  // Typed from the component itself rather than from `three-stdlib`, which is
  // only a transitive dependency of drei and could move without notice.
  const controls = useRef<ElementRef<typeof OrbitControls> | null>(null);
  const palette = scenePalette();
  // Reduced motion wins: the scene is drawn once and never animates.
  const motionOn = !reduced && !paused;

  // The check is deferred to an effect so the first paint is never blocked and
  // a browser without WebGL simply gets the written alternative.
  useEffect(() => {
    setWebgl(hasWebGL());
  }, []);

  const reason = webgl === false ? "3D is not available in this browser" : smallScreen ? "3D is off on a small screen" : null;
  const drawCanvas = webgl === true && !smallScreen && !hidden && sharedCanvas !== false;

  return (
    <figure className={cn("overflow-hidden rounded-lg border bg-card", className)}>
      <figcaption className="flex flex-wrap items-center gap-2 border-b px-3 py-2">
        <span className="text-xs font-semibold">{title}</span>
        <span className="min-w-0 flex-1 text-[11px] text-muted-foreground">{caption}</span>
        {reduced ? (
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Animation off — reduced motion</span>
        ) : null}
        {reason ? (
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{reason}</span>
        ) : null}
        {showControls && webgl !== false && !smallScreen ? (
          <div className="flex items-center gap-1">
            {!reduced && !hidden ? (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1 px-2 text-[11px]"
                  onClick={() => setPaused((value) => !value)}
                  aria-pressed={paused}
                >
                  {paused ? <Play className="h-3 w-3" aria-hidden="true" /> : <Pause className="h-3 w-3" aria-hidden="true" />}
                  {paused ? "Resume motion" : "Pause motion"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1 px-2 text-[11px]"
                  onClick={() => controls.current?.reset()}
                >
                  <Compass className="h-3 w-3" aria-hidden="true" />
                  Reset view
                </Button>
              </>
            ) : null}
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 px-2 text-[11px]"
              aria-pressed={hidden}
              onClick={() => setHidden((value) => !value)}
            >
              {hidden ? <Eye className="h-3 w-3" aria-hidden="true" /> : <EyeOff className="h-3 w-3" aria-hidden="true" />}
              {hidden ? "Show 3D" : "Hide 3D"}
            </Button>
          </div>
        ) : null}
      </figcaption>

      {drawCanvas && sharedCanvas ? (
        // The workspace owns one canvas for the whole application. The scene is
        // drawn into this rectangle by that canvas, so no second WebGL context
        // is created and the geometry is clipped to the figure it belongs to.
        <SceneRegion
          height={height}
          ariaLabel={ariaLabel}
          className="w-full"
          cameraPosition={cameraPosition}
          maxDistance={maxDistance}
          autoRotate={motionOn}
          autoRotateSpeed={autoRotateSpeed}
          damping={motionOn}
          enablePan={enablePan}
          controlsRef={controls}
          interactive
        >
          {children}
        </SceneRegion>
      ) : drawCanvas ? (
        <div style={{ height }} role="img" aria-label={ariaLabel} className="bg-background">
          <Suspense fallback={<div className="h-full w-full bg-muted/30" aria-hidden="true" />}>
            <Canvas
              dpr={[1, reducedDetail ? 1.25 : 1.75]}
              camera={{ position: cameraPosition, fov: 42 }}
              gl={{ antialias: !reducedDetail, powerPreference: "low-power" }}
              frameloop={motionOn ? "always" : "demand"}
              onCreated={({ gl }) => gl.setClearColor(palette.background)}
            >
              <ambientLight intensity={0.85} />
              <directionalLight position={[3, 6, 4]} intensity={0.55} />
              <directionalLight position={[-4, -2, -3]} intensity={0.2} />
              {children}
              <OrbitControls
                ref={controls}
                makeDefault
                enablePan={enablePan}
                enableZoom
                enableDamping={motionOn}
                dampingFactor={0.08}
                autoRotate={motionOn}
                autoRotateSpeed={autoRotateSpeed}
                minDistance={2.4}
                maxDistance={maxDistance}
                maxPolarAngle={Math.PI / 2.05}
              />
            </Canvas>
          </Suspense>
        </div>
      ) : (
        <div className="p-3">{fallback}</div>
      )}

      {legend ? <div className="border-t px-3 py-2">{legend}</div> : null}
    </figure>
  );
}
