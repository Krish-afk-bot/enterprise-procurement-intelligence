import { BookOpen, Loader2 } from "lucide-react";

import { EvidenceItem } from "@/components/common/Evidence";
import type { Citation } from "@/lib/types";

/**
 * Retrieved passages shown while the answer is still being composed and
 * verified. This exists so the page is not blank during generation: the user can
 * already read the pages the system found, and the verified answer replaces the
 * "verifying" note when it arrives.
 */
export function EarlyEvidence({
  evidence,
  verifying,
}: {
  evidence: Citation[];
  verifying: boolean;
}) {
  if (evidence.length === 0) return null;
  return (
    <section
      aria-labelledby="early-evidence-heading"
      aria-busy={verifying}
      className="rounded-lg border bg-card"
    >
      <header className="flex flex-wrap items-center gap-2 border-b px-4 py-2.5">
        <h2 id="early-evidence-heading" className="flex items-center gap-2 text-xs font-semibold">
          <BookOpen className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
          Evidence retrieved
          <span className="font-normal text-muted-foreground">
            {evidence.length === 1 ? "1 passage" : `${evidence.length} passages`}
          </span>
        </h2>
        {verifying ? (
          <span className="ml-auto flex items-center gap-1.5 text-[11px] text-muted-foreground" role="status">
            <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
            Verifying the answer against these passages
          </span>
        ) : null}
      </header>
      <ol className="max-h-72 overflow-y-auto px-4 scrollbar-thin">
        {evidence.slice(0, 5).map((citation, index) => (
          <EvidenceItem
            key={citation.chunk_id ?? `${citation.document_id}-${index}`}
            citation={citation}
            index={index + 1}
            referenced={false}
          />
        ))}
      </ol>
    </section>
  );
}
