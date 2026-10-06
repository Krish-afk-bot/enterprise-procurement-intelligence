import { ArrowRight } from "lucide-react";

import { cn, plural } from "@/lib/utils";

/**
 * The motion between evidence and answer, made legible: what was read, what was
 * verified, and what came out. It is one line of text with a slow travelling
 * highlight — no figures are added, and the counts are the ones the answer
 * already reports.
 */
export function EvidenceFlowStrip({
  passages,
  verified,
  status,
  className,
}: {
  passages: number;
  verified: number;
  status: string;
  className?: string;
}) {
  const steps = [
    { label: `${plural(passages, "passage")} read`, detail: "retrieved from the indexed documents" },
    { label: `${plural(verified, "citation")} verified`, detail: "checked against the passage text" },
    { label: status, detail: "the outcome the pipeline reported" },
  ];

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-2 gap-y-1.5 rounded-md border bg-muted/25 px-3 py-2 text-[11px]",
        className,
      )}
      aria-hidden="true"
    >
      {steps.map((step, index) => (
        <span key={step.label} className="flex items-center gap-2">
          {index > 0 ? (
            <span className="flex items-center gap-1 text-muted-foreground/70">
              <span className="flow-dot h-1 w-1 rounded-full bg-primary" />
              <ArrowRight className="h-3 w-3" />
            </span>
          ) : (
            <span className="flow-dot h-1 w-1 rounded-full bg-primary" />
          )}
          <span className="min-w-0">
            <span className="font-medium text-foreground">{step.label}</span>
            <span className="ml-1 text-muted-foreground">{step.detail}</span>
          </span>
        </span>
      ))}
    </div>
  );
}
