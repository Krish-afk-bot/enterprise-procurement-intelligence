import { AlertTriangle, FileSearch, FileWarning, Info, TriangleAlert } from "lucide-react";

import { AnswerText } from "@/components/answer/AnswerText";
import { EvidenceFlowStrip } from "@/components/answer/EvidenceFlowStrip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CitationChip } from "@/components/common/Evidence";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/misc";
import { MICROCOPY, microcopyPlain } from "@/lib/microcopy";
import type { Answer } from "@/lib/types";
import { answerStatus, cn, evidenceLevel, plural, titleCase, toneClasses } from "@/lib/utils";

function asList(value: unknown): string[] {
  if (!Array.isArray(value) || value.length === 0) return [];
  return value.map(String);
}

/**
 * Shown when the platform refuses. It states what was actually searched, so a
 * refusal reads as a measured outcome rather than an empty screen.
 */
function RefusalCard({ answer, onShowDetails }: { answer: Answer; onShowDetails?: () => void }) {
  const documents = Array.from(
    new Set(
      answer.citations
        .map((citation) => citation.document_name ?? citation.label)
        .filter((name): name is string => Boolean(name)),
    ),
  );
  // Candidates retrieved across the pipeline. The largest non-zero count is the
  // fairest description of how much was looked at; a later step can legitimately
  // report fewer (filtering) or a failed step can report none.
  const passages = answer.citations.length;
  const candidates = answer.retrieval_steps.length
    ? Math.max(...answer.retrieval_steps.map((step) => step.candidates))
    : undefined;

  return (
    <section aria-labelledby="refusal-heading" className="space-y-3 rounded-lg border border-destructive/35 bg-destructive/5 p-4">
      <h3 id="refusal-heading" className="flex items-center gap-2 text-sm font-semibold">
        <FileSearch className="h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
        {MICROCOPY.unsupported}
      </h3>
      <p className="text-xs leading-relaxed text-muted-foreground">
        {microcopyPlain("unsupported")} The platform reports the gap rather than filling it with a plausible number.
      </p>
      <dl className="grid gap-2 text-xs sm:grid-cols-3">
        <div>
          <dt className="text-muted-foreground">Documents checked</dt>
          <dd className="tnum font-medium">{plural(documents.length, "document")}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Relevant passages</dt>
          <dd className="tnum font-medium">{plural(passages, "passage")}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Retrieval outcome</dt>
          <dd className="tnum font-medium">
            {candidates !== undefined ? `${candidates} candidate(s) → ${passages} read` : `${passages} read`}
          </dd>
        </div>
      </dl>
      {documents.length > 0 ? (
        <p className="text-[11px] leading-relaxed text-muted-foreground">
          Closest material found: {documents.slice(0, 4).join(", ")}
          {documents.length > 4 ? ` and ${documents.length - 4} more` : ""}.
        </p>
      ) : null}
      {onShowDetails ? (
        <Button variant="outline" size="sm" onClick={onShowDetails}>
          See retrieval details
        </Button>
      ) : null}
    </section>
  );
}

