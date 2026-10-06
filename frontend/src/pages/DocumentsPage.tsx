import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpDown, FileStack, Info, Search, Upload } from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingRows } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input, Label } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Switch } from "@/components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { useMood } from "@/lib/useMood";
import { MICROCOPY, microcopyPlain } from "@/lib/microcopy";
import type { UploadResponse } from "@/lib/types";
import { useAuth } from "@/store/auth";
import {
  DOCUMENT_TYPE_LABELS,
  cn,
  documentLifecycle,
  documentTypeLabel,
  formatDate,
  formatDateTime,
  titleCase,
  toneClasses,
} from "@/lib/utils";

/** Real ingestion stages, in the order the pipeline reports them. */
const STAGE_LABELS: Record<string, string> = {
  load: "Document received",
  parse: "Document read",
  ocr: "Scanned pages read",
  vision: "Page imagery read",
  layout: "Layout analysed",
  chunk: "Sections identified",
  persist_chunks: "Sections stored",
  vector_index: "Added to the search index",
  structured_and_graph: "Prices, contracts and relationships identified",
  indexed: "Ready to search",
  indexed_without_embeddings: "Ready to search (keyword index only)",
  failed: "Processing failed",
};

/** The stages the pipeline reports, in order, for the progress view. */
const PIPELINE_ORDER = [
  "load",
  "parse",
  "ocr",
  "layout",
  "chunk",
  "persist_chunks",
  "vector_index",
  "structured_and_graph",
  "indexed",
];

function stageLabel(stage: string | null | undefined): string {
  if (!stage) return "not reported";
  return STAGE_LABELS[stage] ?? titleCase(stage);
}

type SortKey = "updated" | "title" | "type" | "supplier" | "effective" | "expiry";

const BUSINESS_STATES = [
  "all",
  "Active",
  "Expires soon",
  "Expired",
  "Superseded",
  "Processing",
  "Needs attention",
  "Not available",
] as const;

