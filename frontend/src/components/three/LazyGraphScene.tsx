import { Suspense, lazy } from "react";

import type { SceneGraphEdge, SceneGraphNode } from "@/components/three/GraphNeighbourhood";
import { MICROCOPY } from "@/lib/microcopy";

const GraphScene3D = lazy(() => import("@/components/three/GraphScene3D"));

/**
 * Only the `import()` above is in the main bundle. three.js and the scene code
 * are fetched when this component first renders, which is when the reader has
 * opened a traversal that has records in it.
 */
export function LazyGraphScene({
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
  fallback: React.ReactNode;
}) {
  return (
    <Suspense
      fallback={
        <div className="flex h-[460px] items-center justify-center rounded-lg border bg-muted/20 text-xs text-muted-foreground">
          {MICROCOPY.loadingScene} The table below already lists the same connections.
        </div>
      }
    >
      <GraphScene3D root={root} nodes={nodes} edges={edges} hops={hops} onSelect={onSelect} fallback={fallback} />
    </Suspense>
  );
}
