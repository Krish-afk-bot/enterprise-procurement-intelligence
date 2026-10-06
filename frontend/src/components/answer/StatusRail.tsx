import { useState } from "react";
import { ChevronDown, Loader2 } from "lucide-react";

import { MICROCOPY } from "@/lib/microcopy";
import type { StreamEvent } from "@/lib/types";
import { cn, pipelineStepLabel } from "@/lib/utils";

type PipelineEvent = NonNullable<StreamEvent["event"]>;

const VISIBLE_STEPS = 4;

/**
 * What the pipeline is doing, in the reader's language. The backend reports a
 * node name and a sentence for each stage; this shows the sentence first and
 * keeps the node identifier for the technical details rather than leading with
 * `retrieve`-style identifiers.
 */
export function StatusRail({ events, streaming }: { events: PipelineEvent[]; streaming: boolean }) {
  const [expanded, setExpanded] = useState(false);
  if (!streaming && events.length === 0) return null;

  const shown = expanded ? events : events.slice(-VISIBLE_STEPS);
  const hidden = events.length - shown.length;

  return (
    <section aria-label="Pipeline status" aria-live="polite" className="rounded-md border bg-muted/30 px-3 py-2.5">
      {streaming ? (
        <p className="flex items-center gap-2 text-xs font-medium">
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          {MICROCOPY.readingDocuments}
          <span className="font-normal text-muted-foreground">Searching the workspace and checking the evidence</span>
        </p>
      ) : (
        <p className="text-xs font-medium">How this answer was produced</p>
      )}

      {events.length > 0 ? (
        <>
          {hidden > 0 ? (
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="mt-1.5 flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
            >
              <ChevronDown className="h-3 w-3" aria-hidden="true" />
              {hidden} earlier step{hidden === 1 ? "" : "s"}
            </button>
          ) : null}
          <ol className="mt-2 space-y-1.5">
            {shown.map((event, index) => (
              <li key={`${event.node}-${index}`} className="grid grid-cols-[auto_minmax(0,1fr)] gap-2 text-[11px]">
                <span
                  aria-hidden="true"
                  className={cn(
                    "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                    index === shown.length - 1 && streaming ? "bg-primary" : "bg-muted-foreground/50",
                  )}
                />
                <span className="min-w-0">
                  <span className="font-medium">{pipelineStepLabel(event.node)}</span>
                  {event.detail ? <span className="text-muted-foreground"> — {event.detail}</span> : null}
                </span>
              </li>
            ))}
          </ol>
        </>
      ) : null}
    </section>
  );
}
