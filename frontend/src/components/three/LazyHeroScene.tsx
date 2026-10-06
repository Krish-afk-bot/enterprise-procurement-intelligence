import { Suspense, lazy } from "react";

const HeroEvidenceScene = lazy(() => import("@/components/three/HeroEvidenceScene"));

export function LazyHeroScene({ fallback }: { fallback: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="flex h-[300px] items-center justify-center rounded-lg border bg-muted/20 text-xs text-muted-foreground">
          Loading the illustration
        </div>
      }
    >
      <HeroEvidenceScene fallback={fallback} />
    </Suspense>
  );
}
