import { useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import * as THREE from "three";

import { scenePalette } from "@/components/three/palette";
import { SceneLabel } from "@/components/world/SceneLabel";
import { SceneFrame } from "@/components/three/SceneFrame";
import type { EcosystemModel, EcosystemNode, EcosystemTier } from "@/lib/ecosystem";
import { titleCase } from "@/lib/utils";

/**
 * Columns, left to right, are the procurement chain as the records express it.
 * The order is data, not decoration: a supplier is drawn before its contract, a
 * price before the document that states it.
 */
const TIER_X: Record<EcosystemTier, number> = {
  supplier: -6.4,
  contract: -3.2,
  product: 0,
  price: 3.2,
  evidence: 6.4,
  compliance: -6.4,
  amendment: -3.2,
};

const TIER_RADIUS: Record<EcosystemTier, number> = {
  supplier: 0.34,
  contract: 0.26,
  product: 0.22,
  price: 0.2,
  evidence: 0.16,
  compliance: 0.17,
  amendment: 0.15,
};

/** Positions are a function of the data: same records, same layout, every time. */
function spread(nodes: EcosystemNode[]): Map<string, [number, number, number]> {
  const positions = new Map<string, [number, number, number]>();
  const byTier = new Map<EcosystemTier, EcosystemNode[]>();
  for (const node of nodes) {
    const list = byTier.get(node.tier) ?? [];
    list.push(node);
    byTier.set(node.tier, list);
  }
  const tallest = Math.max(...[...byTier.values()].map((list) => list.length), 1);
  const gap = Math.min(7.6 / Math.max(tallest - 1, 1), 1.5);

  for (const [tier, list] of byTier) {
    // A tier that overflows the vertical band continues in a second column
    // beside the first, so a large price list never becomes a wall of spheres.
    const perColumn = Math.max(Math.ceil(list.length / 2), Math.min(list.length, Math.floor(7.6 / gap) + 1));
    list.forEach((node, index) => {
      const column = Math.floor(index / perColumn);
      const row = index % perColumn;
      const count = Math.min(perColumn, list.length - column * perColumn);
      const y = (row - (count - 1) / 2) * gap;
      const x = TIER_X[tier] + column * 0.72;
      const z = (index % 3) * 0.34 - 0.34;
      positions.set(node.id, [x, y, z]);
    });
  }
  return positions;
}

/** Thin, slightly transparent line from one record to the next. */
function Link({
  from,
  to,
  colour,
  opacity,
}: {
  from: [number, number, number];
  to: [number, number, number];
  colour: string;
  opacity: number;
}) {
  const geometry = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(...from),
      new THREE.Vector3((from[0] + to[0]) / 2, (from[1] + to[1]) / 2 + 0.12, (from[2] + to[2]) / 2),
      new THREE.Vector3(...to),
    ]);
    return new THREE.TubeGeometry(curve, 10, 0.006, 4, false);
  }, [from, to]);
  return (
    <mesh geometry={geometry} frustumCulled={false}>
      <meshBasicMaterial color={colour} transparent opacity={opacity} depthWrite={false} />
    </mesh>
  );
}

/**
 * A single stored record. Hovering highlights it and its immediate neighbours
 * and shows what the record is; selecting it opens its own page. A record
 * without a page says so rather than pretending to be clickable.
 */
