import { useEffect, useRef, useState } from "react";
import { FileSearch, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Animated procurement search demonstration showing query → results flow.
 * Illustrative content, labeled as demonstration.
 */
export function ProcurementSearchDemo({ active = false }: { active?: boolean }) {
  const [phase, setPhase] = useState(0);
  const timerRef = useRef<number>();

  useEffect(() => {
    if (!active) {
      setPhase(0);
      if (timerRef.current) clearTimeout(timerRef.current);
      return;
    }

    // Cycle through phases when active
    const phases = [0, 1, 2, 3];
    let current = 0;

    const advance = () => {
      current = (current + 1) % phases.length;
      setPhase(phases[current]);
      timerRef.current = window.setTimeout(advance, 2200);
    };

    timerRef.current = window.setTimeout(advance, 1600);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [active]);

  const results = [
    { label: "Master Agreement · Section 4.2 · Pricing", score: "0.94", page: "12" },
    { label: "Amendment 2 · Schedule A · Unit Prices", score: "0.89", page: "4" },
    { label: "Tender Notice · Lot 3 · Equipment Pricing", score: "0.76", page: "8" },
  ];

  return (
    <div className="space-y-3">
      <div
        className={cn(
          "flex items-center gap-2 rounded-lg border bg-white/[0.04] px-3 py-2.5 transition-all duration-500",
          phase >= 1 ? "border-white/20" : "border-white/10",
        )}
      >
        <FileSearch
          className={cn(
            "h-4 w-4 transition-colors",
            phase >= 1 ? "text-white/70" : "text-white/40",
          )}
          aria-hidden="true"
        />
        <span
          className={cn(
            "flex-1 text-[12px] transition-colors",
            phase >= 1 ? "text-foreground/90" : "text-muted-foreground",
          )}
        >
          unit price for industrial equipment
        </span>
        {phase >= 1 && (
          <span className="h-1 w-1 animate-pulse rounded-full bg-white/80" aria-hidden="true" />
        )}
      </div>

      <div className="space-y-2">
        {results.map((result, index) => {
          const resultPhase = index + 2;
          const isActive = phase >= resultPhase;

          return (
            <div
              key={result.label}
              className={cn(
                "flex items-start gap-3 rounded-lg border px-3 py-2.5 transition-all duration-500",
                isActive
                  ? "translate-y-0 border-white/15 bg-white/[0.05] opacity-100"
                  : "translate-y-2 border-white/[0.07] bg-white/[0.02] opacity-40",
              )}
            >
              <FileText
                className={cn(
                  "mt-0.5 h-3.5 w-3.5 shrink-0 transition-colors",
                  isActive ? "text-white/60" : "text-white/30",
                )}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <p
                  className={cn(
                    "text-[11.5px] leading-snug transition-colors",
                    isActive ? "text-foreground/90" : "text-muted-foreground",
                  )}
                >
                  {result.label}
                </p>
                <div className="mt-1.5 flex items-center gap-2">
                  <span className="rounded-sm border border-white/15 px-1.5 py-0.5 text-[8px] uppercase tracking-wider text-subtle">
                    page {result.page}
                  </span>
                  <span
                    className={cn(
                      "font-mono text-[9px] transition-colors",
                      isActive ? "text-subtle" : "text-subtle/60",
                    )}
                  >
                    {result.score}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <p className="flex items-center gap-1.5 text-[9px] uppercase tracking-[0.12em] text-subtle">
        <span className="h-1 w-1 rounded-full bg-white/40" aria-hidden="true" />
        demonstration: illustrative search flow
      </p>
    </div>
  );
}
