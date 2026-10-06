import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Shown wherever the platform holds no value. Never an empty cell, never a guess. */
export const NOT_RECORDED = "Not recorded";
export const NOT_FOUND_IN_DOCUMENTS = "Not found in indexed documents";

export function formatMoney(value: number | null | undefined, currency = "USD"): string {
  if (value === null || value === undefined) return NOT_RECORDED;
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${currency} ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return NOT_RECORDED;
  return value.toLocaleString();
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "Not evaluated";
  return `${(value * 100).toFixed(digits)}%`;
}

/** A measured ratio, used for metrics that are already fractions. */
export function formatRatio(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined) return NOT_RECORDED;
  return value.toFixed(digits);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return NOT_RECORDED;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return NOT_RECORDED;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatBytes(value: number | null | undefined): string {
  if (!value) return NOT_RECORDED;
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

export function truncate(value: string, length = 160): string {
  if (value.length <= length) return value;
  return `${value.slice(0, length - 1)}…`;
}

export function titleCase(value: string | null | undefined): string {
  if (!value) return NOT_RECORDED;
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

/** 1 -> "1 document", 2 -> "2 documents". */
export function plural(count: number, singular: string, plural?: string): string {
  return `${count.toLocaleString()} ${count === 1 ? singular : (plural ?? `${singular}s`)}`;
}

/**
 * True for an identifier this deployment actually issues.
 *
 * Records are keyed as `<prefix>_<32 hex characters>` (for example
 * `sup_2f0170c53c784d55a48a5fd49a6b070b`), and a few older rows carry a
 * hyphenated UUID instead. Both forms address a real record, so both are
 * accepted; anything else has no page to link to.
 */
export function isRecordId(value: string): boolean {
  return (
    /^[a-z]+_[0-9a-f]{32}$/i.test(value) ||
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
  );
}

/** @deprecated Use {@link isRecordId}; kept for callers that still pass a UUID. */
export const isUuid = isRecordId;

export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

/**
 * Colour is a supporting signal only. Every caller pairs a tone with a written
 * label, so the meaning never depends on colour alone.
 */
export function toneClasses(tone: StatusTone): string {
  switch (tone) {
    case "success":
      return "border-success/35 bg-success/10 text-success";
    case "warning":
      return "border-warning/35 bg-warning/10 text-warning";
    case "danger":
      return "border-destructive/35 bg-destructive/10 text-destructive";
    case "info":
      return "border-info/35 bg-info/10 text-info";
    default:
      return "border-border bg-muted text-muted-foreground";
  }
}

export function toneDot(tone: StatusTone): string {
  switch (tone) {
    case "success":
      return "bg-success";
    case "warning":
      return "bg-warning";
    case "danger":
      return "bg-destructive";
    case "info":
      return "bg-info";
    default:
      return "bg-muted-foreground/60";
  }
}

/**
 * Answer verification outcomes reported by the pipeline. These four words are
 * the vocabulary the product uses everywhere for how much the evidence
 * supports an answer; nothing else may be shown in their place.
 */
export function answerStatus(status: string): { label: string; tone: StatusTone; meaning: string } {
  switch (status) {
    case "supported":
      return {
        label: "SUPPORTED",
        tone: "success",
        meaning: "Every claim in the answer is backed by retrieved evidence.",
      };
    case "partial":
      return {
        label: "PARTIAL EVIDENCE",
        tone: "info",
        meaning: "Some claims are backed by evidence; the rest were dropped or flagged.",
      };
    case "conflicting":
      return {
        label: "CONFLICTING EVIDENCE",
        tone: "warning",
        meaning:
          "The corpus contains records that disagree. The answer states both values and which one governs.",
      };
    case "insufficient_evidence":
      return {
        label: "UNABLE TO VERIFY",
        tone: "danger",
        meaning:
          "Searched and read, but the corpus holds no evidence for this. The platform refused instead of guessing.",
      };
    case "error":
      return { label: "ERROR", tone: "danger", meaning: "The query failed before verification finished." };
    default:
      return { label: titleCase(status), tone: "neutral", meaning: "" };
  }
}

/**
 * Plain-language names for the pipeline nodes the backend reports while a query
 * runs. The raw node identifier stays available for the technical details.
 */
export function pipelineStepLabel(node: string): string {
  switch (node) {
    case "understand":
      return "Read the question";
    case "plan":
      return "Planned the retrieval";
    case "retrieve":
      return "Searched the indexed documents";
    case "structured":
      return "Checked recorded price data";
    case "graph":
      return "Traversed supplier relationships";
    case "vision":
      return "Read page imagery";
    case "evaluate":
      return "Judged whether the evidence is sufficient";
    case "rewrite":
      return "Rewrote the question and searched again";
    case "generate":
      return "Composed the answer from evidence";
    case "verify":
      return "Checked the answer against the evidence";
    case "finalize":
      return "Prepared the answer";
    default:
      return titleCase(node);
  }
}

export function evidenceLevel(level: string): { label: string; tone: StatusTone } {
  switch (level) {
    case "strong":
      return { label: "Strong evidence", tone: "success" };
    case "moderate":
      return { label: "Moderate evidence", tone: "info" };
    case "limited":
      return { label: "Limited evidence", tone: "warning" };
    case "none":
      return { label: "No evidence", tone: "danger" };
    default:
      return { label: titleCase(level), tone: "neutral" };
  }
}

export function documentStatus(status: string): { label: string; tone: StatusTone } {
  switch (status) {
    case "indexed":
      return { label: "Indexed", tone: "success" };
    case "failed":
      return { label: "Failed", tone: "danger" };
    case "processing":
    case "running":
      return { label: "Indexing", tone: "info" };
    case "queued":
    case "pending":
      return { label: "Queued", tone: "neutral" };
    default:
      return { label: titleCase(status), tone: "neutral" };
  }
}

/**
 * Document types the backend records (`DOCUMENT_TYPES`), in the words a
 * procurement team uses. An unlisted value is shown as recorded rather than
 * mapped onto a category that does not exist.
 */
export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  contract: "Contract",
  amendment: "Amendment",
  pricing_agreement: "Pricing agreement",
  pricing_schedule: "Pricing schedule",
  compliance_certificate: "Compliance certificate",
  purchase_order: "Purchase order",
  invoice: "Invoice",
  specification: "Specification",
  tender: "Tender",
  supplier_record: "Supplier record",
  other: "Other",
};

export function documentTypeLabel(value: string | null | undefined): string {
  if (!value) return NOT_RECORDED;
  return DOCUMENT_TYPE_LABELS[value] ?? titleCase(value);
}

/** Suppliers, contracts, documents and certificates in the demo corpus. */
export const DEMO_CORPUS_LABEL = "demo corpus";

/** A term is "expiring soon" inside this window. */
export const EXPIRING_SOON_DAYS = 90;

export interface DocumentLifecycle {
  label: string;
  tone: StatusTone;
  /** Which stored values produced the label. Shown to the user, never hidden. */
  basis: string;
}

function daysUntil(value: string, today: Date): number {
  const target = new Date(value);
  if (Number.isNaN(target.getTime())) return Number.NaN;
  return Math.ceil((target.getTime() - today.getTime()) / 86_400_000);
}

/** Whole days from today until a recorded date, or null when there is none. */
export function daysUntilDate(value: string | null | undefined, today: Date = new Date()): number | null {
  if (!value) return null;
  const days = daysUntil(value, today);
  return Number.isNaN(days) ? null : days;
}

/**
 * Audit actions in the words a procurement team reads. The raw action name stays
 * available in the administration area for anyone who needs it.
 */
export const ACTIVITY_LABELS: Record<string, string> = {
  "auth.login": "Signed in",
  "auth.login_failed": "Sign-in failed",
  "auth.logout": "Signed out",
  "auth.register": "Account created",
  "query.run": "Question answered",
  "document.upload": "Document uploaded",
  "document.read": "Document opened",
  "document.delete": "Document deleted",
  "document.reindex": "Document re-indexed",
  "document.update": "Document details updated",
  "compare.run": "Comparison run",
  "evaluation.run": "Search quality evaluation run",
  "admin.config": "Configuration changed",
  "security.access_denied": "Access denied",
  "security.scope_violation": "Out-of-scope access blocked",
  "security.prompt_injection_detected": "Instruction-like text detected in a document",
};

export function activityLabel(action: string): string {
  return ACTIVITY_LABELS[action] ?? titleCase(action.replace(/\./g, " "));
}

/**
 * The state of a document in business words.
 *
 * Derived only from values the backend stores: the ingestion status, whether a
 * newer version replaced the row, and the recorded effective and expiry dates.
 * Where the dates are absent the honest answer is "Not available" — the label
 * never claims a document is active when nothing records its term.
 */
export function documentLifecycle(
  document: {
    status: string;
    superseded_by_id?: string | null;
    effective_date?: string | null;
    expiry_date?: string | null;
  },
  today: Date = new Date(),
): DocumentLifecycle {
  const status = (document.status || "").toLowerCase();
  if (status === "failed" || status === "needs_review") {
    return {
      label: "Needs attention",
      tone: "danger",
      basis: `Ingestion reported the status ${status}.`,
    };
  }
  if (["queued", "uploaded", "processing", "running", "pending"].includes(status)) {
    return {
      label: "Processing",
      tone: "info",
      basis: "The document is still being read and indexed.",
    };
  }
  if (document.superseded_by_id) {
    return {
      label: "Superseded",
      tone: "neutral",
      basis: "A newer version of this document has been uploaded.",
    };
  }

  const { effective_date: effective, expiry_date: expiry } = document;
  if (!effective && !expiry) {
    return {
      label: "Not available",
      tone: "neutral",
      basis: "No effective date or expiry date is recorded for this document.",
    };
  }
  if (effective) {
    const start = daysUntil(effective, today);
    if (!Number.isNaN(start) && start > 0) {
      return {
        label: "Scheduled",
        tone: "info",
        basis: `The recorded effective date is ${start} day(s) away.`,
      };
    }
  }
  if (expiry) {
    const remaining = daysUntil(expiry, today);
    if (!Number.isNaN(remaining)) {
      if (remaining < 0) {
        return {
          label: "Expired",
          tone: "warning",
          basis: `The recorded expiry date passed ${Math.abs(remaining)} day(s) ago.`,
        };
      }
      if (remaining <= EXPIRING_SOON_DAYS) {
        return {
          label: "Expires soon",
          tone: "warning",
          basis: `The recorded expiry date is ${remaining} day(s) away.`,
        };
      }
    }
    return {
      label: "Active",
      tone: "success",
      basis: "The recorded term covers today and the expiry date is more than 90 days away.",
    };
  }
  return {
    label: "Active",
    tone: "success",
    basis: "The recorded effective date has passed and no expiry date is recorded.",
  };
}

/**
 * Plain-language reason a passage surfaced, for the default search view.
 * The retriever's own vocabulary belongs in the technical details.
 */
export function matchReasonPlain(token: string): string {
  switch (token) {
    case "dense":
      return "closely related wording";
    case "sparse":
    case "bm25":
      return "the exact words in the question";
    case "rerank":
      return "ranked highest against the question";
    case "fused":
    case "rrf":
      return "found by more than one search";
    case "graph":
      return "a recorded relationship";
    case "sql":
      return "a recorded price row";
    default:
      return titleCase(token);
  }
}

/** Human wording for the retriever(s) that surfaced a chunk. */
export function matchReason(token: string): string {
  switch (token) {
    case "dense":
      return "semantic similarity";
    case "sparse":
    case "bm25":
      return "exact term match";
    case "rerank":
      return "cross-encoder rerank";
    case "fused":
    case "rrf":
      return "reciprocal rank fusion";
    case "graph":
      return "knowledge graph relation";
    case "sql":
      return "structured pricing query";
    default:
      return titleCase(token);
  }
}

/** Highlight-free passage preview that never exceeds a couple of lines. */
export function passagePreview(text: string, length = 220): string {
  const collapsed = text.replace(/\s+/g, " ").trim();
  return truncate(collapsed, length);
}
