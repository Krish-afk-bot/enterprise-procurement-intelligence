import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, TriangleAlert, X } from "lucide-react";

import { CitationChip } from "@/components/common/Evidence";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { MICROCOPY, microcopyPlain } from "@/lib/microcopy";
import { useMood } from "@/lib/useMood";
import { cn, formatDate, plural, titleCase } from "@/lib/utils";

const DIMENSION_LABELS: Record<string, string> = {
  unit_price: "Unit price",
  currency: "Currency",
  minimum_quantity: "Minimum order quantity",
  discount_percent: "Discount",
  payment_terms: "Payment terms",
  delivery_terms: "Delivery terms",
  price_effective_date: "Price effective",
  price_amendment: "Price set by",
  contract_number: "Contract",
  contract_status: "Contract status",
  contract_version: "Contract version",
  contract_expiry: "Contract expiry",
  contract_duration: "Contract duration (days)",
  renewal: "Renewal",
  compliance: "Compliance",
};

export function ComparePage() {
  const [selected, setSelected] = useState<string[]>([]);
  const [productId, setProductId] = useState("all");
  const [asOf, setAsOf] = useState("");

  const filters = useQuery({ queryKey: ["filters"], queryFn: api.filters });
  const suppliers = useQuery({ queryKey: ["suppliers", "compare"], queryFn: () => api.suppliers({ limit: 100 }) });

  const product = (filters.data?.products ?? []).find((item) => item.id === productId) ?? null;
  const supplierRows = suppliers.data?.items ?? [];
  const selectedSuppliers = supplierRows.filter((supplier) => selected.includes(supplier.id));

  const compare = useMutation({
    mutationFn: () =>
      api.compare({
        supplier_ids: selected,
        product_query: product?.name ?? null,
        as_of: asOf || null,
      }),
  });

  useMood(
    compare.isPending
      ? "loading"
      : compare.isError
        ? "error"
        : compare.data
          ? compare.data.columns.length > 0
            ? "found"
            : "empty"
          : null,
  );

  function toggle(id: string) {
    setSelected((current) => (current.includes(id) ? current.filter((value) => value !== id) : [...current, id]));
  }

  const dimensions = compare.data?.dimensions ?? Object.keys(DIMENSION_LABELS);
  const ready = selected.length >= 2;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Compare suppliers"
        description="Compare what the stored records say about two or more suppliers: prices, contract terms, compliance and the pages each value was read from. Values are reported as recorded; nothing is ranked and no supplier is declared a winner."
      />

      <section aria-labelledby="compare-setup-heading" className="space-y-4 rounded-lg border p-4">
        <h2 id="compare-setup-heading" className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Set up the comparison
        </h2>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Product</Label>
            <Select value={productId} onValueChange={setProductId}>
              <SelectTrigger aria-label="Product to compare">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">every recorded product</SelectItem>
                {(filters.data?.products ?? []).map((item) => (
                  <SelectItem key={item.id} value={item.id}>
                    {item.name}
                    {item.sku ? ` · ${item.sku}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground">
              {filters.data
                ? `${plural(filters.data.products.length, "product")} recorded in the workspace. Choose one to compare prices for that item only.`
                : "Loading products"}
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="compare-asof">Prices as of (optional)</Label>
            <Input
              id="compare-asof"
              type="date"
              value={asOf}
              onChange={(event) => setAsOf(event.target.value)}
              className="w-full sm:w-44"
            />
            <p className="text-[11px] text-muted-foreground">
              Leave empty to use the price rows that are current today. A date restricts the comparison to rows whose
              recorded term covers it.
            </p>
          </div>
        </div>

        <div className="space-y-2 border-t pt-3">
          <div className="flex flex-wrap items-baseline gap-2">
            <h3 className="text-xs font-medium">Step 2 · Choose the suppliers</h3>
            <p className="text-[11px] text-muted-foreground">
              {selected.length === 0
                ? "none selected yet — pick at least two below"
                : `${plural(selected.length, "supplier")} selected`}
            </p>
          </div>

          {suppliers.isLoading ? (
            <LoadingState label="Loading suppliers" />
          ) : supplierRows.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No supplier record exists yet. Supplier records are created when a contract or price sheet that names a
              supplier finishes processing.
            </p>
          ) : (
            <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {supplierRows.map((supplier) => {
                const active = selected.includes(supplier.id);
                return (
                  <li key={supplier.id}>
                    <button
                      type="button"
                      onClick={() => toggle(supplier.id)}
                      aria-pressed={active}
                      className={cn(
                        "flex w-full items-start gap-2 rounded-md border p-2.5 text-left text-xs transition-all duration-control",
                        // A chosen supplier lifts slightly: depth as selection feedback,
                        // never as a ranking.
                        active ? "lift-selected border-primary/45 bg-primary/5" : "hover:-translate-y-px hover:bg-accent",
                      )}
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border",
                          active ? "border-primary bg-primary text-primary-foreground" : "border-input",
                        )}
                        aria-hidden="true"
                      >
                        {active ? <CheckCircle2 className="h-3 w-3" /> : null}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate font-medium">{supplier.name}</span>
                        <span className="block text-[11px] text-muted-foreground">
                          {[supplier.category, supplier.region, supplier.country].filter(Boolean).join(" · ") ||
                            "no category or region recorded"}
                        </span>
                        <span className="block text-[11px] text-muted-foreground">
                          {plural(supplier.contract_count ?? 0, "contract")} · {plural(supplier.price_count ?? 0, "price row")} ·{" "}
                          {plural(supplier.document_count ?? 0, "document")}
                        </span>
                      </span>
                      <span className="sr-only">{active ? "Selected for comparison" : "Not selected"}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          <div className="rounded-md border bg-muted/40 p-3">
            <h4 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Selected for this comparison
            </h4>
            {selectedSuppliers.length === 0 ? (
              <p className="mt-1.5 text-xs">
                <span className="font-medium">{MICROCOPY.needTwoSuppliers}</span>{" "}
                <span className="text-muted-foreground">{microcopyPlain("needTwoSuppliers")}</span>
              </p>
            ) : (
              <ul className="mt-1.5 flex flex-wrap gap-1.5">
                {selectedSuppliers.map((supplier) => (
                  <li key={supplier.id}>
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/40 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary">
                      {supplier.name}
                      <button
                        type="button"
                        onClick={() => toggle(supplier.id)}
                        aria-label={`Remove ${supplier.name} from the comparison`}
                        className="rounded-full p-0.5 hover:bg-primary/15"
                      >
                        <X className="h-3 w-3" aria-hidden="true" />
                      </button>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              disabled={!ready || compare.isPending}
              onClick={() => compare.mutate()}
              aria-describedby="compare-readiness"
            >
              {compare.isPending ? "Comparing" : "Compare selected suppliers"}
            </Button>
            <p id="compare-readiness" className="text-[11px] text-muted-foreground">
              {ready
                ? `Ready: ${plural(selected.length, "supplier")}${product ? ` · ${product.name}` : " · all products"}${asOf ? ` · as of ${formatDate(asOf)}` : ""}. Every value below is reported as recorded; nothing is ranked.`
                : `${MICROCOPY.needTwoSuppliers} ${microcopyPlain("needTwoSuppliers")}`}
            </p>
          </div>
        </div>
      </section>

      {compare.isError ? <ErrorState error={compare.error} onRetry={() => compare.mutate()} /> : null}
      {compare.isPending ? <LoadingState label="Reading the stored rows for the selected suppliers" /> : null}

      {compare.data ? (
        compare.data.columns.length === 0 ? (
          <EmptyState
            title="Nothing to compare"
            description={compare.data.unresolved.join(" ") || "No supplier row could be resolved from the selection."}
          />
        ) : (
          <>
            <p className="text-xs text-muted-foreground">
              Comparing {compare.data.columns.map((column) => column.supplier_name).join(" against ")}
              {product ? ` for ${product.name}` : ""}. Each cell states where its value came from; a dimension with no
              matching record is reported as not found.
            </p>

            {compare.data.unresolved.length > 0 ? (
              <div className="flex items-start gap-2 rounded-md border border-warning/35 bg-warning/5 p-3 text-xs">
                <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" aria-hidden="true" />
                <div>
                  <p className="font-medium">Unresolved input</p>
                  {compare.data.unresolved.map((note, index) => (
                    <p key={index} className="text-muted-foreground">
                      {note}
                    </p>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="rounded-lg border">
              <Table>
                <caption className="sr-only">
                  Recorded procurement dimensions for the selected suppliers, with the source of every value. No ranking is
                  applied.
                </caption>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col" className="w-[200px]">
                      What is compared
                    </TableHead>
                    {compare.data.columns.map((column) => (
                      <TableHead key={column.supplier_name} scope="col">
                        {column.supplier_name}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dimensions.map((dimension) => (
                    <TableRow key={dimension}>
                      <TableHead scope="row" className="text-xs font-medium normal-case tracking-normal">
                        {DIMENSION_LABELS[dimension] ?? titleCase(dimension)}
                      </TableHead>
                      {compare.data.columns.map((column) => {
                        const cell = column.cells[dimension];
                        const unavailable = !cell || cell.source === "unavailable";
                        return (
                          <TableCell key={column.supplier_name} className="align-top text-xs">
                            <p className={cn(unavailable ? "italic text-muted-foreground" : "font-medium")}>
                              {unavailable ? cell?.formatted ?? "Not found in the indexed documents" : cell.formatted}
                            </p>
                            <div className="mt-1 flex flex-wrap items-center gap-1">
                              {cell?.source === "derived" ? (
                                <Badge variant="outline" className="font-normal text-muted-foreground">
                                  computed from records
                                </Badge>
                              ) : null}
                              {cell?.source === "stored" ? (
                                <Badge variant="outline" className="font-normal text-muted-foreground">
                                  read from a stored row
                                </Badge>
                              ) : null}
                              {(cell?.citations ?? []).map((citation, index) => (
                                <CitationChip key={citation.chunk_id ?? index} citation={citation} />
                              ))}
                            </div>
                            {cell?.notes && cell.notes.length > 0 ? (
                              <p className="mt-1 text-[11px] italic text-muted-foreground">{cell.notes.join(" ")}</p>
                            ) : null}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {compare.data.notes.length > 0 ? (
              <details className="rounded-lg border p-3 text-xs text-muted-foreground">
                <summary className="cursor-pointer font-medium text-foreground">How this comparison was produced</summary>
                <ul className="mt-1.5 space-y-1">
                  {compare.data.notes.map((note, index) => (
                    <li key={index}>{note}</li>
                  ))}
                </ul>
              </details>
            ) : null}
          </>
        )
      ) : null}
    </div>
  );
}
