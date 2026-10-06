import { BookOpen, CheckCircle2, Gauge, SearchCheck, Wrench } from "lucide-react";

import { EvidenceItem } from "@/components/common/Evidence";
import { Separator } from "@/components/ui/misc";
import type { Answer } from "@/lib/types";
import { answerStatus, cn, formatPercent, titleCase, toneClasses } from "@/lib/utils";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}

export function EvidencePanel({
  answer,
  showTrace = false,
  detailsOpen,
  onDetailsOpenChange,
}: {
  answer: Answer;
  showTrace?: boolean;
  detailsOpen?: boolean;
  onDetailsOpenChange?: (open: boolean) => void;
}) {
  const validation = (answer.validation ?? {}) as Record<string, unknown>;
  const status = answerStatus(answer.status);
  const groundingScore =
    answer.grounding.total_claims > 0 ? answer.grounding.supported_claims / answer.grounding.total_claims : null;
  // Markers the composed answer actually quoted. When the pipeline reports
  // them, evidence outside that set is labelled rather than silently implied.
  const referenced = Array.isArray(validation.referenced_markers)
    ? new Set((validation.referenced_markers as unknown[]).map((value) => Number(value)))
    : null;

  return (
    <div className="space-y-5">
      <section aria-labelledby="evidence-heading">
        <h2 id="evidence-heading" className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <BookOpen className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          Evidence
          <span className="text-xs font-normal text-muted-foreground">
            {answer.citations.length === 1 ? "1 citation" : `${answer.citations.length} citations`}
          </span>
        </h2>
        <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
          Each citation opens the document at the page it came from.
        </p>
        {answer.citations.length === 0 ? (
          <p className="mt-3 rounded-md border border-dashed p-3 text-xs text-muted-foreground">
            No citation survived verification, so none is shown. An answer without evidence is not presented as if it had
            some.
          </p>
        ) : (
          <ol className="mt-1">
            {answer.citations.map((citation, index) => (
              <EvidenceItem
                key={citation.chunk_id ?? `${citation.document_id}-${index}`}
                citation={citation}
                index={index + 1}
                referenced={referenced ? referenced.has(index + 1) : undefined}
              />
            ))}
          </ol>
        )}
      </section>

      <Separator />

      {/* How the answer was produced is available, not in the way: everything
          below sits behind one disclosure. */}
      <details
        id="technical-details"
        open={detailsOpen}
        onToggle={(event) => onDetailsOpenChange?.((event.currentTarget as HTMLDetailsElement).open)}
        className="scroll-mt-20 rounded-md border bg-muted/20"
      >
        <summary className="flex cursor-pointer items-center gap-2 px-3 py-2.5 text-xs font-medium">
          <Wrench className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
          Technical details
          <span className="text-[11px] font-normal text-muted-foreground">
            verification, retrieval steps, how the question was read
            {answer.trace.length > 0 ? ", execution trace" : ""}
          </span>
        </summary>
        <div className="space-y-5 border-t p-3">
      <section aria-labelledby="verification-heading">
        <h2 id="verification-heading" className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <CheckCircle2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          Verification
        </h2>
        <span className={cn("mt-2 inline-flex rounded border px-2 py-0.5 text-[11px] font-medium", toneClasses(status.tone))}>
          {status.label}
        </span>
        <dl className="mt-2 space-y-1.5 text-xs">
          <Row label="Evidence strength" value={titleCase(answer.evidence_strength.level)} />
          <Row label="Grounding method" value={answer.grounding.method} />
          <Row
            label="Claims supported"
            value={`${answer.grounding.supported_claims} of ${answer.grounding.total_claims}${
              groundingScore !== null ? ` (${formatPercent(groundingScore, 0)})` : ""
            }`}
          />
          <Row label="Citations valid" value={String(validation.valid_citations ?? 0)} />
          <Row label="Citations rejected" value={String(validation.invalid_citations ?? 0)} />
          <Row label="Refusal triggered" value={validation.refusal_triggered ? "yes" : "no"} />
          <Row label="Generation" value={answer.generation_mode} />
        </dl>
        {answer.grounding.unsupported_claims.length > 0 ? (
          <>
            <p className="mt-3 text-xs font-medium">Statements without support</p>
            <ul className="mt-1 space-y-1 text-[11px] text-muted-foreground">
              {answer.grounding.unsupported_claims.slice(0, 5).map((claim, index) => (
                <li key={index} className="border-l pl-2">
                  {claim}
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </section>

      <Separator />

      <section aria-labelledby="retrieval-heading">
        <h2 id="retrieval-heading" className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <Gauge className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          Retrieval
        </h2>
        <ol className="mt-2 space-y-2 text-xs">
          {answer.retrieval_steps.map((step) => (
            <li key={step.name} className="grid grid-cols-[1fr_auto] gap-2 border-b border-border/60 pb-2 last:border-0">
              <div className="min-w-0">
                <p className="font-medium">{titleCase(step.name)}</p>
                <p className="text-muted-foreground">{step.detail}</p>
              </div>
              <div className="tnum shrink-0 text-right text-muted-foreground">
                <p>{step.candidates} candidates</p>
                <p>{step.latency_ms !== null ? `${step.latency_ms} ms` : "not timed"}</p>
              </div>
            </li>
          ))}
        </ol>
        <dl className="mt-2 space-y-1.5 text-xs">
          <Row label="Total" value={answer.timings.total_ms !== undefined ? `${answer.timings.total_ms} ms` : "not timed"} />
          <Row
            label="Generation"
            value={answer.timings.generation_ms !== undefined ? `${answer.timings.generation_ms} ms` : "not timed"}
          />
        </dl>
      </section>

      <Separator />

      <section aria-labelledby="understanding-heading">
        <h2 id="understanding-heading" className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <SearchCheck className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          How the question was read
        </h2>
        <dl className="mt-2 space-y-1.5 text-xs">
          <Row label="Intent" value={titleCase(String(answer.plan.intent ?? "not reported"))} />
          <Row label="Method" value={titleCase(String(answer.plan.method ?? "not reported"))} />
          <Row label="Complexity" value={titleCase(String(answer.plan.complexity ?? "not reported"))} />
          <Row label="Prompt version" value={answer.prompt_version ?? "not recorded"} />
          <Row label="Tokens" value={Object.values(answer.token_usage ?? {}).reduce((total, value) => total + Number(value || 0), 0) > 0 ? JSON.stringify(answer.token_usage) : "not recorded"} />
        </dl>
      </section>

      {showTrace && answer.trace.length > 0 ? (
        <>
          <section aria-labelledby="trace-heading">
            <h2 id="trace-heading" className="text-sm font-semibold tracking-tight">
              Execution trace
            </h2>
            <ol className="mt-2 space-y-2 text-xs">
              {answer.trace.map((event, index) => (
                <li key={index} className="border-b border-border/60 pb-2 last:border-0">
                  <p className="font-mono text-[10px] text-muted-foreground">
                    {String((event as { node?: string }).node ?? "node")} · {String((event as { event?: string }).event ?? "")}
                  </p>
                  <p>{String((event as { detail?: string }).detail ?? "")}</p>
                </li>
              ))}
            </ol>
          </section>
        </>
      ) : null}
        </div>
      </details>
    </div>
  );
}
