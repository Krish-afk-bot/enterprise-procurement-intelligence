import { useEffect, useState } from "react";
import { BadgeCheck, FileText, Quote } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Animated evidence verification flow: passage → claim → verification → citation.
 * Shows the verification pipeline with status transitions.
 */
export function EvidenceVerificationDemo({ active = false }: { active?: boolean }) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (!active) {
      setStage(0);
      return;
    }

    const stages = [0, 1, 2, 3];
    let current = 0;

    const timer = setInterval(() => {
      current = (current + 1) % stages.length;
      setStage(stages[current]);
    }, 2000);

    return () => clearInterval(timer);
  }, [active]);

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-white/12 bg-white/[0.04] p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <BadgeCheck className="h-3.5 w-3.5 text-white/50" aria-hidden="true" />
            <span className="text-[10px] uppercase tracking-[0.12em] text-subtle">evidence pipeline</span>
          </div>
          {stage > 0 && (
            <span className="rounded-full border border-white/20 bg-white/[0.08] px-2 py-0.5 text-[8px] uppercase tracking-wider text-white/80">
              stage {stage}/3
            </span>
          )}
        </div>
      </div>

      {/* Retrieved passage */}
      <div
        className={cn(
          "rounded-lg border px-3 py-2.5 transition-all duration-500",
          stage >= 1 ? "border-white/15 bg-white/[0.05]" : "border-white/[0.08] bg-white/[0.02]",
        )}
      >
        <div className="flex items-center gap-2">
          <Quote className={cn("h-3 w-3", stage >= 1 ? "text-white/70" : "text-white/40")} aria-hidden="true" />
          <span
            className={cn(
              "text-[10px] uppercase tracking-[0.12em]",
              stage >= 1 ? "text-subtle" : "text-subtle/60",
            )}
          >
            retrieved passage
          </span>
        </div>
        <div className="mt-2 space-y-1">
          <span className="block h-1.5 w-[88%] rounded-full bg-white/20" />
          <span className="block h-1.5 w-[72%] rounded-full bg-white/15" />
        </div>
      </div>

      {/* Generated claim */}
      <div
        className={cn(
          "rounded-lg border px-3 py-2.5 transition-all duration-500",
          stage >= 2 ? "border-white/15 bg-white/[0.05]" : "border-white/[0.08] bg-white/[0.02]",
        )}
      >
        <p
          className={cn(
            "text-[11.5px] leading-relaxed transition-colors",
            stage >= 2 ? "text-foreground/90" : "text-muted-foreground",
          )}
        >
          The amended pricing schedule applies from April 1st; the superseded annex no longer governs that line item.
        </p>
      </div>

      {/* Verification result */}
      <div
        className={cn(
          "rounded-lg border px-3 py-2 transition-all duration-500",
          stage >= 3 ? "border-success/30 bg-success/[0.06]" : "border-white/[0.08] bg-white/[0.02]",
        )}
      >
        <div className="flex items-center gap-2">
          <BadgeCheck
            className={cn("h-3.5 w-3.5", stage >= 3 ? "text-success" : "text-white/30")}
            aria-hidden="true"
          />
          <span
            className={cn(
              "flex-1 text-[10.5px] uppercase tracking-[0.1em]",
              stage >= 3 ? "text-foreground/90" : "text-muted-foreground",
            )}
          >
            {stage >= 3 ? "supported" : "verifying..."}
          </span>
          {stage >= 3 && (
            <span className="font-mono text-[9px] text-subtle">2 passages</span>
          )}
        </div>
      </div>

      {/* Citations */}
      {stage >= 3 && (
        <div className="animate-fade-in rounded-lg border border-white/12 bg-white/[0.03] p-3">
          <span className="flex items-center gap-1.5 text-[9px] uppercase tracking-[0.12em] text-subtle">
            <FileText className="h-2.5 w-2.5" aria-hidden="true" />
            citations
          </span>
          <div className="mt-2 space-y-1.5">
            {["Amendment 2 · page 4 · clause 2.1", "Pricing Schedule · page 12 · section A"].map((citation) => (
              <p key={citation} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <span className="h-px w-2 bg-white/30" aria-hidden="true" />
                {citation}
              </p>
            ))}
          </div>
        </div>
      )}

      <p className="flex items-center gap-1.5 text-[9px] uppercase tracking-[0.12em] text-subtle">
        <span className="h-1 w-1 rounded-full bg-white/40" aria-hidden="true" />
        demonstration: verification pipeline
      </p>
    </div>
  );
}