export function AnswerPanel({ answer, onShowDetails }: { answer: Answer; onShowDetails?: () => void }) {
  const status = answerStatus(answer.status);
  const strength = evidenceLevel(answer.evidence_strength.level);
  const validation = (answer.validation ?? {}) as Record<string, unknown>;
  const coverage = (validation.coverage ?? {}) as { satisfied?: boolean; unsatisfied?: string[] };
  const extractive = answer.generation_mode === "extractive";
  const refused = answer.status === "insufficient_evidence";
  const conflicted = answer.status === "conflicting";
  const supported = answer.status === "supported";
  const verified = answer.citations.filter((citation) => citation.verified).length;
  // One line of personality, chosen by what the pipeline actually reported.
  const verdict = refused ? MICROCOPY.unsupported : conflicted ? MICROCOPY.conflict : supported ? MICROCOPY.evidenceFound : null;

  const basis = [
    { label: "Suppliers", values: asList(answer.plan.suppliers) },
    { label: "Products", values: asList(answer.plan.products) },
    { label: "Contracts", values: asList(answer.plan.contract_numbers) },
    { label: "Period", values: answer.plan.year ? [String(answer.plan.year)] : [] },
  ].filter((entry) => entry.values.length > 0);

  return (
    <article aria-labelledby="answer-heading" className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="answer-heading" className="text-sm font-semibold tracking-tight">
          Answer
        </h2>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant="outline" className={cn("font-normal", toneClasses(status.tone))}>
              {status.label}
            </Badge>
          </TooltipTrigger>
          <TooltipContent className="max-w-sm">{status.meaning}</TooltipContent>
        </Tooltip>
        <Badge variant="outline" className={cn("font-normal", toneClasses(strength.tone))}>
          {strength.label}
        </Badge>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant="outline" className={cn("font-normal", "text-foreground")}>
              {extractive ? "Evidence-based answer" : "Model-generated answer"}
            </Badge>
          </TooltipTrigger>
          <TooltipContent className="max-w-sm">
            {extractive
              ? "Composed from the cited passages alone: no language model is configured for this deployment, so nothing is written that the evidence does not contain."
              : `Written by ${answer.model ?? "the configured model"} from the cited passages only.`}
          </TooltipContent>
        </Tooltip>
        <span className="ml-auto text-[11px] text-muted-foreground">
          {answer.timings.total_ms !== undefined ? `${answer.timings.total_ms} ms` : null}
        </span>
      </div>

      {verdict ? (
        <p className="text-xs font-medium">
          {verdict}
          <span className="ml-2 font-normal text-muted-foreground">
            {refused
              ? microcopyPlain("unsupported")
              : conflicted
                ? microcopyPlain("conflict")
                : microcopyPlain("evidenceFound")}
          </span>
        </p>
      ) : null}

      {/* Evidence → answer, stated as the three things that actually happened. */}
      <EvidenceFlowStrip
        passages={answer.citations.length}
        verified={verified}
        status={status.label}
        className="animate-fade-in"
      />

      {refused ? <RefusalCard answer={answer} onShowDetails={onShowDetails} /> : null}

      <AnswerText
        text={answer.answer_text}
        citations={answer.citations}
        className={cn("border-l-2 pl-4", refused ? "border-l-destructive/50" : "border-l-primary/60")}
      />

      {answer.conflicts.length > 0 ? (
        <div className="space-y-2 rounded-md border border-warning/35 bg-warning/5 p-3">
          <p className="flex items-center gap-2 text-xs font-medium text-warning">
            <TriangleAlert className="h-3.5 w-3.5" aria-hidden="true" />
            {MICROCOPY.conflict}{" "}
            {answer.conflicts.length === 1 ? "One conflict between sources" : `${answer.conflicts.length} conflicts between sources`}
          </p>
          <p className="text-[11px] text-muted-foreground">
            {microcopyPlain("conflict")} The records below disagree, and the answer states which one governs instead of
            averaging or choosing silently.
          </p>
          <ul className="space-y-2">
            {answer.conflicts.map((conflict, index) => (
              <li key={index} className="text-xs">
                <p className="font-medium">{conflict.description}</p>
                <p className="mt-0.5 text-muted-foreground">{conflict.resolution}</p>
                {conflict.citations.length > 0 ? (
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {conflict.citations.map((citation, citationIndex) => (
                      <CitationChip key={citation.chunk_id ?? citationIndex} citation={citation} />
                    ))}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {coverage.satisfied === false ? (
        <div className="flex items-start gap-2 rounded-md border border-destructive/35 bg-destructive/5 p-3 text-xs">
          <FileWarning className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
          <div>
            <p className="font-medium">The corpus does not cover everything this question asked for.</p>
            {(coverage.unsatisfied ?? []).length > 0 ? (
              <ul className="mt-1 space-y-0.5 text-muted-foreground">
                {(coverage.unsatisfied ?? []).map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      ) : null}

      {answer.degraded ? (
        <details className="rounded-md border p-3">
          <summary className="flex cursor-pointer items-center gap-2 text-xs font-medium">
            <Info className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
            Degraded mode: {answer.degradation_reasons.length} reason(s) reported by the pipeline
          </summary>
          <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
            {answer.degradation_reasons.map((reason, index) => (
              <li key={index} className="flex items-start gap-1.5">
                <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" />
                {reason}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      {basis.length > 0 ? (
        <dl className="grid gap-2 border-t pt-3 text-xs sm:grid-cols-2">
          {basis.map((entry) => (
            <div key={entry.label} className="flex gap-2">
              <dt className="w-20 shrink-0 text-muted-foreground">{entry.label}</dt>
              <dd className="min-w-0 font-medium">{entry.values.join(", ")}</dd>
            </div>
          ))}
          <div className="flex gap-2">
            <dt className="w-20 shrink-0 text-muted-foreground">Intent</dt>
            <dd className="min-w-0 font-medium">{titleCase(String(answer.plan.intent ?? "not reported"))}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-20 shrink-0 text-muted-foreground">Strategy</dt>
            <dd className="min-w-0 font-medium">{titleCase(String(answer.plan.method ?? "not reported"))}</dd>
          </div>
        </dl>
      ) : null}
    </article>
  );
}
