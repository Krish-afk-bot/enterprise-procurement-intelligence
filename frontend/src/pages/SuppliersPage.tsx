import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";

import { EmptyState, ErrorState, LoadingRows } from "@/components/common/States";
import { PageHeader } from "@/components/common/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Input, Label } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { titleCase } from "@/lib/utils";

export function SuppliersPage() {
  const [search, setSearch] = useState("");
  const suppliers = useQuery({
    queryKey: ["suppliers", search],
    queryFn: () => api.suppliers({ search: search || undefined, limit: 100 }),
  });

  const items = suppliers.data?.items ?? [];

  return (
    <div className="space-y-5">
      <PageHeader
        title="Suppliers"
        description="The suppliers this workspace holds records for, with the contracts, documents and price rows recorded against each. Labels used in the source files are kept as aliases, so a name written one way in a contract and another way in a price sheet still resolves to one supplier."
      />

      <div className="flex flex-wrap items-end gap-3 rounded-lg border p-3">
        <div className="min-w-[220px] flex-1 space-y-1.5">
          <Label htmlFor="supplier-search">Search</Label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
            <Input
              id="supplier-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Supplier name"
              className="pl-8"
            />
          </div>
        </div>
        <p className="pb-2 text-xs text-muted-foreground">
          {suppliers.data ? `${suppliers.data.total} supplier(s)` : "loading"}
        </p>
      </div>

      {suppliers.isError ? <ErrorState error={suppliers.error} onRetry={() => void suppliers.refetch()} /> : null}
      {suppliers.isLoading ? <LoadingRows rows={5} /> : null}

      {suppliers.data ? (
        items.length === 0 ? (
          <EmptyState
            title="No supplier matches"
            description="Supplier records are created when a contract, amendment or price sheet that names a supplier finishes processing."
          />
        ) : (
          <div className="rounded-lg border">
            <Table>
              <caption className="sr-only">Suppliers with recorded aliases, category and how many records reference them.</caption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Supplier</TableHead>
                  <TableHead scope="col">Category</TableHead>
                  <TableHead scope="col">Region</TableHead>
                  <TableHead scope="col" className="text-right">
                    Contracts
                  </TableHead>
                  <TableHead scope="col" className="text-right">
                    Documents
                  </TableHead>
                  <TableHead scope="col" className="text-right">
                    Price rows
                  </TableHead>
                  <TableHead scope="col">Status</TableHead>
                  <TableHead scope="col" className="text-right">
                    Actions
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((supplier) => {
                  const aliases = (supplier.attributes as { aliases?: string[] } | undefined)?.aliases ?? [];
                  return (
                    <TableRow key={supplier.id}>
                      <TableCell>
                        <Link to={`/suppliers/${supplier.id}`} className="text-xs font-medium hover:underline">
                          {supplier.name}
                        </Link>
                        {supplier.is_synthetic ? (
                          <Badge variant="outline" className="ml-2 border-warning/35 font-normal text-warning">
                            demo corpus
                          </Badge>
                        ) : null}
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          {supplier.country ?? "country not recorded"}
                        </p>
                        {aliases.length > 0 ? (
                          <p className="mt-0.5 text-[11px] text-muted-foreground">
                            also recorded as {aliases.join(", ")}
                          </p>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-xs">{supplier.category ?? "not recorded"}</TableCell>
                      <TableCell className="text-xs">{supplier.region ?? "not recorded"}</TableCell>
                      <TableCell className="tnum text-right text-xs">{supplier.contract_count}</TableCell>
                      <TableCell className="tnum text-right text-xs">{supplier.document_count}</TableCell>
                      <TableCell className="tnum text-right text-xs">{supplier.price_count}</TableCell>
                      <TableCell className="text-xs">{titleCase(supplier.status)}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="outline" size="sm" asChild>
                          <Link to={`/suppliers/${supplier.id}`}>Open</Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )
      ) : null}
    </div>
  );
}
