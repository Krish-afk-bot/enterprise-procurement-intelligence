import { useEffect, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

import { scenePalette } from "@/components/three/palette";
import { focusIsRecent, pointerIdleSeconds, readFocus, readPointer } from "@/lib/pointer";
import { watcherState } from "@/lib/worldBus";
import { useWorld } from "@/store/world";

/**
 * The Watcher.
 *
 * One character, drawn in one place, for the whole workspace. It is decorative:
 * `aria-hidden`, never required to do anything, and the reader can switch it off.
 *
 * The eye movement is deliberately kept out of React. The cursor fires hundreds
 * of events a second; they are read here, inside a frame, through the module
 * snapshot in `lib/pointer`, so the application never re-renders because a
 * character blinked.
 *
 * Motion stack, in the order the brief asks for it:
 *   window pointermove -> normalised -> smoothed target -> constrained pupils
 *   -> subtle head tilt -> subtle face parallax.
 */

const HEAD_R = 30;
/** How far a pupil may travel from the centre of its eye, in pixels. */
const PUPIL_TRAVEL = 4.1;
/**
 * How far in front of the eye's centre a pupil sits. The eye is a sphere, so a
 * pupil at the centre of it would be buried inside the white; this is the depth
 * that puts it on the surface. The frame loop moves the pupils in x and y only,
 * and has to keep this depth to do it.
 */
const PUPIL_FORWARD = 8;
/** Normalising distance: past this the gaze is fully turned toward the cursor. */
const GAZE_RANGE = 420;

interface RegionSize {
  width: number;
  height: number;
  top?: number;
  left?: number;
}

export function Watcher({
  position,
  calm,
}: {
  /** Head centre, in band-local pixels with the origin at the band's centre. */
  position: [number, number];
  /** Reduced motion or "Reduce effects": drawn, but still. */
  calm: boolean;
}) {
  const palette = scenePalette();
  const size = useThree((state) => state.size) as RegionSize;

  const root = useRef<THREE.Group>(null);
  const head = useRef<THREE.Group>(null);
  const eyeLeft = useRef<THREE.Group>(null);
  const eyeRight = useRef<THREE.Group>(null);
  const pupilLeft = useRef<THREE.Group>(null);
  const pupilRight = useRef<THREE.Group>(null);
  const browLeft = useRef<THREE.Group>(null);
  const browRight = useRef<THREE.Group>(null);
  const mouth = useRef<THREE.Mesh>(null);

  const anim = useRef({
    gazeX: 0,
    gazeY: 0,
    blink: 0,
    blinkIn: 2.4,
    blinkRunning: 0,
    saccadeIn: 3.1,
    sacX: 0,
    sacY: 0,
    sacRunning: 0,
    lastPoke: 0,
    pop: 0,
    nod: 0,
  });

  useEffect(() => {
    watcherState.visible = true;
    return () => {
      watcherState.visible = false;
    };
  }, []);

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.1);
    const t = state.clock.elapsedTime;
    const now = performance.now();
    const world = useWorld.getState();
    const a = anim.current;

    // ---------------------------------------------------------------- gaze
    let targetX = 0;
    let targetY = 0;

    if (!calm) {
      const mood = world.mood;
      if (mood === "empty") {
        // "Looks around" — a slow sweep of the room, not a tracker.
        targetX = Math.sin(t * 0.6) * 0.75;
        targetY = Math.sin(t * 0.42 + 1.1) * 0.3;
      } else if (focusIsRecent(now)) {
        // Keyboard focus wins while it is recent: the face follows the control
        // being tabbed to rather than the pointer that was left behind.
        const focus = readFocus();
        targetX = focus.x;
        targetY = focus.y;
      } else {
        const pointer = readPointer();
        if (pointer.known) {
          const regionLeft = size.left ?? 0;
          const regionTop = size.top ?? 0;
          const cx = size.width / 2 + position[0];
          const cy = size.height / 2 - position[1];
          const px = ((pointer.x + 1) / 2) * window.innerWidth - regionLeft - cx;
          const py = ((1 - pointer.y) / 2) * window.innerHeight - regionTop - cy;
          const distance = Math.hypot(px, py) || 1;
          const reach = Math.min(distance, GAZE_RANGE) / GAZE_RANGE;
          targetX = (px / distance) * reach;
          targetY = (-py / distance) * reach;
        }
      }

      if (world.mood === "loading") {
        // Eyes dart around while retrieval is running.
        targetX += Math.sin(t * 11) * 0.34;
        targetY += Math.cos(t * 8.5) * 0.12;
      }

      // Occasional saccades: small, quick, and never a new React render.
      a.saccadeIn -= dt;
      if (a.saccadeIn <= 0) {
        a.sacRunning = 0.22;
        a.sacX = (Math.random() - 0.5) * 0.5;
        a.sacY = (Math.random() - 0.5) * 0.3;
        a.saccadeIn = 2 + Math.random() * 4;
      }
      if (a.sacRunning > 0) {
        a.sacRunning -= dt;
        if (a.sacRunning <= 0) {
          a.sacX = 0;
          a.sacY = 0;
        }
      }
      targetX += a.sacX;
      targetY += a.sacY;

      // Blink every 3-7 seconds while the reader is still working.
      a.blinkIn -= dt;
      if (a.blinkIn <= 0 && a.blinkRunning <= 0) {
        a.blinkRunning = 0.26;
        a.blinkIn = 3 + Math.random() * 4;
      }
    }

    if (a.blinkRunning > 0) {
      a.blinkRunning -= dt;
      const progress = 1 - Math.max(a.blinkRunning, 0) / 0.26;
      a.blink = Math.sin(progress * Math.PI);
      if (a.blinkRunning <= 0) a.blink = 0;
    } else {
      a.blink = 0;
    }

    // After 30 seconds of stillness the eyes close; any movement opens them.
    const idle = pointerIdleSeconds(now);
    const dozy = calm ? 0 : Math.max(0, Math.min(1, (idle - 30) / 6));

    // A click blinks and pops the head before the line appears.
    if (world.poke !== a.lastPoke) {
      a.lastPoke = world.poke;
      a.pop = 1;
      if (!calm) a.blinkRunning = Math.max(a.blinkRunning, 0.22);
    }
    a.pop = Math.max(0, a.pop - dt * 3);

    const ease = 1 - Math.exp(-dt * (calm ? 60 : 7));
    a.gazeX += ((calm ? 0 : targetX) - a.gazeX) * ease;
    a.gazeY += ((calm ? 0 : targetY) - a.gazeY) * ease;

    // ----------------------------------------------------------- expression
    let lid = 1;
    let eyeScale = 1;
    let browLiftL = 0;
    let browLiftR = 0;
    let browTiltL = 0;
    let browTiltR = 0;
    let mouthWidth = 1;
    let mouthTilt = 0;
    let nod = 0;

    // Clamped: a timestamp from another clock (or the future) must only ever
    // mean "this happened just now", never a negative age that multiplies the
    // face into the far plane.
    const age = Math.max(0, now - world.moodAt) / 1000;
    switch (world.mood) {
      case "found": {
        // Eyes widen, then a small nod settles back to normal.
        const k = Math.max(0, 1 - age / 2.5);
        eyeScale = 1 + 0.16 * k;
        browLiftL = 0.4 * k;
        browLiftR = 0.4 * k;
        nod = Math.sin(Math.min(age, 1.2) * Math.PI) * 3.2 * k;
        mouthWidth = 1.1 * k + 1 - k;
        break;
      }
      case "conflict":
        // One eyebrow raised.
        browLiftL = 1;
        browTiltL = -0.32;
        browLiftR = 0.1;
        mouthWidth = 0.82;
        mouthTilt = -0.12;
        break;
      case "unsupported":
        lid = 0.46;
        browLiftL = -0.2;
        browLiftR = -0.2;
        break;
      case "error":
        browLiftL = -0.3;
        browLiftR = -0.3;
        browTiltL = 0.4;
        browTiltR = -0.4;
        lid = 0.86;
        mouthWidth = 0.7;
        break;
      case "loading":
        lid = 0.95;
        break;
      default:
        break;
    }

    const openness = Math.max(0.05, Math.min(1, lid * (1 - 0.94 * dozy)) - a.blink * 0.95);
    const pop = 1 + a.pop * 0.06;

    // ------------------------------------------------------------- transform
    if (root.current) {
      root.current.position.set(position[0], position[1], 0);
      watcherState.x = position[0];
      watcherState.y = position[1];
    }
    if (head.current) {
      head.current.rotation.z = a.gazeX * 0.055;
      head.current.position.set(a.gazeX * 1.7, a.gazeY * 1.2 + nod, 0);
      head.current.scale.setScalar(pop);
    }
    for (const eye of [eyeLeft.current, eyeRight.current]) {
      if (eye) eye.scale.set(eyeScale, Math.max(openness * eyeScale, 0.06), eyeScale);
    }
    // `z` is the distance in front of the eye's centre, not part of the gaze:
    // zeroing it here is what buries a pupil inside its own eyeball.
    const px = a.gazeX * PUPIL_TRAVEL;
    const py = a.gazeY * PUPIL_TRAVEL;
    pupilLeft.current?.position.set(px, py, PUPIL_FORWARD);
    pupilRight.current?.position.set(px, py, PUPIL_FORWARD);

    const lift = 14.5;
    if (browLeft.current) {
      browLeft.current.position.y = lift + browLiftL * 3.4;
      browLeft.current.rotation.z = browTiltL;
    }
    if (browRight.current) {
      browRight.current.position.y = lift + browLiftR * 3.4;
      browRight.current.rotation.z = browTiltR;
    }
    if (mouth.current) {
      mouth.current.scale.x = mouthWidth;
      mouth.current.rotation.z = mouthTilt;
    }
  });

  const ink = palette.foreground;

  return (
    <group ref={root}>
      <group ref={head}>
        <mesh>
          <sphereGeometry args={[HEAD_R, 26, 20]} />
          <meshStandardMaterial color={palette.paper} roughness={0.72} metalness={0} />
        </mesh>

        {/* Eye sockets give the whites an edge in both light and dark themes. */}
        <group ref={eyeLeft} position={[-11, 3, 21]}>
          <mesh>
            <sphereGeometry args={[10.4, 20, 16]} />
            <meshStandardMaterial color={ink} roughness={0.6} />
          </mesh>
          <mesh position={[0, 0, 2.2]}>
            <sphereGeometry args={[9.6, 20, 16]} />
            <meshStandardMaterial color="#f4f1ea" roughness={0.5} />
          </mesh>
          <group ref={pupilLeft} position={[0, 0, PUPIL_FORWARD]}>
            <mesh>
              <sphereGeometry args={[4.4, 16, 12]} />
              <meshStandardMaterial color={ink} roughness={0.35} />
            </mesh>
          </group>
        </group>

        <group ref={eyeRight} position={[11, 3, 21]}>
          <mesh>
            <sphereGeometry args={[10.4, 20, 16]} />
            <meshStandardMaterial color={ink} roughness={0.6} />
          </mesh>
          <mesh position={[0, 0, 2.2]}>
            <sphereGeometry args={[9.6, 20, 16]} />
            <meshStandardMaterial color="#f4f1ea" roughness={0.5} />
          </mesh>
          <group ref={pupilRight} position={[0, 0, PUPIL_FORWARD]}>
            <mesh>
              <sphereGeometry args={[4.4, 16, 12]} />
              <meshStandardMaterial color={ink} roughness={0.35} />
            </mesh>
          </group>
        </group>

        <group ref={browLeft} position={[-11.5, 14.5, 26]}>
          <mesh>
            <boxGeometry args={[15, 3.2, 3]} />
            <meshStandardMaterial color={ink} roughness={0.7} />
          </mesh>
        </group>
        <group ref={browRight} position={[11.5, 14.5, 26]}>
          <mesh>
            <boxGeometry args={[15, 3.2, 3]} />
            <meshStandardMaterial color={ink} roughness={0.7} />
          </mesh>
        </group>

        <mesh ref={mouth} position={[0, -13, 26]}>
          <boxGeometry args={[16, 3, 3]} />
          <meshStandardMaterial color={ink} roughness={0.7} />
        </mesh>

        {/* Coral cheeks: the one place the accent colour gets to be a face. */}
        <mesh position={[-19, -5, 20]} scale={[1, 0.6, 0.4]}>
          <sphereGeometry args={[6.5, 14, 10]} />
          <meshStandardMaterial color={palette.coral} roughness={0.9} transparent opacity={0.55} />
        </mesh>
        <mesh position={[19, -5, 20]} scale={[1, 0.6, 0.4]}>
          <sphereGeometry args={[6.5, 14, 10]} />
          <meshStandardMaterial color={palette.coral} roughness={0.9} transparent opacity={0.55} />
        </mesh>
      </group>

      {/* Shoulders, kept low so the character reads as peeking over the floor. */}
      <mesh position={[0, -36, -4]}>
        <boxGeometry args={[46, 20, 26]} />
        <meshStandardMaterial color={palette.primary} roughness={0.75} />
      </mesh>

      {/* A soft contact shadow instead of a shadow map: same read, no cost. */}
      <mesh position={[0, -47, -6]} scale={[58, 9, 1]}>
        <circleGeometry args={[1, 20]} />
        <meshBasicMaterial color={ink} transparent opacity={0.1} />
      </mesh>
    </group>
  );
}
