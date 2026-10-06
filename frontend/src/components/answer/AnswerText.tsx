import { Fragment } from "react";
import { Link } from "react-router-dom";

import { citationHref } from "@/components/common/Evidence";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Markers are written as `[3]` by the answer composer and index `citations`. */
const MARKER = /\[(\d{1,3})\]/g;

/** Section labels the composer emits; anything else is prose. */
const SECTION_LABELS = new Set([
  "answer",
  "structured findings",
  "document evidence",
  "evidence",
  "verification",
]);

function isSectionLine(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("•")) return false;
  if (trimmed.endsWith(":")) return true;
  return SECTION_LABELS.has(trimmed.replace(/[.:]$/, "").toLowerCase());
}

/**
 * Renders an answer as it was composed, with one improvement: every `[n]`
 * marker becomes a link to the page that marker stands for. The reference is
 * therefore usable directly from the answer, not only from the evidence list.
 */
function renderLine(line: string, citations: Citation[], key: string) {
  const parts = line.split(MARKER);
  return parts.map((part, index) => {
    // Captured marker groups land on odd indices.
    if (index % 2 === 1) {
      const marker = Number(part);
      const citation = citations[marker - 1];
      const href = citation ? citationHref(citation) : null;
      const title = citation
        ? `${citation.document_name ?? "Document"}${citation.page ? `, page ${citation.page}` : ""}`
        : `No citation [${part}] in this answer`;
      if (!href) {
        return (
          <span key={`${key}-${index}`} className="tnum text-muted-foreground" title={title}>
            [{part}]
          </span>
        );
      }
      return (
        <Link
          key={`${key}-${index}`}
          to={href}
          title={`Open ${title}`}
          className="tnum mx-0.5 rounded border border-primary/30 bg-primary/5 px-1 py-0.5 align-baseline text-[10px] font-semibold text-primary transition-colors duration-micro hover:border-primary/60 hover:bg-primary/10"
        >
          [{part}]
        </Link>
      );
    }
    return <Fragment key={`${key}-${index}`}>{part}</Fragment>;
  });
}

export function AnswerText({ text, citations, className }: { text: string; citations: Citation[]; className?: string }) {
  const lines = text.split("\n");
  return (
    <div className={cn("prose-answer", className)}>
      {lines.map((line, index) => {
        const key = `line-${index}`;
        const trimmed = line.trim();
        if (!trimmed) return <div key={key} className="h-2" aria-hidden="true" />;
        if (isSectionLine(trimmed)) {
          return (
            <h3 key={key} className="mt-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              {trimmed.replace(/:$/, "")}
            </h3>
          );
        }
        const bullet = /^[•\-*]\s+/.test(trimmed);
        return (
          <p key={key} className={bullet ? "pl-3.5 text-xs leading-relaxed" : "text-sm leading-relaxed"}>
            {renderLine(line, citations, key)}
          </p>
        );
      })}
    </div>
  );
}
