import { Search } from "lucide-react";

import { Input, Label } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Switch } from "@/components/ui/misc";
import { DOCUMENT_TYPE_LABELS } from "@/lib/utils";

export const BUSINESS_STATES = [
  "all",
  "Active",
  "Expires soon",
  "Expired",
  "Superseded",
  "Processing",
  "Needs attention",
  "Not available",
] as const;

export interface DocumentFilterValues {
  search: string;
  documentType: string;
  supplierId: string;
  businessState: string;
  includeSynthetic: boolean;
}

/** Search, status, type, supplier and demo-corpus filters for the document list. */
export function DocumentFilters({
  values,
  onChange,
  suppliers,
}: {
  values: DocumentFilterValues;
  onChange: <K extends keyof DocumentFilterValues>(key: K, value: DocumentFilterValues[K]) => void;
  suppliers: { id: string; name: string }[];
}) {
  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border p-3">
      <div className="min-w-[220px] flex-1 space-y-1.5">
        <Label htmlFor="document-search">Search</Label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
          <Input
            id="document-search"
            value={values.search}
            onChange={(event) => onChange("search", event.target.value)}
            placeholder="Title or filename"
            className="pl-8"
          />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label>Status</Label>
        <Select value={values.businessState} onValueChange={(value) => onChange("businessState", value)}>
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
        <Select value={values.documentType} onValueChange={(value) => onChange("documentType", value)}>
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
        <Select value={values.supplierId} onValueChange={(value) => onChange("supplierId", value)}>
          <SelectTrigger className="w-[200px]" aria-label="Filter by supplier">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">all suppliers</SelectItem>
            {suppliers.map((supplier) => (
              <SelectItem key={supplier.id} value={supplier.id}>
                {supplier.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex items-center gap-2 pb-1.5">
        <Switch
          id="documents-synthetic"
          checked={values.includeSynthetic}
          onCheckedChange={(value) => onChange("includeSynthetic", value)}
        />
        <label htmlFor="documents-synthetic" className="text-xs text-muted-foreground">
          include demo corpus
        </label>
      </div>
    </div>
  );
}
