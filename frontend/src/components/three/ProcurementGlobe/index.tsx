import { useRef, useMemo, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface ProcurementGlobeProps {
  /** Scroll progress (0-1) controls rotation and scale */
  scrollProgress?: number;
}

/**
 * Procurement Globe - Instanced dot-matrix sphere.
 *
 * Features:
 * - Thousands of instanced dots forming a sphere
 * - Land regions more visible than oceans
 * - Fresnel rim glow (orange/amber)
 * - Continuous rotation
 * - Scroll-linked scale and rotation
 * - Performance optimized with InstancedMesh
 */
export function ProcurementGlobe({ scrollProgress = 0 }: ProcurementGlobeProps) {
  const groupRef = useRef<THREE.Group>(null);
  const instancedMeshRef = useRef<THREE.InstancedMesh>(null);

  // Generate globe dots (fibonacci sphere distribution)
  const { positions, isLand } = useMemo(() => {
    const numPoints = 12000; // Adjust for performance
    const positions: THREE.Vector3[] = [];
    const isLand: boolean[] = [];

    const phi = Math.PI * (3 - Math.sqrt(5)); // Golden angle

    for (let i = 0; i < numPoints; i++) {
      const y = 1 - (i / (numPoints - 1)) * 2; // Range: 1 to -1
      const radius = Math.sqrt(1 - y * y);
      const theta = phi * i;

      const x = Math.cos(theta) * radius;
      const z = Math.sin(theta) * radius;

      positions.push(new THREE.Vector3(x, y, z));

      // Simple land mask: latitude-based approximation
      // Real implementation would use equirectangular texture sampling
      const lat = Math.asin(y) * (180 / Math.PI);
      const lon = Math.atan2(z, x) * (180 / Math.PI);

      // Simplified land regions (very approximate)
      const landCheck =
        (lat > -60 && lat < 70 && ((lon > -30 && lon < 60) || (lon > -140 && lon < -50))) || // Eurasia, Americas
        (lat > -40 && lat < 30 && lon > 90 && lon < 180); // Asia-Pacific

      isLand.push(landCheck);
    }

    return { positions, isLand };
  }, []);

  // Initialize instanced mesh
  useEffect(() => {
    const mesh = instancedMeshRef.current;
    if (!mesh) return;

    const matrix = new THREE.Matrix4();
    const scale = new THREE.Vector3();

    positions.forEach((pos, i) => {
      // Land dots are slightly larger
      const size = isLand[i] ? 1 : 0.5;
      scale.set(size, size, size);

      matrix.compose(pos, new THREE.Quaternion(), scale);
      mesh.setMatrixAt(i, matrix);
    });

    mesh.instanceMatrix.needsUpdate = true;
  }, [positions, isLand]);

  // Continuous rotation + scroll-linked transform
  useFrame(() => {
    if (!groupRef.current) return;

    // Base rotation
    groupRef.current.rotation.y += 0.001;

    // Scroll-linked effects
    const progress = scrollProgress;

    // Scale: starts at 0.6, grows to 1.2
    const targetScale = 0.6 + progress * 0.6;
    groupRef.current.scale.setScalar(targetScale);

    // Y position: rises from -1 to 0
    groupRef.current.position.y = -1 + progress;

    // Additional rotation from scroll
    groupRef.current.rotation.y += progress * 0.002;
  });

  return (
    <group ref={groupRef}>
      {/* Instanced dots */}
      <instancedMesh ref={instancedMeshRef} args={[undefined, undefined, positions.length]}>
        <sphereGeometry args={[0.008, 8, 8]} />
        <meshBasicMaterial color="#FB923C" opacity={0.8} transparent />
      </instancedMesh>

      {/* Fresnel rim glow */}
      <mesh>
        <sphereGeometry args={[1.02, 64, 64]} />
        <shaderMaterial
          transparent
          side={THREE.BackSide}
          uniforms={{
            glowColor: { value: new THREE.Color("#FB923C") },
            intensity: { value: 0.6 },
          }}
          vertexShader={`
            varying vec3 vNormal;
            void main() {
              vNormal = normalize(normalMatrix * normal);
              gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
          `}
          fragmentShader={`
            uniform vec3 glowColor;
            uniform float intensity;
            varying vec3 vNormal;

            void main() {
              float fresnel = pow(1.0 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.5);
              gl_FragColor = vec4(glowColor, fresnel * intensity);
            }
          `}
        />
      </mesh>

      {/* Soft halo */}
      <mesh>
        <sphereGeometry args={[1.15, 64, 64]} />
        <meshBasicMaterial color="#FB923C" opacity={0.1} transparent side={THREE.BackSide} />
      </mesh>
    </group>
  );
}
