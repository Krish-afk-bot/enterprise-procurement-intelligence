import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Trash2 } from "lucide-react";

import { ErrorState, LoadingRows } from "@/components/common/States";
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
import { DocumentEvidenceAside } from "@/features/documents/DocumentEvidenceAside";
import { DocumentPageViewer } from "@/features/documents/DocumentPageViewer";
import { DocumentSidebar } from "@/features/documents/DocumentSidebar";
import { EditDetailsDialog } from "@/features/documents/EditDetailsDialog";
import { UploadVersionDialog } from "@/features/documents/UploadVersionDialog";
import { api } from "@/lib/api";
import { NOT_RECORDED, cn, documentLifecycle, documentTypeLabel, formatDate, titleCase, toneClasses } from "@/lib/utils";
import { useAuth } from "@/store/auth";

export function DocumentDetailPage() {
  const { documentId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const user = useAuth((state) => state.user);

  const pageParam = Number(searchParams.get("page") ?? "1");
  const citedChunkId = searchParams.get("chunk");
  const [page, setPage] = useState(Number.isFinite(pageParam) && pageParam > 0 ? pageParam : 1);

  const document = useQuery({ queryKey: ["document", documentId], queryFn: () => api.document(documentId) });
  const pageChunks = useQuery({
    queryKey: ["document-chunks", documentId, page],
    queryFn: () => api.documentChunks(documentId, { page, limit: 200 }),
    enabled: Boolean(documentId),
  });

  const pages = document.data?.pages ?? [];
  const maxPage = Math.max(pages.length, 1);
  const currentPage = useMemo(() => pages.find((item) => item.page_number === page) ?? null, [pages, page]);
  const chunks = pageChunks.data?.items ?? [];

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

  const citedChunk = chunks.find((chunk) => chunk.id === citedChunkId) ?? null;

  if (document.isError) return <ErrorState error={document.error} onRetry={() => void document.refetch()} />;
  if (document.isLoading || !document.data) return <LoadingRows rows={7} />;
  const data = document.data;
  const lifecycle = documentLifecycle(data);
  const canEdit = Boolean(user?.permissions?.includes("documents:write"));
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
        <DocumentSidebar data={data} page={page} goToPage={goToPage} canEdit={canEdit} />
        <DocumentPageViewer
          documentId={documentId}
          data={data}
          page={page}
          maxPage={maxPage}
          goToPage={goToPage}
          currentPage={currentPage}
          citedChunk={citedChunk}
          citedChunkId={citedChunkId}
        />
        <DocumentEvidenceAside
          data={data}
          pagesCount={pages.length}
          pageChunkTotal={pageChunks.data?.total ?? 0}
          pageTablesCount={currentPage?.tables.length ?? 0}
          chunks={chunks}
          citedChunkId={citedChunkId}
          canEdit={canEdit}
        />
      </div>
    </div>
  );
}