function Node({
  node,
  position,
  neighbours,
  hovered,
  onHover,
  tierColour,
}: {
  node: EcosystemNode;
  position: [number, number, number];
  neighbours: string[];
  hovered: string | null;
  onHover: (id: string | null) => void;
  tierColour: string;
}) {
  const navigate = useNavigate();
  const mesh = useRef<THREE.Mesh>(null);
  const [local, setLocal] = useState(false);
  const active = hovered === node.id;
  const connected = hovered !== null && neighbours.includes(hovered);
  const dimmed = hovered !== null && !active && !connected;
  const radius = TIER_RADIUS[node.tier] * (active ? 1.35 : connected ? 1.15 : 1);

  // A very slow vertical drift: the scene breathes without demanding attention.
  useFrame(({ clock }) => {
    if (!mesh.current) return;
    const phase = (node.id.length % 7) * 0.9;
    mesh.current.position.y = Math.sin(clock.elapsedTime * 0.35 + phase) * 0.045;
  });

  return (
    <group position={position}>
      <mesh
        ref={mesh}
        onClick={
          node.href
            ? (event: ThreeEvent<MouseEvent>) => {
                event.stopPropagation();
                navigate(node.href!);
              }
            : undefined
        }
        onPointerOver={(event: ThreeEvent<PointerEvent>) => {
          event.stopPropagation();
          setLocal(true);
          onHover(node.id);
          if (node.href) document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setLocal(false);
          onHover(null);
          document.body.style.cursor = "";
        }}
      >
        <sphereGeometry args={[radius, 20, 14]} />
        <meshStandardMaterial color={tierColour} roughness={0.42} metalness={0.06} transparent opacity={dimmed ? 0.32 : 1} />
      </mesh>
      {active || local ? (
        <SceneLabel center distanceFactor={12} position={[0, radius + 0.34, 0]} zIndexRange={[20, 0]}>
          <span className="pointer-events-none block w-56 rounded-md border bg-background/95 px-2 py-1.5 text-left">
            <span className="block truncate text-[11px] font-semibold">{node.label}</span>
            <span className="block text-[10px] leading-snug text-muted-foreground">{node.detail}</span>
            <span className="mt-0.5 block text-[10px] font-medium text-primary">
              {node.href ? "Open this record" : "No page of its own in the workspace"}
            </span>
          </span>
        </SceneLabel>
      ) : null}
    </group>
  );
}

/**
 * The overview band: what the workspace holds, arranged as the chain the records
 * themselves describe. Every node is a stored row and every link is a
 * relationship the backend reports, so the scene cannot show a supplier, a
 * contract or a price that does not exist.
 */
export default function EcosystemScene({
  model,
  fallback,
  legend,
}: {
  model: EcosystemModel;
  fallback: ReactNode;
  legend?: ReactNode;
}) {
  return (
    <SceneFrame
      title="Procurement ecosystem"
      caption="Every node is a stored record and every line is a relationship the workspace reports. Hover for what the record is; select it to open it. The same records are listed below the scene."
      ariaLabel={`Procurement ecosystem drawn from the stored records: ${model.totals
        .map((tier) => `${tier.shown} of ${tier.count} ${tier.label} record(s) shown`)
        .join(", ")}. The text version below lists the same records.`}
      fallback={fallback}
      legend={legend}
      height={360}
      cameraPosition={[0, 2.2, 11.4]}
      maxDistance={20}
      autoRotateSpeed={0.22}
    >
      <EcosystemSceneInner model={model} />
    </SceneFrame>
  );
}

function EcosystemSceneInner({ model }: { model: EcosystemModel }) {
  const palette = scenePalette();
  const [hovered, setHovered] = useState<string | null>(null);

  const positions = useMemo(() => spread(model.nodes), [model.nodes]);

  const neighbours = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const link of model.links) {
      map.set(link.from, [...(map.get(link.from) ?? []), link.to]);
      map.set(link.to, [...(map.get(link.to) ?? []), link.from]);
    }
    return map;
  }, [model.links]);

  const colour = (tier: EcosystemTier) => {
    switch (tier) {
      case "supplier":
        return palette.primary;
      case "contract":
        return palette.foreground;
      case "product":
        return palette.info;
      case "price":
        return palette.warning;
      case "evidence":
        return palette.muted;
      case "compliance":
        return palette.success;
      case "amendment":
        return palette.border;
    }
  };

  return (
    <>
      {model.links.map((link) => {
        const from = positions.get(link.from);
        const to = positions.get(link.to);
        if (!from || !to) return null;
        const lit = hovered !== null && (link.from === hovered || link.to === hovered);
        return (
          <Link
            key={`${link.from}->${link.to}`}
            from={from}
            to={to}
            colour={lit ? palette.primary : palette.border}
            opacity={lit ? 0.95 : 0.4}
          />
        );
      })}

      {model.nodes.map((node) => {
        const position = positions.get(node.id);
        if (!position) return null;
        return (
          <Node
            key={node.id}
            node={node}
            position={position}
            neighbours={neighbours.get(node.id) ?? []}
            hovered={hovered}
            onHover={setHovered}
            tierColour={colour(node.tier)}
          />
        );
      })}

      {/* Tier captions: what each column means, so the scene reads as a chain
          rather than an abstract cloud. */}
      {(["supplier", "contract", "product", "price", "evidence"] as EcosystemTier[]).map((tier) => (
        <SceneLabel key={tier} center distanceFactor={13} position={[TIER_X[tier], -4.6, 0]}>
          <span className="pointer-events-none whitespace-nowrap text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            {titleCase(tier)}
          </span>
        </SceneLabel>
      ))}
    </>
  );
}
