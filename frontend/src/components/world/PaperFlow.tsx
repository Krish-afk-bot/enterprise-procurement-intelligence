import { useEffect, useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

import { scenePalette } from "@/components/three/palette";
import { readPointer } from "@/lib/pointer";

/**
 * The paper flow.
 *
 * Translucent sheets travelling the chain the records themselves describe:
 * Supplier → Contract → Product → Price → Evidence. Five lanes, one per step,
 * drawn with a single instanced mesh so a hundred sheets still cost one draw
 * call.
 *
 * Two rules hold here:
 *   - no sheet carries a number, a name or a promise. They are paper, not data.
 *     A sheet only ever gets a caption if a real API entity supplied it, which
 *     is why this component does not caption anything itself.
 *   - the cursor bends the lanes a little; it never drives a second render loop.
 *     In calm mode the sheets are placed once and stay put.
 */

/** One lane per step of the chain, in order. */
const LANES = 5;
/** Hard ceiling on instances; the tier decides how many are actually drawn. */
const MAX_SHEETS = 26;
const TINTS = ["primary", "success", "warning", "info", "muted"] as const;

export function PaperFlow({ calm, count }: { calm: boolean; count: number }) {
  const palette = scenePalette();
  const size = useThree((state) => state.size);
  const mesh = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const point = useMemo(() => new THREE.Vector3(), []);

  const lanes = useMemo(() => {
    const width = Math.max(size.width, 320);
    const height = Math.max(size.height, 56);
    const span = Math.min(height / (LANES + 1), 22);
    return Array.from({ length: LANES }, (_unused, lane) => {
      const y = (lane - (LANES - 1) / 2) * span;
      return new THREE.CatmullRomCurve3([
        new THREE.Vector3(-width * 0.48, y + 9, -7),
        new THREE.Vector3(-width * 0.22, y - 7, -3),
        new THREE.Vector3(0, y + 6, 1),
        new THREE.Vector3(width * 0.24, y - 6, -3),
        new THREE.Vector3(width * 0.48, y + 8, -7),
      ]);
    });
  }, [size.width, size.height]);

  // One colour per lane, written once: the chain reads left to right without
  // introducing a colour that is not already a token.
  useEffect(() => {
    const instanced = mesh.current;
    if (!instanced) return;
    const colour = new THREE.Color();
    for (let i = 0; i < MAX_SHEETS; i += 1) {
      colour.set(palette[TINTS[i % LANES]]);
      instanced.setColorAt(i, colour);
    }
    if (instanced.instanceColor) instanced.instanceColor.needsUpdate = true;
  }, [palette]);

  useFrame((state) => {
    const instanced = mesh.current;
    if (!instanced) return;
    const drawn = Math.min(Math.max(count, 0), MAX_SHEETS);
    instanced.count = drawn;
    if (drawn === 0) return;

    const pointer = readPointer();
    const live = !calm && pointer.known;
    const px = live ? pointer.x : 0;
    const py = live ? pointer.y : 0;
    const time = state.clock.elapsedTime;

    for (let i = 0; i < drawn; i += 1) {
      const lane = i % LANES;
      const progress = calm
        ? 0.12 + ((i / Math.max(drawn - 1, 1)) * 0.76)
        : ((time * 0.052 + i / drawn) % 1 + 1) % 1;
      lanes[lane].getPointAt(progress, point);
      dummy.position.set(point.x + px * 15, point.y + py * 9, point.z);
      dummy.rotation.set(
        py * 0.22,
        px * 0.3,
        calm ? (lane - 2) * 0.1 : (lane - 2) * 0.1 + Math.sin(time * 1.2 + i * 1.7) * 0.17,
      );
      const scale = 0.84 + ((i * 7) % 5) * 0.06;
      dummy.scale.set(scale, scale, scale);
      dummy.updateMatrix();
      instanced.setMatrixAt(i, dummy.matrix);
    }
    instanced.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, MAX_SHEETS]} frustumCulled={false}>
      <planeGeometry args={[12, 15]} />
      <meshBasicMaterial
        color={palette.paper}
        transparent
        opacity={0.46}
        depthWrite={false}
        side={THREE.DoubleSide}
      />
    </instancedMesh>
  );
}
