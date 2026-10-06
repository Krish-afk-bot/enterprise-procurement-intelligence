import { useEffect, useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

import { SceneLabel } from "@/components/world/SceneLabel";
import { scenePalette } from "@/components/three/palette";
import { courierState, pokeCourier } from "@/lib/worldBus";

/**
 * The Courier.
 *
 * A low-poly figure walking the floor of the band with a suitcase. The suitcase
 * carries one word, and the word is always a real collection in this workspace —
 * Suppliers, Contracts, Documents, Prices or Evidence. It never carries a number,
 * a deadline or a promise, because it has none.
 *
 * Interactions, all of them optional for the reader:
 *   - a click anywhere in the band near the courier stops it and tips its hat;
 *   - a cursor passing close makes it stumble;
 *   - reduced motion or "Reduce effects" leaves it standing still.
 */

/** One way across the band, in seconds: inside the brief's 20-40 second loop. */
const WALK_SECONDS = 28;
const PAUSE_SECONDS = 2.4;

interface RegionSize {
  width: number;
  height: number;
}

export function Courier({ calm, label }: { calm: boolean; label: string }) {
  const palette = scenePalette();
  const size = useThree((state) => state.size) as RegionSize;

  const root = useRef<THREE.Group>(null);
  const legLeft = useRef<THREE.Group>(null);
  const legRight = useRef<THREE.Group>(null);
  const armLeft = useRef<THREE.Group>(null);
  const armRight = useRef<THREE.Group>(null);
  const body = useRef<THREE.Group>(null);
  const hat = useRef<THREE.Group>(null);
  const suitcase = useRef<THREE.Group>(null);

  const walk = useRef({
    x: 0,
    dir: 1 as 1 | -1,
    pause: 1.2,
    phase: 0,
    hatProgress: 0,
    stumble: 0,
    lastPoke: 0,
    started: false,
  });

  // The suitcase tag is real DOM text: crisp at any size, readable by a screen
  // reader's visual equivalent, and it travels with the courier because it is
  // projected from the same world position every frame.
  const tagStyle = useMemo(
    () => ({
      transform: "translate(-50%, -140%)",
      whiteSpace: "nowrap",
    }),
    [],
  );

  useEffect(() => {
    courierState.visible = true;
    return () => {
      courierState.visible = false;
    };
  }, []);

  useFrame((_state, delta) => {
    const dt = Math.min(delta, 0.1);
    const w = walk.current;
    const halfSpan = Math.max(size.width / 2 - 46, 80);
    if (!w.started) {
      w.started = true;
      w.x = -halfSpan;
    }

    if (courierState.poke !== w.lastPoke) {
      w.lastPoke = courierState.poke;
      w.hatProgress = 1;
      w.pause = 1.8;
    }

    const stumbled = performance.now() < courierState.stumbleUntil;
    w.stumble += ((stumbled ? 1 : 0) - w.stumble) * Math.min(1, dt * 9);
    w.hatProgress = Math.max(0, w.hatProgress - dt * 1.4);

    if (!calm) {
      if (w.pause > 0) {
        w.pause -= dt;
      } else {
        const speed = (halfSpan * 2 - 90) / WALK_SECONDS;
        w.x += w.dir * speed * dt;
        w.phase += dt * 5.6;
        // Turn only at the far end of the direction being walked. The courier
        // starts at the left edge, inside the left margin, so testing both
        // bounds regardless of direction reversed it on its very first step and
        // re-paused for another 2.4s: it advanced one frame per pause and never
        // crossed the band at all. The bound it is walking away from is not a
        // wall.
        if (w.dir === 1 ? w.x > halfSpan - 45 : w.x < -halfSpan + 45) {
          w.dir = w.dir === 1 ? -1 : 1;
          w.pause = PAUSE_SECONDS;
        }
      }
    }

    const stride = w.pause > 0 || calm ? 0 : 1;
    const swing = Math.sin(w.phase) * 0.55 * stride;
    const bob = Math.abs(Math.sin(w.phase)) * 1.6 * stride;

    if (root.current) {
      root.current.position.set(w.x, -size.height / 2 + 4 + bob + w.stumble * 3, 0);
      root.current.rotation.y = w.dir === 1 ? 0 : Math.PI;
      root.current.rotation.z = w.dir === 1 ? -w.stumble * 0.16 : w.stumble * 0.16;
      courierState.x = w.x;
      courierState.halfWidth = 30;
    }
    if (legLeft.current) legLeft.current.rotation.z = swing;
    if (legRight.current) legRight.current.rotation.z = -swing;
    if (armLeft.current) armLeft.current.rotation.z = -swing * 0.6;
    if (armRight.current) armRight.current.rotation.z = swing * 0.4;
    if (body.current) body.current.position.y = bob;
    if (suitcase.current) suitcase.current.rotation.z = swing * 0.12;
    if (hat.current) {
      // The hat's pieces already sit at head height inside the hat group, so the
      // group itself stays at the origin: lifting it here is what would leave the
      // hat hanging in the air above the courier.
      const tip = Math.sin(Math.min(1 - w.hatProgress, 1) * Math.PI) * 0.85;
      hat.current.rotation.x = -tip;
      hat.current.position.y = tip * 4;
    }
  });

  const ink = palette.foreground;

  return (
    <group ref={root} onClick={() => pokeCourier()}>
      {/* Contact shadow: a soft blob rather than a shadow map. */}
      <mesh position={[0, 0.6, -8]} scale={[30, 6, 1]}>
        <circleGeometry args={[1, 18]} />
        <meshBasicMaterial color={ink} transparent opacity={0.12} />
      </mesh>

      <group ref={legLeft} position={[-4.5, 14, 0]}>
        <mesh position={[0, -7, 0]}>
          <boxGeometry args={[5.5, 14, 5.5]} />
          <meshStandardMaterial color={palette.foreground} roughness={0.8} />
        </mesh>
      </group>
      <group ref={legRight} position={[4.5, 14, 0]}>
        <mesh position={[0, -7, 0]}>
          <boxGeometry args={[5.5, 14, 5.5]} />
          <meshStandardMaterial color={palette.foreground} roughness={0.8} />
        </mesh>
      </group>

      <group ref={body}>
        <mesh position={[0, 21.5, 0]}>
          <boxGeometry args={[18, 15, 13]} />
          <meshStandardMaterial color={palette.primary} roughness={0.7} />
        </mesh>

        <group ref={armLeft} position={[-10.5, 26, 0]}>
          <mesh position={[0, -6, 0]}>
            <boxGeometry args={[4.5, 12, 4.5]} />
            <meshStandardMaterial color={palette.primary} roughness={0.7} />
          </mesh>
        </group>

        <group ref={armRight} position={[10.5, 26, 0]}>
          <mesh position={[0, -6, 1]}>
            <boxGeometry args={[4.5, 12, 4.5]} />
            <meshStandardMaterial color={palette.primary} roughness={0.7} />
          </mesh>
        </group>

        <mesh position={[0, 37, 0]}>
          <sphereGeometry args={[7.5, 18, 14]} />
          <meshStandardMaterial color={palette.paper} roughness={0.7} />
        </mesh>
        <mesh position={[2.6, 37.6, 6.4]} scale={[1, 1, 0.7]}>
          <sphereGeometry args={[1.7, 10, 8]} />
          <meshStandardMaterial color={ink} roughness={0.5} />
        </mesh>

        <group ref={hat}>
          <mesh position={[0, 42.4, 0]}>
            <cylinderGeometry args={[10.5, 10.5, 1.6, 18]} />
            <meshStandardMaterial color={palette.warm} roughness={0.75} />
          </mesh>
          <mesh position={[0, 45, 0]}>
            <cylinderGeometry args={[7.2, 7.6, 5, 18]} />
            <meshStandardMaterial color={palette.warm} roughness={0.75} />
          </mesh>
        </group>

        <group ref={suitcase} position={[13, 12, 2]}>
          <mesh position={[0, -7, 0]}>
            <boxGeometry args={[19, 15, 7]} />
            <meshStandardMaterial color={palette.warm} roughness={0.7} />
          </mesh>
          <mesh position={[0, 1.5, 0]}>
            <boxGeometry args={[7, 2.5, 2.5]} />
            <meshStandardMaterial color={ink} roughness={0.6} />
          </mesh>
          <mesh position={[0, -7, 3.7]}>
            <boxGeometry args={[16.5, 0.9, 0.6]} />
            <meshStandardMaterial color={ink} roughness={0.6} />
          </mesh>
        </group>
      </group>

      {/* The one piece of text in the world: a real destination, as DOM text. */}
      <SceneLabel position={[13, -2, 6]} style={tagStyle} aria-hidden="true">
        <span className="rounded border border-foreground/25 bg-background/95 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-foreground">
          {label}
        </span>
      </SceneLabel>
    </group>
  );
}
