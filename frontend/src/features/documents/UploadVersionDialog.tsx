import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Upload } from "lucide-react";

import { ErrorState } from "@/components/common/States";
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
import { api } from "@/lib/api";
import type { DocumentDetail } from "@/lib/types";

/** Upload a new version while keeping every earlier version and its citations. */
export function UploadVersionDialog({ document }: { document: DocumentDetail }) {
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
