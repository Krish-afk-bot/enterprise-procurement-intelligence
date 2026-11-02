import { useQuery } from "@tanstack/react-query";

import { ErrorState, LoadingRows } from "@/components/common/States";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { activityLabel, formatDateTime } from "@/lib/utils";

/** The audit log of recorded actions. */
export function ActivityPanel() {
  const audit = useQuery({ queryKey: ["audit"], queryFn: () => api.audit({ limit: 50 }) });

  return (
    <section className="rounded-lg border">
      <h2 className="border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Recorded activity
      </h2>
      <p className="px-4 py-2.5 text-[11px] leading-relaxed text-muted-foreground">
        Questions, uploads, document reads, detail edits, comparisons and evaluation runs are recorded with the actor,
        the resource and the request id. The raw action name is kept beside the plain-language label.
      </p>
      {audit.isError ? (
        <div className="p-4">
          <ErrorState error={audit.error} onRetry={() => void audit.refetch()} />
        </div>
      ) : audit.isLoading ? (
        <div className="p-4">
          <LoadingRows rows={6} />
        </div>
      ) : (
        <Table>
          <caption className="sr-only">Recorded actions in this workspace.</caption>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">When</TableHead>
              <TableHead scope="col">What happened</TableHead>
              <TableHead scope="col">Resource</TableHead>
              <TableHead scope="col">Outcome</TableHead>
              <TableHead scope="col">Request</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(audit.data?.items ?? []).map((entry) => (
              <TableRow key={entry.id}>
                <TableCell className="text-xs text-muted-foreground">{formatDateTime(entry.created_at)}</TableCell>
                <TableCell className="text-xs font-medium">
                  {activityLabel(entry.action)}
                  <span className="ml-2 font-mono text-[10px] text-muted-foreground">{entry.action}</span>
                </TableCell>
                <TableCell className="text-xs">
                  {entry.resource_type ?? "not recorded"}
                  {entry.resource_id ? (
                    <span className="ml-1 font-mono text-[11px] text-muted-foreground">{entry.resource_id.slice(0, 8)}</span>
                  ) : null}
                </TableCell>
                <TableCell className="text-xs">{entry.outcome ?? "success"}</TableCell>
                <TableCell className="font-mono text-[10px] text-muted-foreground">
                  {entry.request_id ? entry.request_id.slice(0, 12) : "not recorded"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}
