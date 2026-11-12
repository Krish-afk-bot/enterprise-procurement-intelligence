import { useEffect, useState } from "react";
import { Layers } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Animated retrieval flow showing dense → sparse → structured → fusion → rerank.
 * Illustrative content demonstrating the hybrid retrieval pipeline.
 */
export function RetrievalFlowDemo({ active = false }: { active?: boolean }) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (!active) {
      setStage(0);
      return;
    }

    const stages = [0, 1, 2, 3, 4];
    let current = 0;

    const timer = setInterval(() => {
      current = (current + 1) % stages.length;
      setStage(stages[current]);
    }, 1800);

    return () => clearInterval(timer);
  }, [active]);

  const steps = [
    { label: "Dense vectors", count: 47, color: "bg-white/30" },
    { label: "Sparse (BM25)", count: 32, color: "bg-white/25" },
    { label: "Structured rows", count: 18, color: "bg-white/20" },
    { label: "Fusion (RRF)", count: 24, color: "bg-white/35" },
    { label: "Reranked", count: 12, color: "bg-white/50" },
  ];

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-white/12 bg-white/[0.04] p-3">
        <div className="flex items-center gap-2">
          <Layers className="h-3.5 w-3.5 text-white/50" aria-hidden="true" />
          <span className="text-[10px] uppercase tracking-[0.12em] text-subtle">hybrid retrieval pipeline</span>
        </div>
      </div>

      <div className="space-y-2">
        {steps.map((step, index) => {
          const isActive = stage >= index;
          const width = (step.count / 50) * 100;

          return (
            <div
              key={step.label}
              className={cn(
                "rounded-lg border px-3 py-2 transition-all duration-500",
                isActive ? "border-white/15 bg-white/[0.05]" : "border-white/[0.08] bg-white/[0.02]",
              )}
            >
              <div className="flex items-center justify-between">
                <span
                  className={cn(
                    "text-[10.5px] transition-colors",
                    isActive ? "text-foreground/90" : "text-muted-foreground",
                  )}
                >
                  {step.label}
                </span>
                <span
                  className={cn(
                    "font-mono text-[9px] transition-colors",
                    isActive ? "text-subtle" : "text-subtle/60",
                  )}
                >
                  {step.count} candidates
                </span>
              </div>
              <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-white/10">
                <span
                  className={cn(
                    "block h-full origin-left rounded-full transition-all duration-700",
                    step.color,
                    isActive ? "scale-x-100" : "scale-x-0",
                  )}
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <p className="flex items-center gap-1.5 text-[9px] uppercase tracking-[0.12em] text-subtle">
        <span className="h-1 w-1 rounded-full bg-white/40" aria-hidden="true" />
        demonstration: retrieval stages
      </p>
    </div>
  );
}
