import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { LoadingRows } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/utils";

/** Answer counts and the execution trace of recent questions. */
export function QualityPanel() {
  const stats = useQuery({ queryKey: ["admin-stats"], queryFn: api.stats });
  const traces = useQuery({ queryKey: ["traces"], queryFn: () => api.traces({ limit: 25 }) });
  const data = stats.data;

  return (
    <>
      <section className="rounded-lg border p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Questions asked</h2>
        <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Questions run</dt>
            <dd className="tnum mt-0.5 text-lg font-semibold">{formatNumber(data?.queries_total ?? 0)}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Answered with evidence</dt>
            <dd className="tnum mt-0.5 text-lg font-semibold">
              {formatNumber((data?.queries_total ?? 0) - (data?.queries_insufficient_evidence ?? 0))}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Unable to verify</dt>
            <dd className="tnum mt-0.5 text-lg font-semibold">{formatNumber(data?.queries_insufficient_evidence ?? 0)}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Evaluation runs</dt>
            <dd className="tnum mt-0.5 text-lg font-semibold">{formatNumber(data?.evaluation_runs ?? 0)}</dd>
          </div>
        </dl>
        <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
          Answer and retrieval quality are only reported as runs of the evaluation suite over the labelled question
          set; they are never estimated. Open the{" "}
          <Link to="/evaluation" className="underline hover:text-foreground">
            Search quality
          </Link>{" "}
          view for the per-experiment results.
        </p>
      </section>

      <section className="rounded-lg border p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Query execution traces</h2>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Each step the pipeline took for a question, with the node that produced it. This is the same path the answer
          view summarises as &ldquo;how the answer was verified&rdquo;.
        </p>
        <div className="mt-3 space-y-3">
          {traces.isLoading ? <LoadingRows rows={3} /> : null}
          {(traces.data?.items ?? []).map((trace) => (
            <article key={trace.id} className="rounded-lg border p-3">
              <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                <Badge variant="outline" className="font-mono font-normal">
                  query {String(trace.query_id ?? trace.id).slice(0, 8)}
                </Badge>
                <span className="tnum">{trace.duration_ms !== null ? `${trace.duration_ms} ms` : "not timed"}</span>
                <span>{trace.iterations ?? 0} iteration(s)</span>
                <span className="ml-auto">{formatDateTime(trace.created_at)}</span>
              </div>
              <ol className="mt-2 space-y-1">
                {(trace.events ?? []).map((event, index) => (
                  <li key={index} className="grid grid-cols-[auto_minmax(0,1fr)] gap-2 text-[11px]">
                    <span className="h-fit rounded border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                      {event.node}
                    </span>
                    <span className="min-w-0">
                      <span className="font-medium">{event.event}</span>
                      {event.detail ? <span className="text-muted-foreground"> {event.detail}</span> : null}
                    </span>
                  </li>
                ))}
              </ol>
            </article>
          ))}
          {traces.data && traces.data.items.length === 0 ? (
            <p className="rounded-lg border border-dashed p-4 text-xs text-muted-foreground">
              No trace has been recorded yet. A trace is written for each question the pipeline processes.
            </p>
          ) : null}
        </div>
      </section>
    </>
  );
}
