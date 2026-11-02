import { useState } from "react";
import { Check, ChevronLeft, ChevronRight, FileText, Layers, Table2 } from "lucide-react";

import { LoadingState, NotAvailable } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DetailRow } from "@/features/documents/DetailRow";
import { ExtractedTable } from "@/features/documents/ExtractedTable";
import type { ChunkOut, DocumentDetail, PageOut } from "@/lib/types";
import { usePageImage } from "@/lib/usePageImage";
import { cn, formatDateTime, plural, titleCase } from "@/lib/utils";

/** The processing steps a business user is shown, mapped to the real stages. */
const PROCESSING_CHECKLIST: { label: string; stages: string[] }[] = [
  { label: "Document received", stages: ["load"] },
  { label: "Information extracted", stages: ["parse", "ocr", "vision", "layout", "chunk", "persist_chunks"] },
  { label: "Prices, contracts and relationships identified", stages: ["structured_and_graph"] },
  { label: "Added to the search index", stages: ["vector_index"] },
  { label: "Ready to search", stages: ["indexed", "indexed_without_embeddings"] },
];

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

/** The middle column: one page of the document with its preview and provenance. */
export function DocumentPageViewer({
  documentId,
  data,
  page,
  maxPage,
  goToPage,
  currentPage,
  citedChunk,
  citedChunkId,
}: {
  documentId: string;
  data: DocumentDetail;
  page: number;
  maxPage: number;
  goToPage: (page: number) => void;
  currentPage: PageOut | null;
  citedChunk: ChunkOut | null;
  citedChunkId: string | null;
}) {
  const [jump, setJump] = useState("");
  const image = usePageImage(documentId, page);
  const pageText = currentPage?.raw_text || currentPage?.ocr_text || "";
  const processed = completedStages(data);

  return (
    /* The page changes are the largest transition in the workspace: a
       short rise, keyed on the page number so it plays once per page. */
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
            <DetailRow label="Processing status" value={titleCase(data.status)} />
            <DetailRow label="Stage" value={data.stage ?? (data.job?.stage ?? "not reported")} />
            <DetailRow label="Progress" value={`${Math.round(((data.progress ?? data.job?.progress ?? 0) || 0) * 100)}%`} />
            <DetailRow label="Attempts" value={String(data.job?.attempts ?? 0)} />
            <DetailRow label="Queued" value={formatDateTime(data.job?.queued_at)} />
            <DetailRow label="Finished" value={formatDateTime(data.job?.finished_at)} />
            <DetailRow label="Access level" value={data.access_level} />
          </dl>

          <div>
            <h4 className="text-[11px] font-semibold uppercase tracking-wide">Provenance</h4>
            <dl className="mt-1.5 space-y-1.5">
              <DetailRow label="Source" value={data.source ?? "not recorded"} />
              <DetailRow label="Source URI" value={data.source_uri ?? "not recorded"} />
              <DetailRow label="Licence" value={data.license ?? "not recorded"} />
              <DetailRow label="Retrieved" value={formatDateTime(data.retrieved_at)} />
              <DetailRow label="Checksum" value={data.checksum ? `${data.checksum.slice(0, 16)}…` : "not recorded"} />
              <DetailRow label="OCR applied" value={data.ocr_applied ? "yes" : "no"} />
              <DetailRow label="Vision applied" value={data.vision_applied ? "yes" : "no"} />
              <DetailRow label="Scanned pages" value={String(data.scanned_page_count ?? 0)} />
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
  );
}
