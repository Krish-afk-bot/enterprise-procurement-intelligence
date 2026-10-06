import type { ReactNode } from "react";

import { GraphNeighbourhood, type SceneGraphEdge, type SceneGraphNode } from "@/components/three/GraphNeighbourhood";
import { labelColour, scenePalette } from "@/components/three/palette";
import { SceneFrame } from "@/components/three/SceneFrame";
import { useReducedDetail } from "@/lib/useMediaQuery";

/**
 * Heavy entry point for the relationships page: this module is what the lazy
 * loader pulls in, so three.js never reaches a reader who does not open it.
 */
export default function GraphScene3D({
  root,
  nodes,
  edges,
  hops,
  onSelect,
  fallback,
}: {
  root: SceneGraphNode;
  nodes: SceneGraphNode[];
  edges: SceneGraphEdge[];
  hops: number;
  onSelect?: (node: SceneGraphNode) => void;
  fallback: ReactNode;
}) {
  const reducedDetail = useReducedDetail();
  const palette = scenePalette();
  const types = [...new Set(nodes.map((node) => node.label))].sort();

  return (
    <SceneFrame
      title="Relationship neighbourhood"
      caption={`Every record the traversal reached within ${hops} hop(s), placed by record type around the selected one. Drag to orbit, scroll to zoom, right-drag to pan. Select a record to make it the new centre.`}
      ariaLabel={`Relationship neighbourhood of ${
        root.name ?? root.label
      } drawn as ${nodes.length} record(s) and ${edges.length} connection(s). The table below lists the same connections as text.`}
      fallback={fallback}
      height={460}
      cameraPosition={[0, 2.6, 6.4]}
      maxDistance={16}
      autoRotateSpeed={0.24}
      legend={
        <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
          {types.map((type) => (
            <li key={type} className="flex items-center gap-1.5">
              <span
                aria-hidden="true"
                className="inline-block h-2 w-2 rounded-full border"
                style={{ background: labelColour(type, palette) }}
              />
              {type}
            </li>
          ))}
          <li>Hover a record to light its connections · select it to re-centre the traversal</li>
        </ul>
      }
    >
      <GraphNeighbourhood root={root} nodes={nodes} edges={edges} onSelect={onSelect} reducedDetail={reducedDetail} />
    </SceneFrame>
  );
}
