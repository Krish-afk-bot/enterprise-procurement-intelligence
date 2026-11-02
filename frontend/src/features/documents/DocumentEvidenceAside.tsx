import { Link } from "react-router-dom";
import { BadgeCheck } from "lucide-react";

import { DetailRow } from "@/features/documents/DetailRow";
import type { ChunkOut, DocumentDetail } from "@/lib/types";
import { cn, titleCase } from "@/lib/utils";

/** The right column: what was extracted and stored for the document. */
export function DocumentEvidenceAside({
  data,
  pagesCount,
  pageChunkTotal,
  pageTablesCount,
  chunks,
  citedChunkId,
  canEdit,
}: {
  data: DocumentDetail;
  pagesCount: number;
  pageChunkTotal: number;
  pageTablesCount: number;
  chunks: ChunkOut[];
  citedChunkId: string | null;
  canEdit: boolean;
}) {
  return (
    <aside aria-label="Evidence and extracted information" className="min-w-0 space-y-5">
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Evidence extracted</h2>
        <dl className="mt-2 space-y-1.5 text-xs">
          <DetailRow label="Pages" value={String(pagesCount)} />
          <DetailRow label="Sections on this page" value={String(pageChunkTotal)} />
          <DetailRow label="Tables on this page" value={String(pageTablesCount)} />
          <DetailRow label="Tables in document" value={String(data.table_count ?? 0)} />
        </dl>
      </section>

      <section>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Related records</h2>
        <dl className="mt-2 space-y-1.5 text-xs">
          <DetailRow
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
          <DetailRow
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
          {chunks.map((chunk) => (
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
          {chunks.length === 0 ? (
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
  );
}
