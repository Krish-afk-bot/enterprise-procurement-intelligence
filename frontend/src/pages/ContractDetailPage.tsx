import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BadgeCheck, GitCompareArrows, ScrollText } from "lucide-react";

import { PageHeader, MetaItem } from "@/components/common/PageHeader";
import { SourceLink } from "@/components/common/Evidence";
import { ErrorState, LoadingRows, NotAvailable } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { cn, formatDate, formatMoney, toneClasses } from "@/lib/utils";

export function ContractDetailPage() {
  const { contractId = "" } = useParams();
  const contract = useQuery({ queryKey: ["contract", contractId], queryFn: () => api.contract(contractId) });

  if (contract.isError) return <ErrorState error={contract.error} onRetry={() => void contract.refetch()} />;
  if (contract.isLoading || !contract.data) return <LoadingRows rows={7} />;
  const data = contract.data;

  return (
    <div className="space-y-5">
      <PageHeader
        title={`${data.contract_number} v${data.version}`}
        description={data.title}
        backTo="/contracts"
        backLabel="Back to contracts"
        meta={
          <>
            <Badge variant="outline" className={cn("font-normal", toneClasses(data.is_expired ? "danger" : "success"))}>
              {data.is_expired ? "Expired" : data.status}
            </Badge>
            <MetaItem label="Supplier">
              {data.supplier_id ? (
                <Link to={`/suppliers/${data.supplier_id}`} className="hover:underline">
                  {data.supplier_name ?? "supplier record"}
                </Link>
              ) : (
                <span className="italic text-muted-foreground">not attributed</span>
              )}
            </MetaItem>
            <MetaItem label="Window">
              {formatDate(data.effective_date)} to {formatDate(data.expiry_date)}
            </MetaItem>
            <MetaItem label="Type">{data.contract_type ?? "not recorded"}</MetaItem>
            <MetaItem label="Value">
              {data.total_value ? formatMoney(data.total_value, data.currency) : "not recorded"}
            </MetaItem>
            <MetaItem label="Price rows">{data.prices.length}</MetaItem>
            <MetaItem label="Documents">{data.documents.length}</MetaItem>
          </>
        }
      />

      <Tabs defaultValue="prices">
        <TabsList>
          <TabsTrigger value="prices">Prices</TabsTrigger>
          <TabsTrigger value="versions">
            <GitCompareArrows className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Versions
          </TabsTrigger>
          <TabsTrigger value="clauses">
            <ScrollText className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Clauses
          </TabsTrigger>
          <TabsTrigger value="compliance">
            <BadgeCheck className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Compliance
          </TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
        </TabsList>

        <TabsContent value="prices">
          <div className="rounded-lg border">
            <Table>
              <caption className="sr-only">Price rows recorded against this contract, with the page each was extracted from.</caption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Product</TableHead>
                  <TableHead scope="col" className="text-right">
                    Unit price
                  </TableHead>
                  <TableHead scope="col" className="text-right">
                    Minimum quantity
                  </TableHead>
                  <TableHead scope="col" className="text-right">
                    Discount
                  </TableHead>
                  <TableHead scope="col">Effective</TableHead>
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
                    <TableCell className="tnum text-right text-xs">
                      {price.minimum_quantity ?? "not recorded"}
                    </TableCell>
                    <TableCell className="tnum text-right text-xs">
                      {price.discount_percent !== null ? `${price.discount_percent}%` : "not recorded"}
                    </TableCell>
                    <TableCell className="text-xs">{formatDate(price.effective_date)}</TableCell>
                    <TableCell className="text-xs">{price.amendment_ref ?? "original agreement"}</TableCell>
                    <TableCell>
                      <SourceLink documentId={price.source_document_id} page={price.source_page} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {data.prices.length === 0 ? (
              <p className="border-t p-4 text-xs text-muted-foreground">
                No price row has been extracted from this contract yet.
              </p>
            ) : null}
          </div>
        </TabsContent>

        <TabsContent value="versions">
          <div className="grid gap-3 md:grid-cols-2">
            {data.versions.map((version) => (
              <article key={version.id} className="rounded-lg border p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium">
                    {version.contract_number} v{version.version}
                  </p>
                  <Badge variant="outline" className="font-normal">
                    {version.relation}
                  </Badge>
                  <Badge variant="outline" className={cn("font-normal", toneClasses(version.status === "active" ? "success" : "neutral"))}>
                    {version.status}
                  </Badge>
                </div>
                <p className="mt-1.5 text-xs text-muted-foreground">{version.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatDate(version.effective_date)} to {formatDate(version.expiry_date)}
                </p>
                {version.id !== contractId ? (
                  <Link to={`/contracts/${version.id}`} className="mt-2 inline-block text-xs font-medium text-primary hover:underline">
                    Open this version
                  </Link>
                ) : (
                  <p className="mt-2 text-xs text-muted-foreground">This is the version you are viewing.</p>
                )}
              </article>
            ))}
            {data.versions.length === 0 ? (
              <NotAvailable label="No other version of this contract is recorded" />
            ) : null}
          </div>
        </TabsContent>

        <TabsContent value="clauses">
          <div className="space-y-3">
            {data.clauses.length === 0 ? (
              <NotAvailable label="No clause-numbered chunk was extracted from this contract." />
            ) : (
              data.clauses.map((clause) => (
                <article key={clause.chunk_id} className="rounded-lg border p-3.5">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    {clause.section ? <Badge variant="outline" className="font-normal">{clause.section}</Badge> : null}
                    {clause.clause ? <Badge variant="outline" className="font-normal">{clause.clause}</Badge> : null}
                    <Badge variant="outline" className="font-normal">{clause.content_type}</Badge>
                    <span className="ml-auto">
                      <SourceLink documentId={clause.document_id} page={clause.page} chunkId={clause.chunk_id}>
                        {clause.page ? `Page ${clause.page}` : "Open source"}
                      </SourceLink>
                    </span>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed">{clause.content}</p>
                </article>
              ))
            )}
          </div>
        </TabsContent>

        <TabsContent value="compliance">
          <div className="rounded-lg border">
            <Table>
              <caption className="sr-only">Compliance certificates linked to this contract.</caption>
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
                No compliance certificate is linked to this contract in the indexed documents.
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
                  {document.document_type ?? "unclassified"} · {document.status} · version {document.version} · access{" "}
                  {document.access_level}
                </p>
              </li>
            ))}
            {data.documents.length === 0 ? (
              <li className="text-xs text-muted-foreground">No document is linked to this contract.</li>
            ) : null}
          </ul>
        </TabsContent>
      </Tabs>
    </div>
  );
}
