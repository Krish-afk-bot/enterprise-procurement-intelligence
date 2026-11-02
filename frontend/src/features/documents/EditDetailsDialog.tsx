import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PencilLine } from "lucide-react";

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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/misc";
import { api } from "@/lib/api";
import type { DocumentDetail, DocumentSummary } from "@/lib/types";
import { DOCUMENT_TYPE_LABELS, documentTypeLabel, titleCase } from "@/lib/utils";
import { useAuth } from "@/store/auth";

const ACCESS_LEVELS = ["public", "internal", "confidential", "restricted"] as const;

/** Edit the recorded document details without touching the file itself. */
export function EditDetailsDialog({ document, trigger }: { document: DocumentDetail; trigger?: React.ReactNode }) {
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
