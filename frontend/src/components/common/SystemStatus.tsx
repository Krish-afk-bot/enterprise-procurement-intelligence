import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/misc";
import type { HealthResponse } from "@/lib/types";
import { cn, toneDot, titleCase } from "@/lib/utils";

interface CapabilityRow {
  label: string;
  value: string;
  detail: string;
  tone: "success" | "warning" | "neutral";
}

/**
 * Turns the provider snapshot into plain sentences. When a model is not
 * configured the label says so; nothing pretends a model is in the loop.
 */
export function capabilityRows(health: HealthResponse | undefined): CapabilityRow[] {
  const capabilities = health?.capabilities ?? {};
  const providers = health?.providers ?? {};
  const providerName = (kind: string) => providers[kind]?.name ?? "not reported";

  return [
    {
      label: "Answer generation",
      value: capabilities.llm_generation ? "Model-backed" : "Evidence-based answers",
      detail: capabilities.llm_generation
        ? "A language model is configured. Answers are generated and then verified against the retrieved evidence."
        : "No language model endpoint is configured, so answers are composed verbatim from retrieved passages and every sentence traces to a citation. The mode is named 'extractive' in the technical details.",
      tone: capabilities.llm_generation ? "success" : "warning",
    },
    {
      label: "Page understanding",
      value: capabilities.vision_generation ? "Vision model available" : "OCR and text layer only",
      detail: capabilities.vision_generation
        ? "Scanned pages can be escalated to a vision model."
        : "Scanned pages are handled by OCR. No vision model is configured, so no image reasoning is performed.",
      tone: capabilities.vision_generation ? "success" : "neutral",
    },
    {
      label: "Reranking",
      value: capabilities.reranking ? "Enabled" : "Disabled",
      detail: capabilities.reranking
        ? "A cross-encoder reranks fused candidates before the answer is built."
        : "Candidates are ranked by fusion only; no cross-encoder is loaded.",
      tone: capabilities.reranking ? "success" : "neutral",
    },
    {
      label: "Retrieval index",
      value: providerName("vector"),
      detail: providers.vector?.detail ?? "Vector provider not reported.",
      tone: providers.vector?.available === false ? "warning" : "success",
    },
    {
      label: "Graph index",
      value: providerName("graph"),
      detail: providers.graph?.detail ?? "Graph provider not reported.",
      tone: providers.graph?.available === false ? "warning" : "success",
    },
    {
      label: "Document store",
      value: providerName("storage"),
      detail: providers.storage?.detail ?? "Storage provider not reported.",
      tone: providers.storage?.available === false ? "warning" : "success",
    },
  ];
}

/** Inline status used in the workspace header. */
export function SystemStatusSummary({ health, className }: { health: HealthResponse | undefined; className?: string }) {
  if (!health) {
    return <span className={cn("text-[11px] text-muted-foreground", className)}>Checking deployment status</span>;
  }
  const generation = health.capabilities?.llm_generation ? "Model-backed generation" : "Evidence-based answers";
  const tone: "warning" | "success" = health.capabilities?.llm_generation ? "success" : "warning";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded border border-border bg-background px-2 py-1 text-[11px] text-muted-foreground",
            className,
          )}
        >
          <span className={cn("h-1.5 w-1.5 rounded-full", toneDot(tone))} aria-hidden="true" />
          {generation}
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-sm">
        {health.capabilities?.llm_generation
          ? "A language model is configured for answer generation."
          : "No language model endpoint is configured on this deployment. Answers are composed from retrieved passages, and each statement keeps its citation."}
      </TooltipContent>
    </Tooltip>
  );
}

/** Full status table, used on the dashboard and the administration page. */
export function SystemStatusPanel({ health }: { health: HealthResponse | undefined }) {
  const rows = capabilityRows(health);
  const fallbacks = health?.fallbacks ?? [];

  return (
    <div className="space-y-3">
      <dl className="divide-y divide-border/70">
        {rows.map((row) => (
          <div key={row.label} className="grid gap-1 py-2.5 sm:grid-cols-[190px_1fr] sm:gap-4">
            <dt className="flex items-center gap-2 text-xs font-medium">
              <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", toneDot(row.tone))} aria-hidden="true" />
              {row.label}
            </dt>
            <dd className="min-w-0">
              <p className="text-xs font-medium">{row.value}</p>
              <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">{row.detail}</p>
            </dd>
          </div>
        ))}
      </dl>

      {fallbacks.length > 0 ? (
        <div className="rounded-md border border-warning/35 bg-warning/5 p-3">
          <p className="text-xs font-medium text-warning">Fallback providers were used</p>
          <ul className="mt-1 space-y-1 text-[11px] text-muted-foreground">
            {fallbacks.map((fallback) => (
              <li key={`${fallback.kind}-${fallback.requested}`}>
                {titleCase(fallback.kind)}: requested {fallback.requested}, using {fallback.used}. {fallback.reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {health?.details && Object.keys(health.details).length > 0 ? (
        <details className="rounded-md border p-3 text-[11px] text-muted-foreground">
          <summary className="cursor-pointer text-xs font-medium text-foreground">Deployment details</summary>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap scrollbar-thin">{JSON.stringify(health.details, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}
