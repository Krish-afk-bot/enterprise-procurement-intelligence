import { useCallback, useRef, type ComponentProps, type ReactNode } from "react";
import { Html } from "@react-three/drei";
import * as THREE from "three";

import { useRegionTrack } from "@/components/world/SceneRegion";

/** drei exports the component from its index but not its prop type, so derive it. */
type HtmlProps = Omit<ComponentProps<typeof Html>, "ref">;

const scratch = new THREE.Vector3();

/**
 * A label that is part of a 3D scene but is real DOM text.
 *
 * Two changes over a bare `Html`, both of them about living inside one canvas
 * that spans the whole viewport:
 *
 * 1. it is appended to its region's box, not to the canvas wrapper, so a label
 *    scrolls with the record it names;
 * 2. it is positioned from that box's *current* rectangle, so it stays attached
 *    when the layout changes underneath it (a collapsed sidebar, a window
 *    resize) instead of trusting a size captured at mount.
 *
 * The text is always readable by a screen reader and is never the only copy of
 * the fact it names: every scene that uses it also carries a written version.
 */
export function SceneLabel({
  children,
  position,
  center = true,
  distanceFactor,
  zIndexRange,
  ...rest
}: {
  children: ReactNode;
  position?: [number, number, number];
  center?: boolean;
  distanceFactor?: number;
  zIndexRange?: [number, number];
} & Omit<HtmlProps, "children" | "position" | "center" | "distanceFactor" | "zIndexRange">) {
  const track = useRegionTrack();
  const portalRef = useRef<HTMLElement | null>(null);
  if (track) portalRef.current = track;

  // `Html` keeps `style` and `className` for the DOM and hands every other prop
  // to the three.js group underneath it. A prop name with a dash is read by r3f
  // as a path — `aria-hidden` becomes `aria.hidden`, which throws while the
  // group is being built and takes the whole world down with it. Attributes that
  // only mean something in the DOM are therefore taken off here and put on the
  // wrapper element instead, where they do what they say.
  const domOnly: Record<string, unknown> = {};
  const threeProps: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(rest)) {
    if (key.includes("-")) domOnly[key] = value;
    else threeProps[key] = value;
  }

  const calculatePosition = useCallback(
    (object: THREE.Object3D, camera: THREE.Camera, region: { width: number; height: number }) => {
      // Prefer the region's live rectangle; fall back to the size drei cached,
      // which is what a scene drawn straight into its own canvas should use.
      const rect = portalRef.current?.getBoundingClientRect();
      const width = rect ? rect.width : region.width;
      const height = rect ? rect.height : region.height;
      scratch.setFromMatrixPosition(object.matrixWorld).project(camera);
      return [(scratch.x * 0.5 + 0.5) * width, (-scratch.y * 0.5 + 0.5) * height];
    },
    [],
  );

  return (
    <Html
      portal={track ? (portalRef as unknown as HtmlProps["portal"]) : undefined}
      calculatePosition={calculatePosition}
      position={position}
      center={center}
      distanceFactor={distanceFactor}
      zIndexRange={zIndexRange}
      pointerEvents="none"
      {...(threeProps as HtmlProps)}
    >
      <span {...domOnly}>{children}</span>
    </Html>
  );
}
