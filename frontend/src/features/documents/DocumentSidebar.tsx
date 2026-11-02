import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { History, ImageOff, Table2 } from "lucide-react";

import { ErrorState, LoadingRows } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DetailRow } from "@/features/documents/DetailRow";
import { EditDetailsDialog } from "@/features/documents/EditDetailsDialog";
import { api } from "@/lib/api";
import { MICROCOPY } from "@/lib/microcopy";
import type { DocumentDetail } from "@/lib/types";
import {
  NOT_RECORDED,
  cn,
  documentLifecycle,
  documentTypeLabel,
  formatBytes,
  formatDate,
  formatDateTime,
  plural,
  titleCase,
  toneClasses,
} from "@/lib/utils";

/** The left column of the document page: pages, versions and recorded details. */
export function DocumentSidebar({
  data,
  page,
  goToPage,
  canEdit,
}: {
  data: DocumentDetail;
  page: number;
  goToPage: (page: number) => void;
  canEdit: boolean;
}) {
  const versions = useQuery({
    queryKey: ["document-versions", data.id],
    queryFn: () => api.documentVersions(data.id),
    enabled: Boolean(data.id),
  });
  const pages = data.pages;
  const versionRows = versions.data ?? [];
  const activeVersion = versionRows.find((row) => row.is_current) ?? null;
  const lifecycle = documentLifecycle(data);

  return (
    <nav aria-label="Document pages" className="min-w-0 space-y-5">
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {plural(pages.length, "page")}
        </h2>
        <ul className="mt-2 max-h-[280px] space-y-0.5 overflow-y-auto pr-1 scrollbar-thin lg:max-h-[calc(100vh-420px)]">
          {pages.map((item) => (
            <li key={item.page_number}>
              <button
                type="button"
                onClick={() => goToPage(item.page_number)}
                aria-current={item.page_number === page ? "true" : undefined}
                className={cn(
                  "flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-xs transition-colors duration-micro",
                  item.page_number === page ? "bg-primary/10 font-medium text-primary" : "hover:bg-accent",
                )}
              >
                <span className="tnum">Page {item.page_number}</span>
                <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                  {item.tables.length > 0 ? <Table2 className="h-3 w-3" aria-label={`${item.tables.length} tables`} /> : null}
                  {item.is_scanned ? <ImageOff className="h-3 w-3" aria-label="scanned page" /> : null}
                </span>
              </button>
            </li>
          ))}
          {pages.length === 0 ? <li className="px-2 text-[11px] text-muted-foreground">No page has been stored yet.</li> : null}
        </ul>
      </div>

      <section aria-labelledby="version-history-heading">
        <h2 id="version-history-heading" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <History className="h-3.5 w-3.5" aria-hidden="true" />
          Version history
        </h2>
        {/* Older versions sit behind the current one, so the pile shows at a
            glance how many revisions a document has been through. */}
        {versions.isError ? (
          <ErrorState error={versions.error} onRetry={() => void versions.refetch()} />
        ) : versions.isLoading ? (
          <LoadingRows rows={2} />
        ) : (
          <ol className="mt-2 space-y-2 text-xs">
            {versionRows.map((row, index) => (
              <li
                key={row.id}
                className={cn(
                  "stack-layers rounded-md border p-2",
                  row.is_current ? "stack-layers-current" : null,
                  row.id === data.id ? "border-primary/40 bg-primary/5" : null,
                )}
                style={index === 0 ? undefined : { marginRight: `${Math.min(index, 3) * 4}px` }}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">v{row.version ?? 1}</span>
                  {row.is_current ? (
                    <Badge variant="outline" className={cn("font-normal", toneClasses("success"))}>
                      Current
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="font-normal text-muted-foreground">
                      Superseded
                    </Badge>
                  )}
                  {row.id === data.id ? (
                    <span className="text-[11px] text-muted-foreground">you are viewing this one</span>
                  ) : (
                    <Link to={`/documents/${row.id}`} className="text-[11px] font-medium text-primary hover:underline">
                      Open
                    </Link>
                  )}
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Updated {formatDateTime(row.updated_at ?? row.created_at)} · {row.revision_label ?? "no revision label"}
                </p>
                <p className="text-[11px] text-muted-foreground">
                  {formatDate(row.effective_date)} to {formatDate(row.expiry_date)}
                </p>
              </li>
            ))}
          </ol>
        )}
        <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
          {versionRows.length <= 1 ? `${MICROCOPY.singleVersion} ` : ""}
          {activeVersion
            ? `v${activeVersion.version ?? 1} is the version that currently governs.`
            : "No version is marked current."}{" "}
          Earlier versions keep their own pages, text and citations, so evidence already cited from them stays valid.
        </p>
      </section>

      <section aria-labelledby="document-information-heading">
        <h2 id="document-information-heading" className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Document information
        </h2>
        <dl className="mt-2 space-y-1.5 text-xs">
          <DetailRow label="Document type" value={documentTypeLabel(data.document_type)} />
          <DetailRow label="Supplier" value={data.supplier_name ?? "Not available"} />
          <DetailRow label="Contract" value={data.contract_number ?? "Not available"} />
          <DetailRow label="Status" value={lifecycle.label} />
          <DetailRow label="Effective" value={formatDate(data.effective_date)} />
          <DetailRow label="Expiry" value={formatDate(data.expiry_date)} />
          <DetailRow label="Owner" value={data.uploaded_by_name ?? NOT_RECORDED} />
          <DetailRow label="Access" value={titleCase(data.access_level)} />
          <DetailRow label="Revision label" value={data.revision_label ?? NOT_RECORDED} />
          <DetailRow label="Size" value={formatBytes(data.size_bytes)} />
          <DetailRow label="Added" value={formatDateTime(data.created_at)} />
          <DetailRow label="Last updated" value={formatDateTime(data.updated_at)} />
        </dl>
        {canEdit ? (
          <div className="mt-2">
            <EditDetailsDialog document={data} trigger={<Button variant="outline" size="sm">Edit details</Button>} />
          </div>
        ) : null}
      </section>
    </nav>
  );
}
