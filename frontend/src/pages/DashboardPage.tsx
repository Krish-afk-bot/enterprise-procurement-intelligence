import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BadgeCheck, Clock, FileStack, MessagesSquare, TriangleAlert, Upload, Users } from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingRows } from "@/components/common/States";
import { EcosystemSection } from "@/components/three/EcosystemSection";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import type { DocumentSummary } from "@/lib/types";
import {
  EXPIRING_SOON_DAYS,
  NOT_RECORDED,
  activityLabel,
  cn,
  daysUntilDate,
  documentLifecycle,
  documentTypeLabel,
  formatDate,
  formatDateTime,
  formatNumber,
  plural,
  titleCase,
  toneClasses,
} from "@/lib/utils";
import { useAuth } from "@/store/auth";

const PROCESSING_STATUSES = ["queued", "uploaded", "processing", "running", "pending"];
const ATTENTION_STATUSES = ["failed", "needs_review"];

export function DashboardPage() {
  const user = useAuth((state) => state.user);
  const canSeeActivity = Boolean(user?.permissions?.includes("audit:read"));
  const canAdminister = Boolean(user?.permissions?.includes("admin:write"));

  const documents = useQuery({
    queryKey: ["documents", "overview"],
    queryFn: () => api.documents({ limit: 200 }),
    refetchInterval: 20_000,
  });
  const contracts = useQuery({ queryKey: ["contracts", "overview"], queryFn: () => api.contracts({ limit: 100 }) });
  const suppliers = useQuery({
    queryKey: ["suppliers", "overview"],
    queryFn: () => api.suppliers({ limit: 100 }),
  });
  const activity = useQuery({
    queryKey: ["audit", "overview"],
    queryFn: () => api.audit({ limit: 8 }),
    enabled: canSeeActivity,
  });

  const documentItems = documents.data?.items ?? [];
  const contractItems = contracts.data?.items ?? [];

  const derived = useMemo(() => {
    const needingAttention = documentItems.filter((item) => ATTENTION_STATUSES.includes(item.status));
    const processing = documentItems.filter((item) => PROCESSING_STATUSES.includes(item.status));
    const expiring = documentItems
      .map((item) => ({ item, days: daysUntilDate(item.expiry_date) }))
      .filter((row): row is { item: DocumentSummary; days: number } => row.days !== null && row.days >= 0 && row.days <= EXPIRING_SOON_DAYS)
      .sort((a, b) => a.days - b.days);
    const recentlyUpdated = [...documentItems]
      .sort((a, b) => new Date(b.updated_at ?? b.created_at ?? 0).getTime() - new Date(a.updated_at ?? a.created_at ?? 0).getTime())
      .slice(0, 6);
    const contractsExpiring = contractItems
      .map((contract) => ({ contract, days: daysUntilDate(contract.expiry_date) }))
      .filter((row): row is { contract: (typeof contractItems)[number]; days: number } => row.days !== null && row.days >= 0 && row.days <= EXPIRING_SOON_DAYS)
      .sort((a, b) => a.days - b.days);
    const activeContracts = contractItems.filter((contract) => documentLifecycle({ status: "indexed", expiry_date: contract.expiry_date, effective_date: contract.effective_date }).label === "Active");
    return { needingAttention, processing, expiring, recentlyUpdated, contractsExpiring, activeContracts };
  }, [documentItems, contractItems]);

  const figures = [
    { label: "Documents", value: documentItems.length, detail: `${formatNumber(documents.data?.total ?? documentItems.length)} in the repository` },
    { label: "Active contracts", value: derived.activeContracts.length, detail: `${formatNumber(contractItems.length)} contract records` },
    { label: "Suppliers", value: suppliers.data?.total ?? suppliers.data?.items.length ?? 0, detail: "records linked to documents" },
    {
      label: "Expiring within 90 days",
      value: derived.expiring.length,
      detail: derived.expiring[0] ? `next: ${derived.expiring[0].item.title || derived.expiring[0].item.filename}` : "nothing recorded",
    },
    {
      label: "Needs attention",
      value: derived.needingAttention.length,
      detail: derived.needingAttention.length > 0 ? "processing reported a problem" : "no failed processing",
    },
    {
      label: "Still processing",
      value: derived.processing.length,
      detail: derived.processing.length > 0 ? "being read and indexed" : "nothing in the queue",
    },
  ];

  if (documents.isError) return <ErrorState error={documents.error} onRetry={() => void documents.refetch()} />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Overview"
        description="Where your procurement documents, contracts and suppliers stand today, and how they connect. Every figure is read from the workspace database; a value that is not recorded is labelled rather than shown as zero."
        actions={
          <>
            <Button variant="outline" size="sm" asChild>
              <Link to="/documents">
                <Upload className="h-3.5 w-3.5" aria-hidden="true" />
                Upload document
              </Link>
            </Button>
            <Button size="sm" asChild>
              <Link to="/ask">
                Ask a question
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </Button>
          </>
        }
      />

      {documents.isLoading ? <LoadingRows rows={4} /> : null}

      {/* The ecosystem band sits above the figures: it answers "what is in this
          workspace and how does it fit together" before it answers "how many". */}
      <EcosystemSection />

      <section aria-labelledby="figures-heading" className="rounded-lg border">
        <h2 id="figures-heading" className="border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Procurement at a glance
        </h2>
        <dl className="grid gap-px bg-border sm:grid-cols-2 lg:grid-cols-3">
          {figures.map((figure) => (
            <div key={figure.label} className="bg-card p-4">
              <dt className="text-xs text-muted-foreground">{figure.label}</dt>
              <dd className="mt-1">
                <span className="tnum text-xl font-semibold tracking-tight">{formatNumber(figure.value)}</span>
                <span className="ml-2 text-[11px] text-muted-foreground">{figure.detail}</span>
              </dd>
            </div>
          ))}
        </dl>
      </section>

      {derived.needingAttention.length > 0 || derived.expiring.length > 0 ? (
        <div className="grid gap-5 lg:grid-cols-2">
          {derived.needingAttention.length > 0 ? (
            <section aria-labelledby="attention-heading" className="rounded-lg border border-destructive/35 bg-destructive/5 p-4">
              <h2 id="attention-heading" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-destructive">
                <TriangleAlert className="h-3.5 w-3.5" aria-hidden="true" />
                Needs attention
              </h2>
              <p className="mt-1 text-[11px] text-muted-foreground">
                Processing reported a problem. The document keeps its error message and its pages are not searchable until
                it is re-indexed.
              </p>
              <ul className="mt-2 space-y-1.5 text-xs">
                {derived.needingAttention.slice(0, 5).map((item) => (
                  <li key={item.id} className="flex flex-wrap items-baseline gap-2">
                    <Link to={`/documents/${item.id}`} className="font-medium hover:underline">
                      {item.title || item.filename}
                    </Link>
                    <Badge variant="outline" className={cn("font-normal", toneClasses("danger"))}>
                      {item.status === "needs_review" ? "Needs review" : "Processing failed"}
                    </Badge>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {derived.expiring.length > 0 ? (
            <section aria-labelledby="expiring-heading" className="rounded-lg border p-4">
              <h2 id="expiring-heading" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                Expiring within 90 days
              </h2>
              <p className="mt-1 text-[11px] text-muted-foreground">
                Based on the expiry date recorded on each document. Documents without a recorded expiry date are not
                listed here.
              </p>
              <ul className="mt-2 space-y-1.5 text-xs">
                {derived.expiring.slice(0, 5).map(({ item, days }) => (
                  <li key={item.id} className="flex flex-wrap items-baseline gap-2">
                    <Link to={`/documents/${item.id}`} className="font-medium hover:underline">
                      {item.title || item.filename}
                    </Link>
                    <span className="text-muted-foreground">
                      {item.supplier_name ? `${item.supplier_name} · ` : ""}
                      expires {formatDate(item.expiry_date)} ({plural(days, "day")})
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      ) : null}

      {/* `min-w-0` on the grid items: without it a table's min-content width
          widens the whole page on a narrow screen instead of scrolling. */}
      <div className="grid gap-5 lg:grid-cols-2">
        <section aria-labelledby="recent-documents-heading" className="min-w-0 rounded-lg border">
          <div className="flex items-center justify-between gap-3 border-b px-4 py-2.5">
            <h2 id="recent-documents-heading" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <FileStack className="h-3.5 w-3.5" aria-hidden="true" />
              Recently updated documents
            </h2>
            <Link to="/documents" className="text-[11px] font-medium text-primary hover:underline">
              All documents
            </Link>
          </div>
          {documents.isLoading ? (
            <div className="p-4">
              <LoadingRows rows={4} />
            </div>
          ) : documentItems.length === 0 ? (
            <div className="p-4">
              <EmptyState
                icon={FileStack}
                title="No document has been uploaded"
                description="Upload a supplier agreement, an amendment or a pricing sheet and it becomes searchable with page-level citations."
                action={
                  <Button size="sm" asChild>
                    <Link to="/documents">Upload a document</Link>
                  </Button>
                }
              />
            </div>
          ) : (
            <Table>
              <caption className="sr-only">The six documents that changed most recently, with their type and state.</caption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Document</TableHead>
                  <TableHead scope="col">Type</TableHead>
                  <TableHead scope="col">Status</TableHead>
                  <TableHead scope="col">Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {derived.recentlyUpdated.map((item) => {
                  const lifecycle = documentLifecycle(item);
                  return (
                    <TableRow key={item.id}>
                      <TableCell>
                        <Link to={`/documents/${item.id}`} className="text-xs font-medium hover:underline">
                          {item.title || item.filename}
                        </Link>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          {item.supplier_name ?? "supplier not linked"}
                        </p>
                      </TableCell>
                      <TableCell className="text-xs">{documentTypeLabel(item.document_type)}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={cn("font-normal", toneClasses(lifecycle.tone))} title={lifecycle.basis}>
                          {lifecycle.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-[11px] text-muted-foreground">{formatDateTime(item.updated_at)}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </section>

        <section aria-labelledby="contracts-heading" className="min-w-0 rounded-lg border">
          <div className="flex items-center justify-between gap-3 border-b px-4 py-2.5">
            <h2 id="contracts-heading" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
              Contracts
            </h2>
            <Link to="/contracts" className="text-[11px] font-medium text-primary hover:underline">
              All contracts
            </Link>
          </div>
          {contracts.isLoading ? (
            <div className="p-4">
              <LoadingRows rows={4} />
            </div>
          ) : contractItems.length === 0 ? (
            <div className="p-4">
              <EmptyState
                icon={BadgeCheck}
                title="No contract record yet"
                description="Contracts are created when an agreement that names a contract number finishes ingesting."
              />
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Contract records with their supplier, recorded term and state.</caption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Contract</TableHead>
                  <TableHead scope="col">Supplier</TableHead>
                  <TableHead scope="col">Expiry</TableHead>
                  <TableHead scope="col">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {contractItems.slice(0, 6).map((contract) => (
                  <TableRow key={contract.id}>
                    <TableCell>
                      <Link to={`/contracts/${contract.id}`} className="text-xs font-medium hover:underline">
                        {contract.contract_number}
                      </Link>
                      <p className="mt-0.5 text-[11px] text-muted-foreground">{contract.title}</p>
                    </TableCell>
                    <TableCell className="text-xs">{contract.supplier_name ?? NOT_RECORDED}</TableCell>
                    <TableCell className="text-xs">{formatDate(contract.expiry_date)}</TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={cn("font-normal", toneClasses(contract.is_expired ? "warning" : "neutral"))}
                      >
                        {titleCase(contract.status)}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>
      </div>

      {canSeeActivity ? (
        <section aria-labelledby="activity-heading" className="rounded-lg border">
          <h2 id="activity-heading" className="border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Recent activity
          </h2>
          <div className="p-4">
            {activity.isError ? (
              <ErrorState error={activity.error} onRetry={() => void activity.refetch()} />
            ) : activity.isLoading ? (
              <LoadingRows rows={3} />
            ) : (
              <ul className="space-y-2 text-xs">
                {(activity.data?.items ?? []).map((entry) => (
                  <li key={entry.id} className="flex flex-wrap items-baseline gap-2">
                    <span className="font-medium">{activityLabel(entry.action)}</span>
                    <span className="text-muted-foreground">
                      {entry.resource_type ? `${titleCase(entry.resource_type)} ` : ""}
                      {entry.resource_id ?? ""}
                    </span>
                    <span className="ml-auto text-[11px] text-muted-foreground">{formatDateTime(entry.created_at)}</span>
                  </li>
                ))}
                {(activity.data?.items.length ?? 0) === 0 ? (
                  <li className="text-muted-foreground">No activity has been recorded for this workspace yet.</li>
                ) : null}
              </ul>
            )}
          </div>
        </section>
      ) : null}

      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <Users className="h-3.5 w-3.5" aria-hidden="true" />
          Ready when you are: ask a question, search the repository, or compare two suppliers.
        </span>
        <Link to="/search" className="underline hover:text-foreground">
          Search the repository
        </Link>
        <Link to="/compare" className="underline hover:text-foreground">
          Compare suppliers
        </Link>
        {canAdminister ? (
          <Link to="/admin" className="underline hover:text-foreground">
            Administration
          </Link>
        ) : null}
      </p>

      <p className="flex items-start gap-2 text-[11px] leading-relaxed text-muted-foreground">
        <MessagesSquare className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        Search quality, answer generation, provider configuration and the audit trail are managed in Administration, so
        the procurement workspace stays focused on the work.
      </p>
    </div>
  );
}
