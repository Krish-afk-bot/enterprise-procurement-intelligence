import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ErrorState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import {
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input, Label } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Switch } from "@/components/ui/misc";
import { stageLabel } from "@/features/documents/stages";
import { api } from "@/lib/api";
import type { UploadResponse } from "@/lib/types";
import { DOCUMENT_TYPE_LABELS } from "@/lib/utils";

/** Upload a new document, or a duplicate the API returns instead of re-ingesting. */
export function UploadDocumentDialog({ onClose }: { onClose: () => void }) {
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
