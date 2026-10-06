import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BadgeCheck, CalendarClock, FileStack, Receipt } from "lucide-react";

import { PageHeader, MetaItem } from "@/components/common/PageHeader";
import { SourceLink } from "@/components/common/Evidence";
import { ErrorState, LoadingRows, NotAvailable } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/utils";

export function SupplierDetailPage() {
  const { supplierId = "" } = useParams();
  const supplier = useQuery({ queryKey: ["supplier", supplierId], queryFn: () => api.supplier(supplierId) });

  if (supplier.isError) return <ErrorState error={supplier.error} onRetry={() => void supplier.refetch()} />;
  if (supplier.isLoading || !supplier.data) return <LoadingRows rows={7} />;
  const data = supplier.data;
  const aliases = (data.attributes as { aliases?: string[] } | undefined)?.aliases ?? [];

  return (
    <div className="space-y-5">
      <PageHeader
        title={data.name}
        description={`${data.category ?? "uncategorised"} supplier`}
        backTo="/suppliers"
        backLabel="Back to suppliers"
        meta={
          <>
            <MetaItem label="Status">{data.status}</MetaItem>
            <MetaItem label="Region">{data.region ?? "not recorded"}</MetaItem>
            <MetaItem label="Country">{data.country ?? "not recorded"}</MetaItem>
            <MetaItem label="Contracts">{data.contracts.length}</MetaItem>
            <MetaItem label="Documents">{data.documents.length}</MetaItem>
            <MetaItem label="Price rows">{data.prices.length}</MetaItem>
            <MetaItem label="Compliance">{data.compliance.length}</MetaItem>
            <MetaItem label="Aliases">{aliases.length > 0 ? aliases.join(", ") : "none recorded"}</MetaItem>
            {data.is_synthetic ? (
              <Badge variant="outline" className="border-warning/35 font-normal text-warning">
                demo corpus
              </Badge>
            ) : null}
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" asChild>
          <Link to="/compare">Compare with another supplier</Link>
        </Button>
        <Button variant="outline" size="sm" asChild>
          <Link to="/graph">Explore relationships</Link>
        </Button>
        <Button variant="outline" size="sm" asChild>
          <Link to={`/documents?supplier=${data.id}`}>Documents for this supplier</Link>
        </Button>
      </div>

      <section aria-labelledby="current-price-heading" className="rounded-lg border p-4">
        <h2 id="current-price-heading" className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <Receipt className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          Price currently in force
        </h2>
        {data.current_price ? (
          <>
            <p className="mt-2 text-2xl font-semibold tracking-tight">
              {formatMoney(data.current_price.unit_price, data.current_price.currency)}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {data.current_price.product_name ?? "product not recorded"}
              {data.current_price.effective_date ? ` · effective ${formatDate(data.current_price.effective_date)}` : ""}
              {data.current_price.amendment_ref ? ` · ${data.current_price.amendment_ref}` : " · original agreement"}
            </p>
            <p className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              <span className="text-muted-foreground">
                Source: {data.current_price.document_name ?? "document not recorded"}
              </span>
              <SourceLink
                documentId={data.documents.find((document) => document.title === data.current_price?.document_name)?.id ?? null}
                page={data.current_price.page}
              />
            </p>
          </>
        ) : (
          <p className="mt-2">
            <NotAvailable
              label={
                data.prices.length > 0
                  ? `No price row is marked current. The ${data.prices.length} recorded row(s) are listed under Prices with their effective dates.`
                  : "No price row is recorded for this supplier."
              }
            />
          </p>
        )}
      </section>

      <Tabs defaultValue="contracts">
        <TabsList>
          <TabsTrigger value="contracts">Contracts</TabsTrigger>
          <TabsTrigger value="documents">
            <FileStack className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Documents
          </TabsTrigger>
          <TabsTrigger value="prices">Pricing</TabsTrigger>
          <TabsTrigger value="compliance">
            <BadgeCheck className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Compliance
          </TabsTrigger>
          <TabsTrigger value="timeline">
            <CalendarClock className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Timeline
          </TabsTrigger>
        </TabsList>

        <TabsContent value="prices">
          <div className="rounded-lg border">
            <Table>
              <caption className="sr-only">Every price row recorded for this supplier with its effective period and source page.</caption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Product</TableHead>
                  <TableHead scope="col" className="text-right">
                    Unit price
                  </TableHead>
                  <TableHead scope="col" className="text-right">
                    Minimum quantity
                  </TableHead>
                  <TableHead scope="col">Effective</TableHead>
                  <TableHead scope="col">Expiry</TableHead>
                  <TableHead scope="col">Set by</TableHead>
                  <TableHead scope="col">Source</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.prices.map((price) => (
                  <TableRow key={price.id}>
                    <TableCell className="text-xs">{price.product_name ?? "not recorded"}</TableCell>
                    <TableCell className="tnum text-right text-xs font-medium">
                      {formatMoney(price.unit_price, price.currency)}
                    </TableCell>
                    <TableCell className="tnum text-right text-xs">{price.minimum_quantity ?? "not recorded"}</TableCell>
                    <TableCell className="text-xs">{formatDate(price.effective_date)}</TableCell>
                    <TableCell className="text-xs">{formatDate(price.expiry_date)}</TableCell>
                    <TableCell className="text-xs">{price.amendment_ref ?? "original agreement"}</TableCell>
                    <TableCell>
                      <SourceLink documentId={price.source_document_id} page={price.source_page} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {data.prices.length === 0 ? (
              <p className="border-t p-4 text-xs text-muted-foreground">No price row recorded for this supplier.</p>
            ) : null}
          </div>
        </TabsContent>

        <TabsContent value="contracts">
          <ul className="grid gap-3 md:grid-cols-2">
            {data.contracts.map((contract) => (
              <li key={contract.id} className="rounded-lg border p-4">
                <Link to={`/contracts/${contract.id}`} className="text-sm font-medium hover:underline">
                  {contract.contract_number}
                </Link>
                <p className="mt-1 text-xs text-muted-foreground">{contract.title}</p>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  {formatDate(contract.effective_date)} to {formatDate(contract.expiry_date)} · version {contract.version} ·{" "}
                  {contract.status}
                </p>
                {contract.total_value ? (
                  <p className="mt-1 text-xs">{formatMoney(contract.total_value, contract.currency)}</p>
                ) : null}
              </li>
            ))}
            {data.contracts.length === 0 ? (
              <li className="text-xs text-muted-foreground">No contract is recorded for this supplier.</li>
            ) : null}
          </ul>
        </TabsContent>

        <TabsContent value="compliance">
          <div className="rounded-lg border">
            <Table>
              <caption className="sr-only">Compliance certificates recorded for this supplier.</caption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Certificate</TableHead>
                  <TableHead scope="col">Number</TableHead>
                  <TableHead scope="col">Issued</TableHead>
                  <TableHead scope="col">Expiry</TableHead>
                  <TableHead scope="col">Status</TableHead>
                  <TableHead scope="col">Source</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.compliance.map((certificate) => (
                  <TableRow key={certificate.id}>
                    <TableCell className="text-xs font-medium">{certificate.certificate_type}</TableCell>
                    <TableCell className="text-xs">{certificate.certificate_number ?? "not recorded"}</TableCell>
                    <TableCell className="text-xs">{formatDate(certificate.issued_date)}</TableCell>
                    <TableCell className="text-xs">{formatDate(certificate.expiry_date)}</TableCell>
                    <TableCell className="text-xs">{certificate.status}</TableCell>
                    <TableCell>
                      <SourceLink documentId={certificate.source_document_id} page={certificate.source_page} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {data.compliance.length === 0 ? (
              <p className="border-t p-4 text-xs text-muted-foreground">
                No compliance certificate is recorded for this supplier in the indexed documents.
              </p>
            ) : null}
          </div>
        </TabsContent>

        <TabsContent value="documents">
          <ul className="grid gap-3 md:grid-cols-2">
            {data.documents.map((document) => (
              <li key={document.id} className="rounded-lg border p-4">
                <Link to={`/documents/${document.id}`} className="text-sm font-medium hover:underline">
                  {document.title || document.filename}
                </Link>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  {document.document_type ?? "unclassified"} · {document.status} · access {document.access_level}
                </p>
              </li>
            ))}
            {data.documents.length === 0 ? (
              <li className="text-xs text-muted-foreground">No document is linked to this supplier.</li>
            ) : null}
          </ul>
        </TabsContent>

        <TabsContent value="timeline">
          {data.timeline.length === 0 ? (
            <NotAvailable label="No dated price events are recorded for this supplier." />
          ) : (
            <ol className="space-y-3">
              {data.timeline.map((entry, index) => (
                <li key={index} className="flex gap-3 border-l pl-3">
                  <div>
                    <p className="text-xs font-medium">{formatDate(entry.date)}</p>
                    <p className="text-xs text-muted-foreground">{entry.label}</p>
                    {entry.document_name ? (
                      <p className="mt-0.5 text-[11px] text-muted-foreground">
                        {entry.document_name}
                        {entry.page ? ` · page ${entry.page}` : ""}
                      </p>
                    ) : null}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
