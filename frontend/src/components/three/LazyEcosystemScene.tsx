import { Suspense, lazy } from "react";

import type { EcosystemModel } from "@/lib/ecosystem";

const EcosystemScene = lazy(() => import("@/components/three/EcosystemScene"));

/**
 * Only the `import()` above is in the main bundle. three.js and the scene code
 * are fetched when the overview actually renders a scene, which is when the
 * workspace holds at least one supplier record.
 */
export function LazyEcosystemScene({
  model,
  fallback,
  legend,
}: {
  model: EcosystemModel;
  fallback: React.ReactNode;
  legend?: React.ReactNode;
}) {
  return (
    <Suspense
      fallback={
        <div className="flex h-[360px] items-center justify-center rounded-lg border bg-muted/20 text-xs text-muted-foreground">
          Loading the ecosystem view — the counts beside it are already exact
        </div>
      }
    >
      <EcosystemScene model={model} fallback={fallback} legend={legend} />
    </Suspense>
  );
}
