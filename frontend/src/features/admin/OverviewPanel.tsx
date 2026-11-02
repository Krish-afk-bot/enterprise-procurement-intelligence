import { useQuery } from "@tanstack/react-query";

import { ErrorState, LoadingRows } from "@/components/common/States";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

/** Workspace figures and the ingestion queue. */
export function OverviewPanel() {
  const stats = useQuery({ queryKey: ["admin-stats"], queryFn: api.stats });
  const indexing = useQuery({ queryKey: ["indexing"], queryFn: api.indexing, refetchInterval: 15_000 });
  const data = stats.data;

  if (stats.isError) return <ErrorState error={stats.error} onRetry={() => void stats.refetch()} />;

  return stats.isLoading || !data ? (
    <LoadingRows rows={6} />
  ) : (
    <>
      <section aria-labelledby="workspace-figures" className="rounded-lg border">
        <h2 id="workspace-figures" className="border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Workspace at a glance
        </h2>
        <dl className="grid gap-px bg-border sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: "Documents indexed", value: data.documents_indexed },
            { label: "Documents processing", value: data.documents_pending },
            { label: "Documents failed", value: data.documents_failed },
            { label: "Pages extracted", value: data.pages },
            { label: "Suppliers", value: data.suppliers },
            { label: "Contracts", value: data.contracts },
            { label: "Price rows", value: data.prices },
            { label: "Compliance certificates", value: data.compliance_certificates },
            { label: "Extracted tables", value: data.tables },
            { label: "Relationship nodes", value: data.graph_nodes },
            { label: "Relationship edges", value: data.graph_edges },
            { label: "Evaluation runs", value: data.evaluation_runs },
          ].map((figure) => (
            <div key={figure.label} className="bg-card p-4">
              <dt className="text-xs text-muted-foreground">{figure.label}</dt>
              <dd className="tnum mt-1 text-lg font-semibold tracking-tight">{formatNumber(figure.value)}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="rounded-lg border p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Ingestion queue</h2>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Uploads are queued and processed by a background worker outside the request path.
        </p>
        {indexing.isError ? (
          <ErrorState error={indexing.error} onRetry={() => void indexing.refetch()} />
        ) : (
          <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {(["queued", "running", "succeeded", "failed"] as const).map((key) => (
              <div key={key}>
                <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{key}</dt>
                <dd className="tnum mt-0.5 text-lg font-semibold">{formatNumber(Number(indexing.data?.[key] ?? 0))}</dd>
              </div>
            ))}
          </dl>
        )}
        {(indexing.data?.notes ?? []).length > 0 ? (
          <ul className="mt-3 space-y-1 border-t pt-3 text-[11px] text-muted-foreground">
            {(indexing.data?.notes ?? []).map((note, index) => (
              <li key={index}>{note}</li>
            ))}
          </ul>
        ) : null}
      </section>
    </>
  );
}
