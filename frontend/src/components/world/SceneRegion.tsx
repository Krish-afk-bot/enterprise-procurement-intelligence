import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type PointerEvent as ReactPointerEvent,
  type MouseEvent as ReactMouseEvent,
} from "react";
import type { ElementRef } from "react";
import { OrbitControls, OrthographicCamera, PerspectiveCamera, View } from "@react-three/drei";

import { setInteractiveElement } from "@/lib/worldBus";
import { cn } from "@/lib/utils";

type Controls = ElementRef<typeof OrbitControls>;

/**
 * The region's own DOM box, handed to the labels drawn inside it.
 *
 * The `Provider` lives *inside* the View's children on purpose: `<View>` is a
 * tunnel, so its children are rendered inside the canvas' React tree, where a
 * context created on the page no longer reaches. Placing it here means a label
 * deep in the scene still resolves the box it belongs to.
 *
 * Labels are positioned from a fresh `getBoundingClientRect()` of that box
 * rather than from the canvas' cached size, which is what keeps them attached
 * to their record while the page scrolls or the sidebar is collapsed.
 */
const RegionTrack = createContext<HTMLElement | null>(null);

export function useRegionTrack(): HTMLElement | null {
  return useContext(RegionTrack);
}

export interface SceneRegionProps {
  /** Box height in CSS pixels; the width follows the container. */
  height: number;
  /** Describes the picture for a screen reader. Required unless decorative. */
  ariaLabel?: string;
  /** Decorative regions (the band) are hidden from assistive technology. */
  decorative?: boolean;
  children: ReactNode;
  className?: string;
  cameraPosition?: [number, number, number];
  fov?: number;
  minDistance?: number;
  maxDistance?: number;
  enablePan?: boolean;
  autoRotate?: boolean;
  autoRotateSpeed?: number;
  damping?: boolean;
  /** Off for the band, which is decoration and has nothing to orbit. */
  controls?: boolean;
  controlsRef?: React.Ref<Controls>;
  /** Pixel-space orthographic camera, used by the band. */
  orthographic?: boolean;
  /** Read pointer events from this region's box. Only one region at a time. */
  interactive?: boolean;
  /** Draw order across regions. The band uses 1 like every other region. */
  index?: number;
  onPointerMove?: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onPointerLeave?: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onClick?: (event: ReactMouseEvent<HTMLDivElement>) => void;
}

/**
 * One 3D rectangle of the page, drawn by the workspace's shared canvas.
 *
 * The scene is portalled into its own `THREE.Scene` with its own camera, so it
 * can orbit and reset without disturbing the other regions on the page, and it
 * is drawn into exactly this box with a scissor — the geometry physically
 * cannot paint over the text, tables and controls outside it.
 *
 * The element returned by `<View ref>` is the region's DOM box: it is what the
 * canvas listens to for pointer events and what labels are portalled into.
 */
export function SceneRegion({
  height,
  ariaLabel,
  decorative = false,
  children,
  className,
  cameraPosition = [0, 1.6, 5.2],
  fov = 42,
  minDistance = 2.4,
  maxDistance = 9,
  enablePan = true,
  autoRotate = false,
  autoRotateSpeed = 0.3,
  damping = true,
  controls: showControls = true,
  controlsRef,
  orthographic = false,
  interactive = false,
  index = 1,
  onPointerMove,
  onPointerLeave,
  onClick,
}: SceneRegionProps) {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [trackEl, setTrackEl] = useState<HTMLDivElement | null>(null);
  const setTrack = useCallback((element: HTMLDivElement | null) => {
    trackRef.current = element;
    setTrackEl(element);
  }, []);

  useEffect(() => {
    if (!interactive || !trackEl) return;
    setInteractiveElement(trackEl);
    return () => setInteractiveElement(null);
  }, [interactive, trackEl]);

  return (
    <div
      // Above the canvas so labels stay readable, and positioned so the region
      // owns exactly this rectangle. It carries no background: the canvas
      // draws underneath it and the card's own surface shows through.
      className={cn("relative z-20", className)}
      style={{ height }}
      role={decorative ? undefined : "img"}
      aria-label={decorative ? undefined : ariaLabel}
      aria-hidden={decorative ? true : undefined}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
      onClick={onClick}
    >
      <View ref={setTrack} className="absolute inset-0" index={index} frames={Infinity}>
        <RegionTrack.Provider value={trackEl}>
          {orthographic ? (
            <BandCamera />
          ) : (
            <PerspectiveCamera makeDefault position={cameraPosition} fov={fov} near={0.1} far={400} />
          )}
          <ambientLight intensity={0.85} />
          <directionalLight position={[3, 6, 4]} intensity={0.55} />
          <directionalLight position={[-4, -2, -3]} intensity={0.2} />
          {children}
          {showControls ? (
            <OrbitControls
              ref={controlsRef}
              makeDefault
              // Bound to this region's own box rather than to the canvas, so
              // the scene can be dragged even though the canvas ignores pointers.
              domElement={trackEl ?? undefined}
              enablePan={enablePan}
              enableZoom
              enableDamping={damping}
              dampingFactor={0.08}
              autoRotate={autoRotate}
              autoRotateSpeed={autoRotateSpeed}
              minDistance={minDistance}
              maxDistance={maxDistance}
              maxPolarAngle={Math.PI / 2.05}
            />
          ) : null}
        </RegionTrack.Provider>
      </View>
    </div>
  );
}

/** Pixel-space camera for the band: one world unit is one CSS pixel. */
export function BandCamera() {
  return <OrthographicCamera makeDefault position={[0, 0, 600]} near={-1000} far={1000} />;
}
