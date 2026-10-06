import { useMemo, useRef, useState } from "react";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import * as THREE from "three";

import { labelColour, scenePalette } from "@/components/three/palette";
import { SceneLabel } from "@/components/world/SceneLabel";

export interface SceneGraphNode {
  label: string;
  key: string;
  name?: string;
}

export interface SceneGraphEdge {
  type: string;
  start: { label: string; key: string };
  end: { label: string; key: string };
}

const NODE_ID = (node: { label: string; key: string }) => `${node.label}:${node.key}`;

/** Readable size per record type: a supplier is a bigger fact than a price row. */
const RADIUS: Record<string, number> = {
  Supplier: 0.19,
  Contract: 0.15,
  Amendment: 0.15,
  Product: 0.13,
  ComplianceCertificate: 0.12,
  Document: 0.105,
  Price: 0.095,
};

export function areaRadius(label: string): number {
  return RADIUS[label] ?? 0.12;
}

/**
 * Positions are derived from the data, never random: records of the same type
 * sit in the same sector of the ring around the selected record, ordered by
 * name, so the same supplier always appears in the same place.
 */
function layout(root: SceneGraphNode, nodes: SceneGraphNode[]) {
  const positions = new Map<string, [number, number, number]>();
  positions.set(NODE_ID(root), [0, 0, 0]);

  const groups = new Map<string, SceneGraphNode[]>();
  for (const node of nodes) {
    if (NODE_ID(node) === NODE_ID(root)) continue;
    const list = groups.get(node.label) ?? [];
    list.push(node);
    groups.set(node.label, list);
  }

  const labels = [...groups.keys()].sort();
  labels.forEach((label, groupIndex) => {
    const members = (groups.get(label) ?? []).sort((a, b) => (a.name ?? a.key).localeCompare(b.name ?? b.key));
    const sector = (Math.PI * 2) / Math.max(labels.length, 1);
    const start = groupIndex * sector;
    members.forEach((member, index) => {
      // At most six records per ring per type; further rings stack above and
      // below so a large product list never flattens into a wall.
      const ring = Math.floor(index / 6);
      const radius = 1.5 + ring * 0.95;
      const step = sector / Math.max(Math.min(members.length, 6), 1);
      const angle = start + step * (index % 6) + step / 2;
      const height = ring === 0 ? 0 : (index % 2 === 0 ? 0.45 : -0.45) * ring;
      positions.set(NODE_ID(member), [Math.cos(angle) * radius, height, Math.sin(angle) * radius]);
    });
  });

  return positions;
}

/**
 * One record in the neighbourhood. The selected record is the centre of the
 * scene; hovering any record lifts it and lights every connection it takes part
 * in, which is how the shape of a relationship is read without a legend.
 */
function Node({
  node,
  position,
  isRoot,
  connected,
  hovered,
  onHover,
  onSelect,
  showLabel,
  dimmed,
  reducedDetail,
}: {
  node: SceneGraphNode;
  position: [number, number, number];
  isRoot: boolean;
  connected: boolean;
  hovered: boolean;
  onHover: (id: string | null) => void;
  onSelect?: (node: SceneGraphNode) => void;
  showLabel: boolean;
  dimmed: boolean;
  reducedDetail: boolean;
}) {
  const palette = scenePalette();
  const mesh = useRef<THREE.Mesh>(null);
  const id = NODE_ID(node);
  const colour = isRoot ? palette.primary : labelColour(node.label, palette);
  const base = isRoot ? 0.22 : areaRadius(node.label);
  const radius = base * (hovered ? 1.2 : connected ? 1.1 : 1);

  useFrame(({ clock }) => {
    if (!mesh.current) return;
    const phase = (id.length % 9) * 0.7;
    mesh.current.position.y = Math.sin(clock.elapsedTime * 0.4 + phase) * 0.035;
  });

  return (
    <group position={position}>
      <mesh
        ref={mesh}
        onClick={
          onSelect && !isRoot
            ? (event: ThreeEvent<MouseEvent>) => {
                event.stopPropagation();
                onSelect(node);
              }
            : undefined
        }
        onPointerOver={
          onSelect
            ? (event: ThreeEvent<PointerEvent>) => {
                event.stopPropagation();
                onHover(id);
                if (!isRoot) document.body.style.cursor = "pointer";
              }
            : undefined
        }
        onPointerOut={
          onSelect
            ? () => {
                onHover(null);
                document.body.style.cursor = "";
              }
            : undefined
        }
      >
        <sphereGeometry args={[radius, reducedDetail ? 16 : 24, reducedDetail ? 12 : 18]} />
        <meshStandardMaterial
          color={colour}
          roughness={0.45}
          metalness={0.05}
          transparent
          opacity={dimmed ? 0.28 : 1}
          emissive={hovered ? colour : "#000000"}
          emissiveIntensity={hovered ? 0.28 : 0}
        />
      </mesh>
      {showLabel ? (
        <SceneLabel center distanceFactor={9} prepend={false} zIndexRange={[10, 0]}>
          <span
            className={
              isRoot
                ? "pointer-events-none whitespace-nowrap rounded border border-primary/40 bg-background/95 px-1.5 py-0.5 text-[10px] font-semibold text-primary"
                : "pointer-events-none whitespace-nowrap rounded border bg-background/95 px-1.5 py-0.5 text-[10px] text-foreground"
            }
          >
            {node.name ?? `${node.label} · ${node.key.slice(-6)}`}
          </span>
        </SceneLabel>
      ) : null}
    </group>
  );
}

