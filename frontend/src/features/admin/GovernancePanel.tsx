import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { FileStack } from "lucide-react";

import { EmptyState, LoadingRows } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { cn, documentLifecycle, toneClasses } from "@/lib/utils";

/** Documents that are stuck, and the governance rules this build enforces. */
export function GovernancePanel() {
  const failed = useQuery({
    queryKey: ["documents", "admin-failed"],
    queryFn: () => api.documents({ status: "failed", limit: 50 }),
  });
  const processing = useQuery({
    queryKey: ["documents", "admin-processing"],
    queryFn: () => api.documents({ status: "processing", limit: 50 }),
  });

  return (
    <>
      <section className="rounded-lg border">
        <h2 className="border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Documents that need attention
        </h2>
        {failed.isLoading || processing.isLoading ? (
          <div className="p-4">
            <LoadingRows rows={3} />
          </div>
        ) : (failed.data?.items.length ?? 0) + (processing.data?.items.length ?? 0) === 0 ? (
          <div className="p-4">
            <EmptyState
              icon={FileStack}
              title="Nothing is stuck"
              description="No document is in a failed or in-flight processing state. Every uploaded file has finished processing."
            />
          </div>
        ) : (
          <Table>
            <caption className="sr-only">Documents that failed processing or are still being processed.</caption>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Document</TableHead>
                <TableHead scope="col">State</TableHead>
                <TableHead scope="col">Stage</TableHead>
                <TableHead scope="col">Recorded error</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...(failed.data?.items ?? []), ...(processing.data?.items ?? [])].map((document) => {
                const lifecycle = documentLifecycle(document);
                return (
                  <TableRow key={document.id}>
                    <TableCell>
                      <Link to={`/documents/${document.id}`} className="text-xs font-medium hover:underline">
                        {document.title || document.filename}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn("font-normal", toneClasses(lifecycle.tone))}>
                        {lifecycle.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{document.stage ?? "not reported"}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{document.error_message ?? "none recorded"}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </section>

      <section className="rounded-lg border p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Governance this build enforces</h2>
        <ul className="mt-2 space-y-1.5 text-xs text-muted-foreground">
          <li>
            <span className="font-medium text-foreground">Document access levels.</span> Every document carries an access
            level and every role has a ceiling; retrieval is filtered by tenant and by readable access level before a
            candidate can reach a model.
          </li>
          <li>
            <span className="font-medium text-foreground">Every metadata change is recorded.</span> Document uploads,
            detail edits, re-indexing and deletions are written to the audit log with the acting account and the
            before/after values.
          </li>
          <li>
            <span className="font-medium text-foreground">Versions are preserved.</span> Uploading a new version links the
            replaced document to its successor; the earlier version keeps its own pages, text and citations.
          </li>
          <li>
            <span className="font-medium text-foreground">Processing state is reported, not editable.</span> Status, stage
            and progress come from the ingestion run; a person cannot set them.
          </li>
          <li>
            <span className="font-medium text-foreground">No retention or legal-hold policy is implemented</span> in this
            build, and no archive action is exposed. Deletion removes the file and everything derived from it.
          </li>
        </ul>
      </section>
    </>
  );
}
