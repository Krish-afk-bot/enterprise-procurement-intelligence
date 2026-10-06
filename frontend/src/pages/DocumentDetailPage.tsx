import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BadgeCheck,
  Check,
  ChevronLeft,
  ChevronRight,
  FileText,
  History,
  ImageOff,
  Layers,
  PencilLine,
  RefreshCw,
  Table2,
  Trash2,
  Upload,
} from "lucide-react";

import { ErrorState, LoadingRows, LoadingState, NotAvailable } from "@/components/common/States";
import { PageHeader, MetaItem } from "@/components/common/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input, Label } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { MICROCOPY } from "@/lib/microcopy";
import type { DocumentDetail, DocumentSummary, TableOut } from "@/lib/types";
import { usePageImage } from "@/lib/usePageImage";
import {
  DOCUMENT_TYPE_LABELS,
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
import { useAuth } from "@/store/auth";

const ACCESS_LEVELS = ["public", "internal", "confidential", "restricted"] as const;

/** The processing steps a business user is shown, mapped to the real stages. */
const PROCESSING_CHECKLIST: { label: string; stages: string[] }[] = [
  { label: "Document received", stages: ["load"] },
  { label: "Information extracted", stages: ["parse", "ocr", "vision", "layout", "chunk", "persist_chunks"] },
  { label: "Prices, contracts and relationships identified", stages: ["structured_and_graph"] },
  { label: "Added to the search index", stages: ["vector_index"] },
  { label: "Ready to search", stages: ["indexed", "indexed_without_embeddings"] },
];

function cellText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

export function DocumentDetailPage() {
  const { documentId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const user = useAuth((state) => state.user);

  const pageParam = Number(searchParams.get("page") ?? "1");
  const citedChunkId = searchParams.get("chunk");
  const [page, setPage] = useState(Number.isFinite(pageParam) && pageParam > 0 ? pageParam : 1);
  const [jump, setJump] = useState("");

  const document = useQuery({ queryKey: ["document", documentId], queryFn: () => api.document(documentId) });
  const versions = useQuery({
    queryKey: ["document-versions", documentId],
    queryFn: () => api.documentVersions(documentId),
    enabled: Boolean(documentId),
  });
  const pageChunks = useQuery({
    queryKey: ["document-chunks", documentId, page],
    queryFn: () => api.documentChunks(documentId, { page, limit: 200 }),
    enabled: Boolean(documentId),
  });

  const pages = document.data?.pages ?? [];
  const maxPage = Math.max(pages.length, 1);
  const currentPage = useMemo(() => pages.find((item) => item.page_number === page) ?? null, [pages, page]);
  const image = usePageImage(documentId, page);

  useEffect(() => {
    if (Number.isFinite(pageParam) && pageParam > 0) setPage(pageParam);
  }, [pageParam]);

  function goToPage(next: number) {
    const bounded = Math.min(Math.max(next, 1), maxPage);
    setPage(bounded);
    const params = new URLSearchParams(searchParams);
    params.set("page", String(bounded));
    params.delete("chunk");
    setSearchParams(params, { replace: true });
  }

  const reindex = useMutation({
    mutationFn: () => api.reindexDocument(documentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["document", documentId] });
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const remove = useMutation({
    mutationFn: () => api.deleteDocument(documentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      navigate("/documents", { replace: true });
    },
  });

  const citedChunk = (pageChunks.data?.items ?? []).find((chunk) => chunk.id === citedChunkId) ?? null;

  if (document.isError) return <ErrorState error={document.error} onRetry={() => void document.refetch()} />;
  if (document.isLoading || !document.data) return <LoadingRows rows={7} />;
  const data = document.data;
  const lifecycle = documentLifecycle(data);
  const pageText = currentPage?.raw_text || currentPage?.ocr_text || "";
  const canEdit = Boolean(user?.permissions?.includes("documents:write"));
  const versionRows = versions.data ?? [];
  const activeVersion = versionRows.find((row) => row.is_current) ?? null;
  const processed = completedStages(data);
  const processingFailed = ["failed", "needs_review"].includes(data.status);

  return (
    <div className="space-y-5">
      <PageHeader
        title={data.title || data.filename}
        description={data.filename}
        backTo="/documents"
        backLabel="Back to documents"
        meta={
          <>
            <Badge variant="outline" className={cn("font-normal", toneClasses(lifecycle.tone))} title={lifecycle.basis}>
              {lifecycle.label}
            </Badge>
            <MetaItem label="Type">{documentTypeLabel(data.document_type)}</MetaItem>
            <MetaItem label="Version">
              v{data.version ?? 1}
              {data.revision_label ? ` · ${data.revision_label}` : ""}
            </MetaItem>
            <MetaItem label="Supplier">
              {data.supplier_id ? (
                <Link to={`/suppliers/${data.supplier_id}`} className="hover:underline">
                  {data.supplier_name ?? data.supplier_id}
                </Link>
              ) : (
                "Not available"
              )}
            </MetaItem>
            <MetaItem label="Contract">
              {data.contract_id ? (
                <Link to={`/contracts/${data.contract_id}`} className="hover:underline">
                  {data.contract_number ?? data.contract_id}
                </Link>
              ) : (
                "Not available"
              )}
            </MetaItem>
            <MetaItem label="Effective">{formatDate(data.effective_date)}</MetaItem>
            <MetaItem label="Expiry">{formatDate(data.expiry_date)}</MetaItem>
            <MetaItem label="Owner">{data.uploaded_by_name ?? NOT_RECORDED}</MetaItem>
            <MetaItem label="Access">{titleCase(data.access_level)}</MetaItem>
            {data.is_synthetic ? (
              <Badge variant="outline" className="border-warning/35 font-normal text-warning">
                demo corpus
              </Badge>
            ) : null}
          </>
        }
        actions={
          <>
            {canEdit ? <EditDetailsDialog document={data} /> : null}
            {canEdit ? <UploadVersionDialog document={data} /> : null}
            {canEdit ? (
              <Button variant="outline" size="sm" disabled={reindex.isPending} onClick={() => reindex.mutate()}>
                <RefreshCw className={cn("h-3.5 w-3.5", reindex.isPending && "animate-spin")} aria-hidden="true" />
                {reindex.isPending ? "Queuing" : "Re-index"}
              </Button>
            ) : null}
            {user?.permissions?.includes("documents:delete") ? (
              <Dialog>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm" className="text-destructive">
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    Delete
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-md">
                  <DialogHeader>
                    <DialogTitle>Delete this document?</DialogTitle>
                    <DialogDescription>
                      The file and everything derived from it are removed: pages, extracted text, tables, sections,
                      search index entries, price rows and relationship entries. This cannot be undone.
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter>
                    <DialogClose asChild>
                      <Button variant="outline" size="sm">
                        Cancel
                      </Button>
                    </DialogClose>
                    <Button variant="destructive" size="sm" disabled={remove.isPending} onClick={() => remove.mutate()}>
                      {remove.isPending ? "Deleting" : "Delete document"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            ) : null}
          </>
        }
      />

      {reindex.isError ? <ErrorState error={reindex.error} /> : null}
      {remove.isError ? <ErrorState error={remove.error} /> : null}

      {processingFailed ? (
        <p className="rounded-md border border-destructive/35 bg-destructive/5 p-3 text-xs">
          <span className="font-medium">Processing reported a problem.</span>{" "}
          {data.error_message ?? "No error message was recorded."} The pages below are what was extracted before the run
          stopped. Re-index to try again.
        </p>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[240px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)_340px]">
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
                      row.id === documentId ? "border-primary/40 bg-primary/5" : null,
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
                      {row.id === documentId ? (
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
              <Row label="Document type" value={documentTypeLabel(data.document_type)} />
              <Row label="Supplier" value={data.supplier_name ?? "Not available"} />
              <Row label="Contract" value={data.contract_number ?? "Not available"} />
              <Row label="Status" value={lifecycle.label} />
              <Row label="Effective" value={formatDate(data.effective_date)} />
              <Row label="Expiry" value={formatDate(data.expiry_date)} />
              <Row label="Owner" value={data.uploaded_by_name ?? NOT_RECORDED} />
              <Row label="Access" value={titleCase(data.access_level)} />
              <Row label="Revision label" value={data.revision_label ?? NOT_RECORDED} />
              <Row label="Size" value={formatBytes(data.size_bytes)} />
              <Row label="Added" value={formatDateTime(data.created_at)} />
              <Row label="Last updated" value={formatDateTime(data.updated_at)} />
            </dl>
            {canEdit ? (
              <div className="mt-2">
                <EditDetailsDialog document={data} trigger={<Button variant="outline" size="sm">Edit details</Button>} />
              </div>
            ) : null}
          </section>
        </nav>

        {/* The page changes are the largest transition in the workspace: a
            short rise, keyed on the page number so it plays once per page. */}
        <section key={`page-${page}`} aria-label={`Page ${page}`} className="min-w-0 animate-page space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => goToPage(page - 1)}>
              <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={page >= maxPage} onClick={() => goToPage(page + 1)}>
              Next
              <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
            <p className="tnum text-xs text-muted-foreground">
              Page {page} of {maxPage}
            </p>
            <form
              className="ml-auto flex items-center gap-1.5"
              onSubmit={(event) => {
                event.preventDefault();
                const target = Number(jump);
                if (Number.isFinite(target) && target > 0) goToPage(target);
                setJump("");
              }}
            >
              <label htmlFor="jump-page" className="text-[11px] text-muted-foreground">
                Go to page
              </label>
              <Input id="jump-page" value={jump} inputMode="numeric" onChange={(event) => setJump(event.target.value)} className="h-8 w-16" />
            </form>
          </div>

          {citedChunk ? (
            /* The citation is never hidden: the passage is shown in full and the
               focus animation only draws the eye to it. */
            <div className="cited-passage animate-cite rounded-r-md py-2.5">
              <p className="text-[11px] font-medium uppercase tracking-wide text-primary">Cited passage on this page</p>
              <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed">{citedChunk.content}</p>
              <p className="mt-1.5 text-[11px] text-muted-foreground">
                {citedChunk.section ?? "section not recorded"}
                {citedChunk.clause ? ` · ${citedChunk.clause}` : ""} · {citedChunk.content_type}
              </p>
            </div>
          ) : citedChunkId ? (
            <p className="rounded-md border border-warning/35 bg-warning/5 p-2.5 text-xs text-muted-foreground">
              The cited passage is not on page {page}. Use the citation link again, or search the passages below.
            </p>
          ) : null}

          <div className="page-sheet">
            <div className="flex flex-wrap items-center gap-2 border-b px-4 py-2.5">
              <h3 className="flex items-center gap-2 text-xs font-medium">
                <FileText className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                Page preview and extracted text
              </h3>
              {currentPage ? (
                <>
                  <Badge variant="outline" className="font-normal">
                    {currentPage.has_text_layer ? "text layer present" : "no text layer"}
                  </Badge>
                  <Badge variant="outline" className="font-normal">
                    {currentPage.is_scanned ? "scanned" : "digital"}
                  </Badge>
                  <span className="tnum text-[11px] text-muted-foreground">{currentPage.char_count} characters</span>
                </>
              ) : null}
            </div>
            <div className="space-y-3 p-4">
              {image.loading ? <LoadingState label="Loading the rendered page" /> : null}
              {image.url ? (
                <figure className="page-sheet overflow-hidden">
                  <img
                    src={image.url}
                    alt={`Rendered page ${page} of ${data.title || data.filename}`}
                    className="w-full bg-muted object-contain"
                  />
                  <figcaption className="border-t px-3 py-1.5 text-[11px] text-muted-foreground">
                    Rendered from the stored file · page {page} of {maxPage}
                  </figcaption>
                </figure>
              ) : image.error ? (
                <p className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">
                  {image.error instanceof Error ? image.error.message : "No rendered page image is stored."} The extracted
                  text below is what was indexed.
                </p>
              ) : null}

              <div className="max-h-[420px] overflow-y-auto scrollbar-thin">
                {pageText ? (
                  <p className="whitespace-pre-wrap text-xs leading-relaxed">{pageText}</p>
                ) : (
                  <NotAvailable label="No text was extracted for this page." />
                )}
                {currentPage?.vision_summary ? (
                  <div className="mt-3 rounded-md border p-3">
                    <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Page imagery summary</p>
                    <p className="mt-1 text-xs leading-relaxed">{currentPage.vision_summary}</p>
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          {currentPage && currentPage.tables.length > 0 ? (
            <div className="space-y-3">
              <h3 className="flex items-center gap-2 text-xs font-medium">
                <Table2 className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                {plural(currentPage.tables.length, "table")} extracted from this page
              </h3>
              {currentPage.tables.map((table) => (
                <ExtractedTable key={table.id} table={table} caption={`Table ${table.table_index + 1} on page ${table.page_number}`} />
              ))}
            </div>
          ) : null}

          <details className="rounded-lg border p-3 text-xs">
            <summary className="flex cursor-pointer items-center gap-2 font-medium text-foreground">
              <Layers className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
              Processing details
            </summary>
            <div className="mt-3 space-y-4 text-muted-foreground">
              <div>
                <h4 className="text-[11px] font-semibold uppercase tracking-wide">How far processing has reached</h4>
                <ol className="mt-1.5 space-y-1">
                  {PROCESSING_CHECKLIST.map((step) => {
                    const done = step.stages.some((stage) => processed.has(stage));
                    return (
                      <li key={step.label} className="flex items-center gap-2">
                        <Check
                          className={cn("h-3.5 w-3.5 shrink-0", done ? "text-success" : "text-muted-foreground/40")}
                          aria-hidden="true"
                        />
                        <span className={cn(done ? "text-foreground" : null)}>
                          {step.label}
                          <span className="sr-only">{done ? " — completed" : " — not reached"}</span>
                        </span>
                      </li>
                    );
                  })}
                </ol>
                <p className="mt-1.5 text-[11px]">
                  Stages reported by this run: {processed.size > 0 ? Array.from(processed).join(", ") : "none yet"}.
                </p>
              </div>

              <dl className="space-y-1.5">
                <Row label="Processing status" value={titleCase(data.status)} />
                <Row label="Stage" value={data.stage ?? (data.job?.stage ?? "not reported")} />
                <Row label="Progress" value={`${Math.round(((data.progress ?? data.job?.progress ?? 0) || 0) * 100)}%`} />
                <Row label="Attempts" value={String(data.job?.attempts ?? 0)} />
                <Row label="Queued" value={formatDateTime(data.job?.queued_at)} />
                <Row label="Finished" value={formatDateTime(data.job?.finished_at)} />
                <Row label="Access level" value={data.access_level} />
              </dl>

              <div>
                <h4 className="text-[11px] font-semibold uppercase tracking-wide">Provenance</h4>
                <dl className="mt-1.5 space-y-1.5">
                  <Row label="Source" value={data.source ?? "not recorded"} />
                  <Row label="Source URI" value={data.source_uri ?? "not recorded"} />
                  <Row label="Licence" value={data.license ?? "not recorded"} />
                  <Row label="Retrieved" value={formatDateTime(data.retrieved_at)} />
                  <Row label="Checksum" value={data.checksum ? `${data.checksum.slice(0, 16)}…` : "not recorded"} />
                  <Row label="OCR applied" value={data.ocr_applied ? "yes" : "no"} />
                  <Row label="Vision applied" value={data.vision_applied ? "yes" : "no"} />
                  <Row label="Scanned pages" value={String(data.scanned_page_count ?? 0)} />
                </dl>
                {data.source_url ? <p className="mt-1.5 truncate text-[11px]">{data.source_url}</p> : null}
              </div>

              <div>
                <h4 className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide">
                  <Layers className="h-3 w-3" aria-hidden="true" />
                  Stored content types
                </h4>
                <p className="mt-1.5 text-[11px]">
                  {Object.entries(data.chunk_type_counts ?? {})
                    .map(([type, count]) => `${type} ${count}`)
                    .join(", ") || "not recorded"}
                </p>
              </div>
            </div>
          </details>
        </section>

        <aside aria-label="Evidence and extracted information" className="min-w-0 space-y-5">
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Evidence extracted</h2>
            <dl className="mt-2 space-y-1.5 text-xs">
              <Row label="Pages" value={String(pages.length)} />
              <Row label="Sections on this page" value={String(pageChunks.data?.total ?? 0)} />
              <Row label="Tables on this page" value={String(currentPage?.tables.length ?? 0)} />
              <Row label="Tables in document" value={String(data.table_count ?? 0)} />
            </dl>
          </section>

          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Related records</h2>
            <dl className="mt-2 space-y-1.5 text-xs">
              <Row
                label="Supplier"
                value={
                  data.supplier_id ? (
                    <Link to={`/suppliers/${data.supplier_id}`} className="hover:underline">
                      {data.supplier_name ?? "open supplier"}
                    </Link>
                  ) : (
                    "Not available"
                  )
                }
              />
              <Row
                label="Contract"
                value={
                  data.contract_id ? (
                    <Link to={`/contracts/${data.contract_id}`} className="hover:underline">
                      {data.contract_number ?? "open contract"}
                    </Link>
                  ) : (
                    "Not available"
                  )
                }
              />
            </dl>
            {!data.supplier_id && canEdit ? (
              <p className="mt-2 text-[11px] text-muted-foreground">
                Link a supplier or contract with <span className="font-medium text-foreground">Edit details</span>.
              </p>
            ) : null}
          </section>

          <section aria-labelledby="page-evidence-heading">
            <h2 id="page-evidence-heading" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
              Passages stored for this page
            </h2>
            <ul className="mt-2 space-y-2">
              {(pageChunks.data?.items ?? []).map((chunk) => (
                <li
                  key={chunk.id}
                  className={cn("rounded border p-2 text-[11px]", chunk.id === citedChunkId ? "cited-passage rounded-r-md" : null)}
                >
                  <div className="flex flex-wrap items-center gap-2 text-muted-foreground">
                    <span>{titleCase(chunk.content_type)}</span>
                    {chunk.section ? <span>{chunk.section}</span> : null}
                    {chunk.clause ? <span>{chunk.clause}</span> : null}
                  </div>
                  <p className="mt-1 line-clamp-4 leading-relaxed">{chunk.content}</p>
                  <p className="mt-1 text-[10px] text-muted-foreground">#{chunk.chunk_index}</p>
                </li>
              ))}
              {pageChunks.data && pageChunks.data.items.length === 0 ? (
                <li className="text-[11px] text-muted-foreground">No passage is stored for this page.</li>
              ) : null}
            </ul>
          </section>

          <p className="text-[11px] leading-relaxed text-muted-foreground">
            Back to{" "}
            <Link to="/documents" className="underline hover:text-foreground">
              all documents
            </Link>
            .
          </p>
        </aside>
      </div>
    </div>
  );
}

/** The stages the stored job reports as reached. */
function completedStages(data: DocumentDetail): Set<string> {
  const stages = new Set<string>();
  for (const entry of data.job?.stages_completed ?? []) {
    if (typeof entry === "string") stages.add(entry);
    else if (entry && typeof entry === "object" && "stage" in entry && typeof (entry as { stage: unknown }).stage === "string") {
      stages.add((entry as { stage: string }).stage);
    }
  }
  if (data.stage) stages.add(data.stage);
  if (data.status === "indexed") stages.add("indexed");
  return stages;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}

function EditDetailsDialog({ document, trigger }: { document: DocumentDetail; trigger?: React.ReactNode }) {
  const queryClient = useQueryClient();
  const user = useAuth((state) => state.user);
  const suppliers = useQuery({ queryKey: ["suppliers", "edit-details"], queryFn: () => api.suppliers({ limit: 100 }) });
  const contracts = useQuery({ queryKey: ["contracts", "edit-details"], queryFn: () => api.contracts({ limit: 200 }) });

  const [title, setTitle] = useState(document.title || document.filename);
  const [documentType, setDocumentType] = useState(document.document_type ?? "other");
  const [supplierId, setSupplierId] = useState(document.supplier_id ?? "none");
  const [contractId, setContractId] = useState(document.contract_id ?? "none");
  const [effectiveDate, setEffectiveDate] = useState(document.effective_date ?? "");
  const [expiryDate, setExpiryDate] = useState(document.expiry_date ?? "");
  const [accessLevel, setAccessLevel] = useState(document.access_level);
  const [revisionLabel, setRevisionLabel] = useState(document.revision_label ?? "");
  const [saved, setSaved] = useState<DocumentSummary | null>(null);

  const ceilingIndex = ACCESS_LEVELS.indexOf((user?.access_ceiling ?? "internal") as (typeof ACCESS_LEVELS)[number]);

  const save = useMutation({
    mutationFn: () =>
      api.updateDocument(document.id, {
        title,
        document_type: documentType,
        supplier_id: supplierId === "none" ? null : supplierId,
        contract_id: contractId === "none" ? null : contractId,
        effective_date: effectiveDate || null,
        expiry_date: expiryDate || null,
        access_level: accessLevel,
        revision_label: revisionLabel || null,
      }),
    onSuccess: (payload) => {
      setSaved(payload);
      void queryClient.invalidateQueries({ queryKey: ["document", document.id] });
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["document-versions", document.id] });
    },
  });

  return (
    <Dialog>
      <DialogTrigger asChild>
        {trigger ?? (
          <Button variant="outline" size="sm">
            <PencilLine className="h-3.5 w-3.5" aria-hidden="true" />
            Edit details
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit document details</DialogTitle>
          <DialogDescription>
            These values are stored on the document and shown across the workspace. The file itself is not changed, and
            processing state is reported by the pipeline rather than edited here.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="edit-title">Document name</Label>
            <Input id="edit-title" value={title} onChange={(event) => setTitle(event.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Document type</Label>
            <Select value={documentType} onValueChange={setDocumentType}>
              <SelectTrigger aria-label="Document type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(DOCUMENT_TYPE_LABELS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
                {documentType && !(documentType in DOCUMENT_TYPE_LABELS) ? (
                  <SelectItem value={documentType}>{titleCase(documentType)} (as recorded)</SelectItem>
                ) : null}
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
                <SelectItem value="none">not linked</SelectItem>
                {(suppliers.data?.items ?? []).map((supplier) => (
                  <SelectItem key={supplier.id} value={supplier.id}>
                    {supplier.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Contract</Label>
            <Select value={contractId} onValueChange={setContractId}>
              <SelectTrigger aria-label="Contract">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">not linked</SelectItem>
                {(contracts.data?.items ?? [])
                  .filter((contract) => supplierId === "none" || contract.supplier_id === supplierId)
                  .map((contract) => (
                    <SelectItem key={contract.id} value={contract.id}>
                      {contract.contract_number}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground">
              {supplierId === "none"
                ? "All contracts are listed. Choose a supplier to narrow the list."
                : "Contracts recorded for the chosen supplier."}
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-effective">Effective date</Label>
            <Input id="edit-effective" type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-expiry">Expiry date</Label>
            <Input id="edit-expiry" type="date" value={expiryDate} onChange={(event) => setExpiryDate(event.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Access level</Label>
            <Select value={accessLevel} onValueChange={setAccessLevel}>
              <SelectTrigger aria-label="Access level">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ACCESS_LEVELS.map((level, index) => (
                  <SelectItem key={level} value={level} disabled={index > ceilingIndex}>
                    {titleCase(level)}
                    {index > ceilingIndex ? " — above your access ceiling" : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground">
              Your account may assign up to <span className="font-medium text-foreground">{titleCase(user?.access_ceiling ?? "internal")}</span>.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-revision">Revision label</Label>
            <Input id="edit-revision" value={revisionLabel} onChange={(event) => setRevisionLabel(event.target.value)} />
          </div>
        </div>

        {save.isError ? <ErrorState error={save.error} /> : null}

        {saved ? (
          <div className="rounded-md border border-success/35 bg-success/5 p-3 text-xs">
            <p className="font-medium">Details saved.</p>
            <p className="mt-1 text-muted-foreground">
              {saved.title} · {documentTypeLabel(saved.document_type)} · {saved.supplier_name ?? "no supplier linked"} ·{" "}
              v{saved.version ?? 1}
            </p>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Search filters are matched against the values recorded when the document was indexed. Re-index the document
              to make a changed supplier, type or term take effect in search.
            </p>
          </div>
        ) : null}

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" size="sm">
              Close
            </Button>
          </DialogClose>
          <Button size="sm" disabled={save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? "Saving" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function UploadVersionDialog({ document }: { document: DocumentDetail }) {
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const limits = useQuery({ queryKey: ["upload-limits"], queryFn: api.uploadLimits });
  const [revisionLabel, setRevisionLabel] = useState("");
  const [title, setTitle] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [result, setResult] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: (file: File) =>
      api.uploadDocument(file, {
        replaces_document_id: document.id,
        document_type: document.document_type ?? undefined,
        title: title || undefined,
        revision_label: revisionLabel || undefined,
        effective_date: effectiveDate || undefined,
        expiry_date: expiryDate || undefined,
      }),
    onSuccess: (payload) => {
      setResult(
        payload.duplicate_of
          ? "This file is byte-for-byte identical to a document already in the repository, so no new version was created. Upload the changed file instead."
          : `Uploaded as v${payload.document.version ?? "?"}. The previous version is preserved with its own pages and citations.`,
      );
      void queryClient.invalidateQueries({ queryKey: ["document", document.id] });
      void queryClient.invalidateQueries({ queryKey: ["document-versions", document.id] });
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button size="sm">
          <Upload className="h-3.5 w-3.5" aria-hidden="true" />
          Upload new version
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Upload a new version</DialogTitle>
          <DialogDescription>
            The uploaded file becomes the next version of {document.title || document.filename}. The current version
            v{document.version ?? 1} is kept exactly as it is, including the pages that have already been cited.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="version-file">File</Label>
            <input
              id="version-file"
              ref={fileInput}
              type="file"
              accept={(limits.data?.allowed_extensions ?? [".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md"]).join(",")}
              className="block w-full rounded-md border border-input bg-background text-xs file:mr-3 file:rounded-l-md file:border-0 file:bg-secondary file:px-3 file:py-2 file:text-xs file:font-medium"
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="version-title">Document name (optional)</Label>
              <Input
                id="version-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder={document.title || document.filename}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="version-revision">Revision label</Label>
              <Input id="version-revision" value={revisionLabel} onChange={(event) => setRevisionLabel(event.target.value)} placeholder="Amendment 2" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="version-effective">Effective date</Label>
              <Input id="version-effective" type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="version-expiry">Expiry date</Label>
              <Input id="version-expiry" type="date" value={expiryDate} onChange={(event) => setExpiryDate(event.target.value)} />
            </div>
          </div>
          <p className="text-[11px] text-muted-foreground">
            After the upload the new version is read, indexed and mined for prices and contract terms; relationship and
            amendment links are reconciled by that run. Nothing is overwritten.
          </p>

          {result ? (
            <p className="rounded-md border border-success/35 bg-success/5 p-3 text-xs">{result}</p>
          ) : null}
          {upload.isError ? <ErrorState error={upload.error} /> : null}
        </div>

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" size="sm">
              Close
            </Button>
          </DialogClose>
          <Button
            size="sm"
            disabled={upload.isPending}
            onClick={() => {
              const file = fileInput.current?.files?.[0];
              if (file) upload.mutate(file);
            }}
          >
            {upload.isPending ? "Uploading" : "Upload version"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ExtractedTable({ table, caption }: { table: TableOut; caption: string }) {
  const headers = (table.headers ?? []).map(cellText);
  const rows = (table.rows ?? []).map((row) => (Array.isArray(row) ? row.map(cellText) : [cellText(row)]));

  return (
    <figure className="rounded-lg border">
      <figcaption className="flex flex-wrap items-center gap-2 border-b px-3 py-2 text-[11px] text-muted-foreground">
        <span className="font-medium text-foreground">{table.caption ?? caption}</span>
        <span>{table.extraction_method}</span>
        {table.complexity_score ? <span>complexity {table.complexity_score}</span> : null}
      </figcaption>
      <Table>
        {headers.length > 0 ? (
          <TableHeader>
            <TableRow>
              {headers.map((header, index) => (
                <TableHead key={index} scope="col">
                  {header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
        ) : null}
        <TableBody>
          {rows.map((row, rowIndex) => (
            <TableRow key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <TableCell key={cellIndex} className="tnum text-xs">
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </figure>
  );
}