export function GraphNeighbourhood({
  root,
  nodes,
  edges,
  onSelect,
  reducedDetail = false,
}: {
  root: SceneGraphNode;
  nodes: SceneGraphNode[];
  edges: SceneGraphEdge[];
  onSelect?: (node: SceneGraphNode) => void;
  reducedDetail?: boolean;
}) {
  const palette = scenePalette();
  const [hovered, setHovered] = useState<string | null>(null);

  // The root record is drawn from the same list so it is never duplicated.
  const sceneNodes = useMemo(() => {
    const seen = new Set<string>();
    const list: SceneGraphNode[] = [{ label: root.label, key: root.key, name: root.name }, ...nodes];
    return list.filter((node) => (seen.has(NODE_ID(node)) ? false : seen.add(NODE_ID(node))));
  }, [nodes, root]);

  const positions = useMemo(() => layout(root, sceneNodes), [root, sceneNodes]);

  const { edgePositions, adjacency } = useMemo(() => {
    const points: number[] = [];
    const map = new Map<string, Set<string>>();
    const add = (from: string, to: string) => {
      const set = map.get(from) ?? new Set<string>();
      set.add(to);
      map.set(from, set);
    };
    for (const edge of edges) {
      const fromId = NODE_ID(edge.start);
      const toId = NODE_ID(edge.end);
      const from = positions.get(fromId);
      const to = positions.get(toId);
      if (from && to) points.push(...from, ...to);
      // Highlighting follows the edges that are actually drawn.
      if (from && to) {
        add(fromId, toId);
        add(toId, fromId);
      }
    }
    return { edgePositions: points, adjacency: map };
  }, [edges, positions]);

  // One representative label per record type keeps the scene readable; the
  // hovered record and the selected one always name themselves.
  const labelled = useMemo(() => {
    const first = new Map<string, string>();
    for (const node of sceneNodes) {
      if (!first.has(node.label)) first.set(node.label, NODE_ID(node));
    }
    return new Set(first.values());
  }, [sceneNodes]);

  const rootId = NODE_ID(root);
  const connectedToHover = hovered ? adjacency.get(hovered) ?? new Set<string>() : new Set<string>();

  return (
    <>
      <lineSegments key={`edges-${edgePositions.length}`} frustumCulled={false}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            array={new Float32Array(edgePositions)}
            count={edgePositions.length / 3}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color={palette.border} transparent opacity={0.95} />
      </lineSegments>

      {sceneNodes.map((node) => {
        const id = NODE_ID(node);
        const position = positions.get(id);
        if (!position) return null;
        const isRoot = id === rootId;
        const hoveredHere = hovered === id;
        const connected = hovered !== null && (connectedToHover.has(id) || id === hovered);
        return (
          <Node
            key={id}
            node={node}
            position={position}
            isRoot={isRoot}
            connected={connected}
            hovered={hoveredHere}
            onHover={setHovered}
            onSelect={onSelect}
            showLabel={isRoot || hoveredHere || connected || labelled.has(id)}
            dimmed={hovered !== null && !connected && !isRoot}
            reducedDetail={reducedDetail}
          />
        );
      })}
    </>
  );
}
