import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpDown, FileStack, Info, Upload } from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingRows } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogTrigger } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  BUSINESS_STATES,
  DocumentFilters,
  type DocumentFilterValues,
} from "@/features/documents/DocumentFilters";
import { PIPELINE_ORDER, stageLabel } from "@/features/documents/stages";
import { SortableHead, sortLabel, type SortKey } from "@/features/documents/SortableHead";
import { UploadDocumentDialog } from "@/features/documents/UploadDocumentDialog";
import { api } from "@/lib/api";
import { useMood } from "@/lib/useMood";
import { MICROCOPY, microcopyPlain } from "@/lib/microcopy";
import { useAuth } from "@/store/auth";
import {
  cn,
  documentLifecycle,
  documentTypeLabel,
  formatDate,
  formatDateTime,
  toneClasses,
} from "@/lib/utils";

/** Every label `documentLifecycle` can produce, in the order a reader scans them. */
const LIFECYCLE_ORDER: string[] = [
  "Active",
  "Expires soon",
  "Expired",
  "Scheduled",
  "Superseded",
  "Processing",
  "Needs attention",
  "Not available",
];

export function DocumentsPage() {
  const user = useAuth((state) => state.user);
  const canUpload = Boolean(user?.permissions?.includes("documents:write"));
  const [filters, setFilters] = useState<DocumentFilterValues>({
    search: "",
    documentType: "all",
    supplierId: "all",
    businessState: "all",
    includeSynthetic: true,
  });
  const [sortKey, setSortKey] = useState<SortKey>("updated");
  const [sortAscending, setSortAscending] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  const documents = useQuery({
    queryKey: ["documents", filters.search, filters.documentType, filters.supplierId, filters.includeSynthetic],
    queryFn: () =>
      api.documents({
        search: filters.search || undefined,
        document_type: filters.documentType === "all" ? undefined : filters.documentType,
        supplier_id: filters.supplierId === "all" ? undefined : filters.supplierId,
        include_synthetic: filters.includeSynthetic,
        limit: 200,
      }),
    refetchInterval: 8_000,
  });
  const suppliers = useQuery({ queryKey: ["suppliers", "documents-filter"], queryFn: () => api.suppliers({ limit: 100 }) });
  const items = useMemo(() => documents.data?.items ?? [], [documents.data]);

  useMood(documents.isPending ? "loading" : documents.isError ? "error" : items.length === 0 ? "empty" : null);

  const visible = useMemo(() => {
    const annotated = items.map((item) => ({ item, lifecycle: documentLifecycle(item) }));
    const filtered =
      filters.businessState === "all"
        ? annotated
        : annotated.filter((row) => row.lifecycle.label === filters.businessState);
    const direction = sortAscending ? 1 : -1;
    const value = (row: (typeof annotated)[number]): string | number => {
      switch (sortKey) {
        case "title":
          return (row.item.title || row.item.filename).toLowerCase();
        case "type":
          return row.item.document_type ?? "";
        case "supplier":
          return row.item.supplier_name ?? "";
        case "effective":
          return row.item.effective_date ?? "";
        case "expiry":
          return row.item.expiry_date ?? "";
        default:
          return new Date(row.item.updated_at ?? row.item.created_at ?? 0).getTime();
      }
    };
    return [...filtered].sort((a, b) => {
      const left = value(a);
      const right = value(b);
      if (left === right) return 0;
      return (left > right ? 1 : -1) * direction;
    });
  }, [items, filters.businessState, sortKey, sortAscending]);

  // Counted with the same derivation the table uses, so the strip can never
  // contradict the rows below it.
  const lifecycleCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of items) {
      const label = documentLifecycle(item).label;
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }
    return counts;
  }, [items]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortAscending((value) => !value);
      return;
    }
    setSortKey(key);
    setSortAscending(key === "title" || key === "type" || key === "supplier");
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Documents"
        description="Manage supplier contracts, pricing agreements, amendments and compliance documents. Each file keeps its own pages, extracted tables and citation links."
        actions={
          canUpload ? (
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button size="sm">
                  <Upload className="h-3.5 w-3.5" aria-hidden="true" />
                  Upload document
                </Button>
              </DialogTrigger>
              <UploadDocumentDialog onClose={() => setDialogOpen(false)} />
            </Dialog>
          ) : (
            <Badge variant="outline" className="font-normal text-muted-foreground">
              Read-only access to documents
            </Badge>
          )
        }
      />

      {items.length > 0 ? (
        <dl
          aria-label="Documents by lifecycle"
          className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.08] sm:grid-cols-[repeat(auto-fit,minmax(148px,1fr))]"
        >
          {[...lifecycleCounts.keys()]
            .sort((a, b) => {
              const left = LIFECYCLE_ORDER.indexOf(a);
              const right = LIFECYCLE_ORDER.indexOf(b);
              return (left === -1 ? 99 : left) - (right === -1 ? 99 : right);
            })
            .map((state) => (
              <div key={state} className="bg-card px-4 py-3">
                <dt className="text-[10px] font-medium uppercase tracking-[0.14em] text-subtle">{state}</dt>
                <dd className="tnum mt-1 text-xl font-semibold leading-none">{lifecycleCounts.get(state)}</dd>
              </div>
            ))}
        </dl>
      ) : null}

      <DocumentFilters
        values={filters}
        onChange={(key, value) => setFilters((current) => ({ ...current, [key]: value }))}
        suppliers={suppliers.data?.items ?? []}
      />

      {documents.isError ? <ErrorState error={documents.error} onRetry={() => void documents.refetch()} /> : null}
      {documents.isLoading ? <LoadingRows rows={6} /> : null}

      {documents.data ? (
        items.length === 0 ? (
          <EmptyState
            icon={FileStack}
            title={MICROCOPY.noDocuments}
            description={`${microcopyPlain("noDocuments")} ${
              canUpload
                ? "Upload a supplier agreement, an amendment, a pricing spreadsheet or a scanned page and it becomes searchable with page-level citations."
                : "Your account can read documents but not upload them; an account with document write access can add files."
            }`}
          />
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
              <p>
                Showing {visible.length} of {documents.data.total} document(s)
                {documents.data.total > items.length ? ` (first ${items.length} loaded)` : ""}.
              </p>
              <p className="flex items-center gap-1.5">
                <ArrowUpDown className="h-3.5 w-3.5" aria-hidden="true" />
                Sort by {sortLabel(sortKey)}, {sortAscending ? "ascending" : "descending"}
              </p>
            </div>
            <div className="stack-layers rounded-lg border">
              <Table>
                <caption className="sr-only">
                  Documents in this workspace with the supplier, contract, state, version and recorded term of each. The
                  layers behind this table show that a document can exist in more than one version.
                </caption>
                <TableHeader className="sticky top-0 z-10 bg-card">
                  <TableRow>
                    <SortableHead label="Document" column="title" current={sortKey} ascending={sortAscending} onSort={toggleSort} />
                    <SortableHead label="Type" column="type" current={sortKey} ascending={sortAscending} onSort={toggleSort} />
                    <SortableHead label="Supplier" column="supplier" current={sortKey} ascending={sortAscending} onSort={toggleSort} />
                    <TableHead scope="col">Status</TableHead>
                    <TableHead scope="col">Version</TableHead>
                    <SortableHead label="Effective" column="effective" current={sortKey} ascending={sortAscending} onSort={toggleSort} />
                    <SortableHead label="Expiry" column="expiry" current={sortKey} ascending={sortAscending} onSort={toggleSort} />
                    <SortableHead label="Last updated" column="updated" current={sortKey} ascending={sortAscending} onSort={toggleSort} />
                    <TableHead scope="col" className="text-right">
                      Actions
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visible.map(({ item, lifecycle }) => (
                    <TableRow key={item.id}>
                      <TableCell className="max-w-[280px]">
                        <Link to={`/documents/${item.id}`} className="text-xs font-medium hover:underline">
                          {item.title || item.filename}
                        </Link>
                        <div className="mt-0.5 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                          <span className="truncate">{item.filename}</span>
                          {item.is_synthetic ? (
                            <Badge variant="outline" className="border-warning/35 font-normal text-warning">
                              demo corpus
                            </Badge>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs">{documentTypeLabel(item.document_type)}</TableCell>
                      <TableCell className="text-xs">
                        {item.supplier_name ?? <span className="italic text-muted-foreground">Not available</span>}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={cn("font-normal", toneClasses(lifecycle.tone))} title={lifecycle.basis}>
                          {lifecycle.label}
                        </Badge>
                        {["Processing", "Needs attention"].includes(lifecycle.label) ? (
                          <p className="mt-1 text-[11px] text-muted-foreground">{stageLabel(item.stage)}</p>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-xs">
                        <span className="tnum">v{item.version ?? 1}</span>
                        {item.revision_label ? (
                          <span className="ml-1 text-[11px] text-muted-foreground">{item.revision_label}</span>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-xs">{formatDate(item.effective_date)}</TableCell>
                      <TableCell className="text-xs">{formatDate(item.expiry_date)}</TableCell>
                      <TableCell className="text-[11px] text-muted-foreground">{formatDateTime(item.updated_at)}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="outline" size="sm" asChild>
                          <Link to={`/documents/${item.id}`}>Open</Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {visible.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-xs text-muted-foreground">
                        No document in this list has the status {filters.businessState}. Status is{" "}
                        {BUSINESS_STATES.includes(filters.businessState as (typeof BUSINESS_STATES)[number])
                          ? "derived from the recorded effective and expiry dates and from processing"
                          : "not available"}
                        ; documents without dates are listed as &ldquo;Not available&rdquo;.
                      </TableCell>
                    </TableRow>
                  ) : null}
                </TableBody>
              </Table>
            </div>
          </>
        )
      ) : null}

      <details className="rounded-lg border p-3 text-xs text-muted-foreground">
        <summary className="flex cursor-pointer items-center gap-2 font-medium text-foreground">
          <Info className="h-3.5 w-3.5" aria-hidden="true" />
          Processing details
        </summary>
        <p className="mt-2">
          Each upload is read, indexed and mined for prices, contract terms and relationships. The stage names below are
          the ones this deployment reports; a stage is only shown once the pipeline has reached it.
        </p>
        <ol className="mt-2 grid gap-1 sm:grid-cols-2">
          {PIPELINE_ORDER.map((stage, index) => (
            <li key={stage} className="flex items-baseline gap-2">
              <span className="tnum text-[11px] text-muted-foreground">{index + 1}</span>
              <span>
                <span className="font-medium text-foreground">{stageLabel(stage)}</span>
                <span className="text-muted-foreground"> ({stage})</span>
              </span>
            </li>
          ))}
        </ol>
        <p className="mt-2">
          Pages with no text layer are routed to OCR before layout analysis, and to the vision model only when one is
          configured. Documents that fail processing keep their error message on the document page.
        </p>
      </details>
    </div>
  );
}
