import { Link } from "react-router-dom";
import { CheckCircle2, ExternalLink, ShieldAlert, ShieldQuestion } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { Citation } from "@/lib/types";
import { NOT_RECORDED, cn, passagePreview, titleCase } from "@/lib/utils";

/** Plain wording for the detector's pattern names, used on flagged passages. */
const INJECTION_PATTERN_LABELS: Record<string, string> = {
  instruction_override: "tells the reader to disregard earlier instructions",
  system_impersonation: "impersonates a system or assistant role",
  role_switch: "tries to reassign the assistant's role",
  secret_exfiltration: "asks for a system prompt, key or password",
  tool_abuse: "asks for a tool, function or shell to be run",
  policy_override: "claims the rules no longer apply",
  fabricated_citation: "instructs how a citation must be reported",
};

/**
 * Untrusted-content notice for a passage that reads like an instruction.
 * The passage stays evidence; the notice says plainly that it was not obeyed.
 */
function UntrustedContentNotice({ patterns }: { patterns: string[] }) {
  const described = patterns.map((pattern) => INJECTION_PATTERN_LABELS[pattern] ?? titleCase(pattern));
  return (
    <div className="mt-2 rounded-md border border-warning/45 bg-warning/5 p-2.5">
      <p className="flex items-center gap-1.5 text-[11px] font-semibold tracking-wide text-warning">
        <ShieldAlert className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        UNTRUSTED DOCUMENT CONTENT
      </p>
      <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
        This passage contains text addressed at an assistant rather than procurement information
        {described.length > 0 ? ` — it ${described.join("; it ")}` : ""}. It was retrieved as evidence and recorded
        here; it was never executed as an instruction.
      </p>
    </div>
  );
}

/** Every citation resolves to the page it came from. */
export function citationHref(citation: Citation): string | null {
  if (!citation.document_id) return null;
  const params = new URLSearchParams();
  if (citation.page) params.set("page", String(citation.page));
  if (citation.chunk_id) params.set("chunk", citation.chunk_id);
  const query = params.toString();
  return `/documents/${citation.document_id}${query ? `?${query}` : ""}`;
}

export function citationLabel(citation: Citation, index?: number): string {
  const name = citation.document_name ?? citation.label ?? "Document";
  const page = citation.page ? `, p.${citation.page}` : "";
  return `${index !== undefined ? `[${index}] ` : ""}${name}${page}`;
}

/** Compact, keyboard-reachable citation chip used inside answers and tables. */
export function CitationChip({ citation, index }: { citation: Citation; index?: number }) {
  const href = citationHref(citation);
  const label = citationLabel(citation, index);
  const inner = (
    <>
      <span className="truncate">{citation.document_name ?? citation.label ?? "Document"}</span>
      {citation.page ? <span className="tnum text-muted-foreground">p.{citation.page}</span> : null}
      <ExternalLink className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden="true" />
    </>
  );

  if (!href) {
    return (
      <span className="inline-flex max-w-full items-center gap-1 rounded border border-border bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground">
        {label}
      </span>
    );
  }

  return (
    <Link
      to={href}
      title={`Open ${label}`}
      className="inline-flex max-w-full items-center gap-1.5 rounded border border-border bg-background px-1.5 py-0.5 text-[11px] text-foreground transition-colors duration-micro hover:border-primary/50 hover:bg-primary/5"
    >
      {inner}
    </Link>
  );
}

/** Full evidence row: who it came from, where, and what it says. */
export function EvidenceItem({
  citation,
  index,
  className,
  referenced,
}: {
  citation: Citation;
  index: number;
  className?: string;
  /** False when the answer text never quotes this marker. Undefined = unknown. */
  referenced?: boolean;
}) {
  const href = citationHref(citation);
  const verified = citation.verified;

  return (
    <li className={cn("border-b border-border/70 py-3 last:border-0", className)}>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="tnum rounded bg-muted px-1.5 py-0.5 font-medium">[{index}]</span>
        <span className="font-medium">{citation.document_name ?? citation.label ?? "Document"}</span>
        <span className="text-muted-foreground">{citation.page ? `page ${citation.page}` : "page not recorded"}</span>
        {citation.section ? <span className="text-muted-foreground">{citation.section}</span> : null}
        {citation.clause ? <span className="text-muted-foreground">{citation.clause}</span> : null}
        <Badge variant="outline" className="ml-auto font-normal">
          {titleCase(citation.evidence_type)}
        </Badge>
        {verified ? (
          <Badge variant="outline" className="gap-1 border-success/35 font-normal text-success">
            <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
            verified
          </Badge>
        ) : (
          <Badge variant="outline" className="gap-1 border-warning/35 font-normal text-warning">
            <ShieldQuestion className="h-3 w-3" aria-hidden="true" />
            not re-verified
          </Badge>
        )}
      </div>
      {referenced === false ? (
        <p className="mt-1 text-[10px] text-muted-foreground">
          Read as context for this question; the answer text does not quote this marker.
        </p>
      ) : null}
      <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{passagePreview(citation.snippet, 320)}</p>
      {citation.injection?.suspicious ? <UntrustedContentNotice patterns={citation.injection.patterns} /> : null}
      <div className="mt-1.5 flex flex-wrap items-center gap-3 text-[11px]">
        {href ? (
          <Link to={href} className="inline-flex items-center gap-1 font-medium text-primary hover:underline">
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
            Open cited page
          </Link>
        ) : (
          <span className="text-muted-foreground">No source document is attached to this citation.</span>
        )}
        {citation.source_uri ? <span className="truncate text-muted-foreground">{citation.source_uri}</span> : null}
        <span className="tnum text-muted-foreground">
          {citation.score !== null ? `retrieval score ${citation.score.toFixed(3)}` : "score not reported"}
        </span>
      </div>
    </li>
  );
}

/** A pointer to a page in a specific document, used by price and clause tables. */
export function SourceLink({
  documentId,
  page,
  chunkId,
  children,
}: {
  documentId: string | null | undefined;
  page?: number | null;
  chunkId?: string | null;
  children?: React.ReactNode;
}) {
  if (!documentId) return <span className="text-xs italic text-muted-foreground">{NOT_RECORDED}</span>;
  const params = new URLSearchParams();
  if (page) params.set("page", String(page));
  if (chunkId) params.set("chunk", chunkId);
  const query = params.toString();
  return (
    <Link
      to={`/documents/${documentId}${query ? `?${query}` : ""}`}
      className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
    >
      {children ?? (page ? `Page ${page}` : "Open source")}
      <ExternalLink className="h-3 w-3" aria-hidden="true" />
    </Link>
  );
}
