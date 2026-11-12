import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";

import { EmptyState, ErrorState, LoadingRows } from "@/components/common/States";
import { PageHeader } from "@/components/common/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { PAGE_SIZE, offsetFor, pageLabel } from "@/lib/pagination";
import { cn, formatDate, formatMoney, toneClasses } from "@/lib/utils";

export function ContractsPage() {
  const [search, setSearch] = useState("");
  const [supplierId, setSupplierId] = useState("all");
  const [page, setPage] = useState(0);

  const filters = useQuery({ queryKey: ["filters"], queryFn: api.filters });
  const contracts = useQuery({
    queryKey: ["contracts", search, supplierId, page],
    queryFn: () =>
      api.contracts({
        search: search || undefined,
        supplier_id: supplierId === "all" ? undefined : supplierId,
        limit: PAGE_SIZE,
        offset: offsetFor(page),
      }),
  });

  const items = contracts.data?.items ?? [];
  const total = contracts.data?.total ?? 0;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Contracts"
        description="Contract rows are versioned. An amendment supersedes the terms it changes instead of overwriting them, so both records stay visible with the page they came from."
      />

      <div className="flex flex-wrap items-end gap-3 rounded-lg border p-3">
        <div className="min-w-[220px] flex-1 space-y-1.5">
          <Label htmlFor="contract-search">Search</Label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
            <Input
              id="contract-search"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(0);
              }}
              placeholder="Contract number or title"
              className="pl-8"
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label>Supplier</Label>
          <Select
            value={supplierId}
            onValueChange={(value) => {
              setSupplierId(value);
              setPage(0);
            }}
          >
            <SelectTrigger className="w-[220px]" aria-label="Filter by supplier">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">all suppliers</SelectItem>
              {(filters.data?.suppliers ?? []).map((supplier) => (
                <SelectItem key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <p className="pb-2 text-xs text-muted-foreground" aria-live="polite">
          {contracts.data ? `${total} contract(s)` : "loading"}
        </p>
      </div>

      {contracts.isError ? <ErrorState error={contracts.error} onRetry={() => void contracts.refetch()} /> : null}
      {contracts.isLoading ? <LoadingRows rows={6} /> : null}

      {contracts.data ? (
        items.length === 0 ? (
          <EmptyState
            title="No contract matches"
            description="Ingest a supply agreement or amendment and the extracted contract record will appear here with its prices and clause structure."
          />
        ) : (
          <div className="rounded-lg border">
            <Table>
              <caption className="sr-only">Contracts with supplier, effective window, version and recorded value.</caption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Contract</TableHead>
                  <TableHead scope="col">Supplier</TableHead>
                  <TableHead scope="col">Window</TableHead>
                  <TableHead scope="col" className="text-right">
                    Version
                  </TableHead>
                  <TableHead scope="col">Status</TableHead>
                  <TableHead scope="col" className="text-right">
                    Price rows
                  </TableHead>
                  <TableHead scope="col" className="text-right">
                    Value
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((contract) => (
                  <TableRow key={contract.id}>
                    <TableCell>
                      <Link to={`/contracts/${contract.id}`} className="text-xs font-medium hover:underline">
                        {contract.contract_number}
                      </Link>
                      <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{contract.title}</p>
                    </TableCell>
                    <TableCell className="text-xs">
                      {contract.supplier_name ? (
                        contract.supplier_id ? (
                          <Link to={`/suppliers/${contract.supplier_id}`} className="hover:underline">
                            {contract.supplier_name}
                          </Link>
                        ) : (
                          contract.supplier_name
                        )
                      ) : (
                        <span className="italic text-muted-foreground">not attributed to a supplier</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs">
                      {formatDate(contract.effective_date)} to {formatDate(contract.expiry_date)}
                    </TableCell>
                    <TableCell className="tnum text-right text-xs">v{contract.version}</TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={cn("font-normal", toneClasses(contract.is_expired ? "danger" : "success"))}
                      >
                        {contract.is_expired ? "Expired" : contract.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="tnum text-right text-xs">{contract.price_count ?? 0}</TableCell>
                    <TableCell className="tnum text-right text-xs">
                      {contract.total_value ? formatMoney(contract.total_value, contract.currency) : "not recorded"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {total > PAGE_SIZE ? (
              <nav
                aria-label="Contract pages"
                className="flex flex-wrap items-center justify-between gap-2 border-t px-3 py-2"
              >
                <p className="text-xs text-muted-foreground">{pageLabel(page, total)}</p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 0}
                    onClick={() => setPage((current) => Math.max(0, current - 1))}
                  >
                    <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={offsetFor(page) + items.length >= total}
                    onClick={() => setPage((current) => current + 1)}
                  >
                    Next
                    <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                </div>
              </nav>
            ) : null}
          </div>
        )
      ) : null}
    </div>
  );
}
