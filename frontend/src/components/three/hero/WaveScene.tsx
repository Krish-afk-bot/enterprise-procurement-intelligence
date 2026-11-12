import { useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

/**
 * The landing page's 3D field: an abstract, monochrome landscape of slow
 * contours. It is decoration for the product idea (layers of records settling
 * into one evidence surface), never a data visualisation, so it draws no
 * figures and carries no labels.
 *
 * Engineering rules, enforced here rather than by the caller:
 * - Nothing loads until the hero is on screen (the caller imports this lazily).
 * - Geometry detail drops on small screens and on low-end GPUs.
 * - Reduced motion paints a single frame and stops: no animation loop.
 * - The shader writes only to `gl_FragColor` with a cheap value-noise fBm, so a
 *   mid-range laptop GPU is never the bottleneck.
 * - A WebGL failure is caught by the caller, which renders the CSS fallback.
 */

const vertexShader = /* glsl */ `
  uniform float uTime;
  uniform float uAmplitude;
  varying float vElevation;
  varying vec3 vLocal;

  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
  }

  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
      mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
      u.y
    );
  }

  float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    for (int i = 0; i < 4; i++) {
      value += amplitude * noise(p);
      p *= 2.03;
      amplitude *= 0.5;
    }
    return value;
  }

  void main() {
    vec3 pos = position;
    float t = uTime * 0.055;
    vec2 q = pos.xy;

    // Two layers moving at different speeds: a slow swell and a finer ripple.
    float swell = fbm(vec2(q.x * 0.085 + t * 0.7, q.y * 0.12 - t));
    float ripple = fbm(vec2(q.x * 0.19 - t * 0.55, q.y * 0.24 + t * 0.4));

    // Concentrate the height toward the middle so the horizon stays calm.
    float centre = smoothstep(34.0, 4.0, length(q * vec2(0.9, 1.35)));
    float elevation = (swell * 0.72 + ripple * 0.34 - 0.42) * uAmplitude * (0.45 + centre * 0.9);

    pos.z = elevation;
    vElevation = elevation;
    vLocal = pos;

    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`;

const fragmentShader = /* glsl */ `
  uniform float uTime;
  varying float vElevation;
  varying vec3 vLocal;

  void main() {
    // A woven contour grid across the displaced surface.
    vec2 cell = abs(fract(vLocal.xy * 0.32) - 0.5);
    float grid = smoothstep(0.46, 0.5, max(cell.x, cell.y));

    // Elevation bands: the crests catch the light.
    float band = abs(fract(vElevation * 1.35) - 0.5);
    float contour = smoothstep(0.10, 0.0, band);

    // Light from above, stronger on the crests.
    float crest = smoothstep(-0.6, 0.9, vElevation);

    float fade = smoothstep(1.0, 0.15, length(vLocal.xy * vec2(0.028, 0.045)));
    float horizon = smoothstep(46.0, 12.0, length(vLocal.xy));

    float intensity = (grid * 0.5 + contour * 0.35 + crest * 0.22) * fade * horizon;

    // A faint moving sheen so the surface reads as fluid rather than as wire.
    float sheen = 0.5 + 0.5 * sin(vLocal.x * 0.12 + uTime * 0.22 + vLocal.y * 0.08);
    intensity += sheen * 0.035 * fade * crest;

    vec3 colour = mix(vec3(0.55), vec3(1.0), clamp(crest, 0.0, 1.0));
    gl_FragColor = vec4(colour, clamp(intensity, 0.0, 1.0));
  }
`;

/** Sparse dust that drifts at two different speeds, giving depth to the field. */
function Particles({ count, animate }: { count: number; animate: boolean }) {
  const ref = useRef<THREE.Points>(null);

  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      positions[index * 3] = (Math.random() - 0.5) * 46;
      positions[index * 3 + 1] = (Math.random() - 0.5) * 18;
      positions[index * 3 + 2] = (Math.random() - 0.5) * 22;
    }
    const buffer = new THREE.BufferGeometry();
    buffer.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return buffer;
  }, [count]);

  useFrame((_, delta) => {
    if (!animate || !ref.current) return;
    // Slow upward drift with wrap-around; no per-frame allocation.
    ref.current.rotation.y += delta * 0.012;
    const position = ref.current.geometry.getAttribute("position") as THREE.BufferAttribute;
    const array = position.array as Float32Array;
    for (let index = 1; index < array.length; index += 3) {
      array[index] += delta * 0.16;
      if (array[index] > 9) array[index] = -9;
    }
    position.needsUpdate = true;
  });

  return (
    <points ref={ref} geometry={geometry} frustumCulled={false}>
      <pointsMaterial
        color="#ffffff"
        size={0.035}
        sizeAttenuation
        transparent
        opacity={0.42}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

function WaveField({ animate, detail }: { animate: boolean; detail: boolean }) {
  const material = useRef<THREE.ShaderMaterial>(null);
  const { camera } = useThree();

  const uniforms = useMemo(
    () => ({
      uTime: { value: 12 },
      uAmplitude: { value: 1.9 },
    }),
    [],
  );

  const geometry = useMemo(() => {
    const segments = detail ? 190 : 90;
    const plane = new THREE.PlaneGeometry(64, 40, segments, Math.round(segments * 0.62));
    return plane;
  }, [detail]);

  useFrame(({ clock }) => {
    if (material.current) {
      material.current.uniforms.uTime.value = animate ? clock.elapsedTime : 12;
    }
    if (!animate) return;
    // A slow, bounded camera drift: the surface moves, the horizon does not.
    const t = clock.elapsedTime;
    camera.position.x = Math.sin(t * 0.05) * 1.1;
    camera.position.y = 3.1 + Math.sin(t * 0.037) * 0.22;
    camera.position.z = 8.4 + Math.cos(t * 0.043) * 0.35;
    camera.lookAt(0, -0.4, 0);
  });

  return (
    <mesh geometry={geometry} rotation={[-Math.PI / 2.32, 0, 0]} position={[0, -2.5, 0]}>
      <shaderMaterial
        ref={material}
        uniforms={uniforms}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        transparent
        depthWrite={false}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

export default function WaveScene({ animate = true, detail = true }: { animate?: boolean; detail?: boolean }) {
  return (
    <Canvas
      className="!absolute inset-0"
      dpr={detail ? [1, 1.6] : [1, 1.15]}
      gl={{ antialias: detail, powerPreference: "low-power", alpha: true }}
      camera={{ position: [0, 3.1, 8.4], fov: 52, near: 0.1, far: 90 }}
      frameloop={animate ? "always" : "demand"}
      onCreated={({ gl, scene }) => {
        gl.setClearColor(new THREE.Color("#050505"), 0);
        scene.fog = new THREE.Fog("#050505", 12, 42);
      }}
    >
      <WaveField animate={animate} detail={detail} />
      <Particles count={detail ? 320 : 120} animate={animate} />
    </Canvas>
  );
}
