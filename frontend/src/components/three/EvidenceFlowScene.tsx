import { Html } from "@react-three/drei";

import { scenePalette } from "@/components/three/palette";

/** Document families that actually exist in a procurement corpus. */
const DOCUMENTS = ["Master contract", "Amendment", "Pricing schedule"];

const DOC_POSITIONS: [number, number, number][] = [
  [-2.15, 0.85, -0.55],
  [-2.35, 0.05, 0.35],
  [-2.05, -0.8, -0.15],
];

const EVIDENCE: [number, number, number] = [0.35, 0, 0];
const ANSWER: [number, number, number] = [2.35, 0, 0];

function Connector({ from, to, colour }: { from: [number, number, number]; to: [number, number, number]; colour: string }) {
  return (
    <lineSegments frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          array={new Float32Array([...from, ...to])}
          count={2}
          itemSize={3}
        />
      </bufferGeometry>
      <lineBasicMaterial color={colour} transparent opacity={0.9} />
    </lineSegments>
  );
}

function Caption({
  text,
  position,
  emphasis = false,
}: {
  text: string;
  position: [number, number, number];
  emphasis?: boolean;
}) {
  return (
    <Html center distanceFactor={10} position={position}>
      <span
        className={
          emphasis
            ? "pointer-events-none whitespace-nowrap rounded border border-primary/40 bg-background/95 px-1.5 py-0.5 text-[10px] font-semibold text-primary"
            : "pointer-events-none whitespace-nowrap rounded border border-border bg-background/95 px-1.5 py-0.5 text-[10px] font-semibold"
        }
      >
        {text}
      </span>
    </Html>
  );
}

/**
 * A schematic of what the product does, drawn from its own vocabulary:
 * separate documents are retrieved, one passage is quoted, and the answer is
 * composed from that passage. It shows no figures, because a schematic must
 * never look like data.
 */
export function EvidenceFlowScene() {
  const palette = scenePalette();

  return (
    <>
      {DOC_POSITIONS.map((position, index) => (
        <group key={DOCUMENTS[index]} position={position}>
          <mesh>
            <boxGeometry args={[1.05, 0.035, 0.72]} />
            <meshStandardMaterial color={palette.muted} roughness={0.6} metalness={0.02} />
          </mesh>
          <mesh position={[0, 0.03, 0]}>
            <boxGeometry args={[1.05, 0.012, 0.06]} />
            <meshStandardMaterial color={palette.border} roughness={0.6} />
          </mesh>
          <Html center distanceFactor={10} position={[0, 0.42, 0]}>
            <span className="pointer-events-none whitespace-nowrap text-[10px] text-muted-foreground">
              {DOCUMENTS[index]}
            </span>
          </Html>
        </group>
      ))}

      {DOC_POSITIONS.map((position, index) => (
        <Connector key={`connector-${index}`} from={position} to={EVIDENCE} colour={palette.border} />
      ))}

      <group position={EVIDENCE}>
        <mesh>
          <boxGeometry args={[0.94, 0.05, 0.66]} />
          <meshStandardMaterial color={palette.primary} roughness={0.35} metalness={0.1} />
        </mesh>
        <Caption text="Cited passage" position={[0, 0.46, 0]} emphasis />
      </group>

      <Connector from={EVIDENCE} to={ANSWER} colour={palette.border} />

      <group position={ANSWER}>
        <mesh>
          <boxGeometry args={[1.15, 0.06, 0.8]} />
          <meshStandardMaterial color={palette.foreground} roughness={0.4} metalness={0.08} />
        </mesh>
        <Caption text="Answer" position={[0, 0.5, 0]} />
      </group>
    </>
  );
}