export function DocumentsPage() {
  const user = useAuth((state) => state.user);
  const canUpload = Boolean(user?.permissions?.includes("documents:write"));
  const [search, setSearch] = useState("");
  const [documentType, setDocumentType] = useState("all");
  const [supplierId, setSupplierId] = useState("all");
  const [businessState, setBusinessState] = useState<string>("all");
  const [includeSynthetic, setIncludeSynthetic] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>("updated");
  const [sortAscending, setSortAscending] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  const documents = useQuery({
    queryKey: ["documents", search, documentType, supplierId, includeSynthetic],
    queryFn: () =>
      api.documents({
        search: search || undefined,
        document_type: documentType === "all" ? undefined : documentType,
        supplier_id: supplierId === "all" ? undefined : supplierId,
        include_synthetic: includeSynthetic,
        limit: 200,
      }),
    refetchInterval: 8_000,
  });
  const suppliers = useQuery({ queryKey: ["suppliers", "documents-filter"], queryFn: () => api.suppliers({ limit: 100 }) });

  const items = documents.data?.items ?? [];

  useMood(documents.isPending ? "loading" : documents.isError ? "error" : items.length === 0 ? "empty" : null);

  const visible = useMemo(() => {
    const annotated = items.map((item) => ({ item, lifecycle: documentLifecycle(item) }));
    const filtered =
      businessState === "all" ? annotated : annotated.filter((row) => row.lifecycle.label === businessState);
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
  }, [items, businessState, sortKey, sortAscending]);

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

      <div className="flex flex-wrap items-end gap-3 rounded-lg border p-3">
        <div className="min-w-[220px] flex-1 space-y-1.5">
          <Label htmlFor="document-search">Search</Label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
            <Input
              id="document-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Title or filename"
              className="pl-8"
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label>Status</Label>
          <Select value={businessState} onValueChange={setBusinessState}>
            <SelectTrigger className="w-[170px]" aria-label="Filter by document status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {BUSINESS_STATES.map((value) => (
                <SelectItem key={value} value={value}>
                  {value === "all" ? "all statuses" : value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Type</Label>
          <Select value={documentType} onValueChange={setDocumentType}>
            <SelectTrigger className="w-[180px]" aria-label="Filter by document type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">all types</SelectItem>
              {Object.entries(DOCUMENT_TYPE_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Supplier</Label>
          <Select value={supplierId} onValueChange={setSupplierId}>
            <SelectTrigger className="w-[200px]" aria-label="Filter by supplier">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">all suppliers</SelectItem>
              {(suppliers.data?.items ?? []).map((supplier) => (
                <SelectItem key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2 pb-1.5">
          <Switch id="documents-synthetic" checked={includeSynthetic} onCheckedChange={setIncludeSynthetic} />
          <label htmlFor="documents-synthetic" className="text-xs text-muted-foreground">
            include demo corpus
          </label>
        </div>
      </div>

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
                <TableHeader>
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
                        No document in this list has the status {businessState}. Status is derived from the recorded
                        effective and expiry dates and from processing; documents without dates are listed as
                        &ldquo;Not available&rdquo;.
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

function sortLabel(key: SortKey): string {
  switch (key) {
    case "title":
      return "document name";
    case "type":
      return "type";
    case "supplier":
      return "supplier";
    case "effective":
      return "effective date";
    case "expiry":
      return "expiry date";
    default:
      return "last updated";
  }
}

function SortableHead({
  label,
  column,
  current,
  ascending,
  onSort,
}: {
  label: string;
  column: SortKey;
  current: SortKey;
  ascending: boolean;
  onSort: (key: SortKey) => void;
}) {
  const active = current === column;
  return (
    <TableHead scope="col" aria-sort={active ? (ascending ? "ascending" : "descending") : "none"}>
      <button
        type="button"
        onClick={() => onSort(column)}
        className={cn(
          "inline-flex items-center gap-1 text-left text-xs font-medium transition-colors duration-micro hover:text-foreground",
          active ? "text-foreground" : "text-muted-foreground",
        )}
      >
        {label}
        <ArrowUpDown className="h-3 w-3" aria-hidden="true" />
      </button>
    </TableHead>
  );
}

function UploadDocumentDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const limits = useQuery({ queryKey: ["upload-limits"], queryFn: api.uploadLimits });
  const suppliers = useQuery({ queryKey: ["suppliers", "upload-form"], queryFn: () => api.suppliers({ limit: 100 }) });
  const fileInput = useRef<HTMLInputElement>(null);

  const [documentType, setDocumentType] = useState("");
  const [supplierId, setSupplierId] = useState("none");
  const [title, setTitle] = useState("");
  const [revisionLabel, setRevisionLabel] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [isSynthetic, setIsSynthetic] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<unknown>(null);

  const selectedSupplier = (suppliers.data?.items ?? []).find((supplier) => supplier.id === supplierId) ?? null;

  const upload = useMutation({
    mutationFn: (file: File) =>
      api.uploadDocument(file, {
        document_type: documentType || undefined,
        supplier_name: selectedSupplier?.name,
        title: title || undefined,
        revision_label: revisionLabel || undefined,
        effective_date: effectiveDate || undefined,
        expiry_date: expiryDate || undefined,
        is_synthetic: isSynthetic,
      }),
    onSuccess: (payload) => {
      setResult(payload);
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (uploadError) => {
      setResult(null);
      setError(uploadError);
    },
  });

  return (
    <DialogContent className="max-w-2xl">
      <DialogHeader>
        <DialogTitle>Upload a document</DialogTitle>
        <DialogDescription>
          The file is stored, then read and indexed. The details you add here are what the repository, the filters and the
          citations show.
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="upload-file">File</Label>
          <input
            id="upload-file"
            ref={fileInput}
            type="file"
            accept={(limits.data?.allowed_extensions ?? [".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md"]).join(",")}
            className="block w-full rounded-md border border-input bg-background text-xs file:mr-3 file:rounded-l-md file:border-0 file:bg-secondary file:px-3 file:py-2 file:text-xs file:font-medium"
          />
          <p className="text-[11px] text-muted-foreground">
            Maximum size {limits.data ? `${limits.data.max_upload_mb} MB` : "set by the deployment"}. Accepted types:{" "}
            {(limits.data?.allowed_extensions ?? ["not reported"]).join(", ")}. Uploading a file that is already in the
            corpus returns the existing document instead of ingesting it twice.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Document type</Label>
            <Select value={documentType || "unset"} onValueChange={(value) => setDocumentType(value === "unset" ? "" : value)}>
              <SelectTrigger aria-label="Document type">
                <SelectValue placeholder="Choose a type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="unset">let the pipeline classify it</SelectItem>
                {Object.entries(DOCUMENT_TYPE_LABELS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Supplier</Label>
            <Select value={supplierId} onValueChange={setSupplierId}>
              <SelectTrigger aria-label="Supplier">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">not linked yet</SelectItem>
                {(suppliers.data?.items ?? []).map((supplier) => (
                  <SelectItem key={supplier.id} value={supplier.id}>
                    {supplier.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground">
              {suppliers.data
                ? "The supplier is recorded on the document; a contract can be linked from the document page."
                : "Loading suppliers"}
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="upload-title">Document name</Label>
            <Input
              id="upload-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Master Supply Agreement"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="upload-revision">Revision label</Label>
            <Input
              id="upload-revision"
              value={revisionLabel}
              onChange={(event) => setRevisionLabel(event.target.value)}
              placeholder="signed copy"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="upload-effective">Effective date</Label>
            <Input
              id="upload-effective"
              type="date"
              value={effectiveDate}
              onChange={(event) => setEffectiveDate(event.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="upload-expiry">Expiry date</Label>
            <Input id="upload-expiry" type="date" value={expiryDate} onChange={(event) => setExpiryDate(event.target.value)} />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Switch id="upload-synthetic" checked={isSynthetic} onCheckedChange={setIsSynthetic} />
          <label htmlFor="upload-synthetic" className="text-xs text-muted-foreground">
            label this file as part of the demo corpus
          </label>
        </div>

        {result ? (
          <div className="rounded-md border border-success/35 bg-success/5 p-3 text-xs">
            <p className="font-medium">
              {result.duplicate_of ? "This file is already in the repository. It was not ingested again." : result.message}
            </p>
            <p className="mt-1 text-muted-foreground">{result.document.filename}</p>
            {result.job ? (
              <p className="mt-1 text-[11px] text-muted-foreground">
                Processing: {stageLabel(result.job.stage ?? result.job.status)} · {Math.round((result.job.progress ?? 0) * 100)}%
              </p>
            ) : null}
            <p className="mt-2">
              <Link to={`/documents/${result.document.id}`} className="font-medium text-primary hover:underline">
                Open the document
              </Link>
            </p>
          </div>
        ) : null}

        {error ? <ErrorState error={error} /> : null}
      </div>

      <DialogFooter>
        <Button variant="outline" size="sm" onClick={onClose} disabled={upload.isPending}>
          Close
        </Button>
        <Button
          size="sm"
          disabled={upload.isPending}
          onClick={() => {
            const file = fileInput.current?.files?.[0];
            if (file) upload.mutate(file);
          }}
        >
          {upload.isPending ? "Uploading" : "Upload"}
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}


