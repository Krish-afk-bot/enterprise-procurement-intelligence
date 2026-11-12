import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  CircleAlert,
  Clock,
  FileStack,
  MessagesSquare,
  Upload,
  Users,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingRows } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Reveal } from "@/components/motion/Reveal";
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
  formatMoney,
  formatNumber,
  plural,
  titleCase,
  toneClasses,
} from "@/lib/utils";
import { useAuth } from "@/store/auth";

const PROCESSING_STATUSES = ["queued", "uploaded", "processing", "running", "pending"];
const ATTENTION_STATUSES = ["failed", "needs_review"];
const ACTIVITY_DAYS = 14;

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
  const supplierItems = suppliers.data?.items ?? [];

  const derived = useMemo(() => {
    const needingAttention = documentItems.filter((item) => ATTENTION_STATUSES.includes(item.status));
    const processing = documentItems.filter((item) => PROCESSING_STATUSES.includes(item.status));
    const expiring = documentItems
      .map((item) => ({ item, days: daysUntilDate(item.expiry_date) }))
      .filter(
        (row): row is { item: DocumentSummary; days: number } =>
          row.days !== null && row.days >= 0 && row.days <= EXPIRING_SOON_DAYS,
      )
      .sort((a, b) => a.days - b.days);
    const recentlyUpdated = [...documentItems]
      .sort(
        (a, b) =>
          new Date(b.updated_at ?? b.created_at ?? 0).getTime() -
          new Date(a.updated_at ?? a.created_at ?? 0).getTime(),
      )
      .slice(0, 6);
    const contractsExpiring = contractItems
      .map((contract) => ({ contract, days: daysUntilDate(contract.expiry_date) }))
      .filter(
        (row): row is { contract: (typeof contractItems)[number]; days: number } =>
          row.days !== null && row.days >= 0 && row.days <= EXPIRING_SOON_DAYS,
      )
      .sort((a, b) => a.days - b.days);
    const activeContracts = contractItems.filter(
      (contract) =>
        documentLifecycle({ status: "indexed", expiry_date: contract.expiry_date, effective_date: contract.effective_date })
          .label === "Active",
    );

    // Activity is counted from the timestamps the API already returns. A day
    // with no record is a real zero, not a gap to be filled.
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const buckets = Array.from({ length: ACTIVITY_DAYS }, (_, index) => {
      const date = new Date(today);
      date.setDate(today.getDate() - (ACTIVITY_DAYS - 1 - index));
      return { date, uploaded: 0, updated: 0 };
    });
    for (const item of documentItems) {
      const created = item.created_at ? new Date(item.created_at) : null;
      const updated = item.updated_at ? new Date(item.updated_at) : null;
      for (const bucket of buckets) {
        if (created && sameDay(created, bucket.date)) bucket.uploaded += 1;
        if (updated && sameDay(updated, bucket.date)) bucket.updated += 1;
      }
    }

    const searchable = documentItems.filter((item) => item.status === "indexed").length;
    const withSupplier = contractItems.filter((contract) => Boolean(contract.supplier_id)).length;
    const withValue = contractItems.filter((contract) => contract.total_value !== null);
    const recordedValue = withValue.reduce((total, contract) => total + (contract.total_value ?? 0), 0);

    const topSuppliers = [...supplierItems]
      .sort((a, b) => b.document_count - a.document_count || b.contract_count - a.contract_count)
      .slice(0, 5);

    return {
      needingAttention,
      processing,
      expiring,
      recentlyUpdated,
      contractsExpiring,
      activeContracts,
      buckets,
      searchable,
      withSupplier,
      withValue,
      recordedValue,
      topSuppliers,
    };
  }, [documentItems, contractItems, supplierItems]);

  const figures = [
    {
      label: "Documents",
      value: formatNumber(documents.data?.total ?? documentItems.length),
      detail: `${derived.searchable} searchable`,
      icon: FileStack,
      to: "/documents",
    },
    {
      label: "Active contracts",
      value: formatNumber(derived.activeContracts.length),
      detail: `${formatNumber(contractItems.length)} records`,
      icon: BadgeCheck,
      to: "/contracts",
    },
    {
      label: "Suppliers",
      value: formatNumber(suppliers.data?.total ?? supplierItems.length),
      detail: "linked to documents",
      icon: Users,
      to: "/suppliers",
    },
    {
      label: "Recorded contract value",
      value: derived.withValue.length > 0 ? formatMoney(derived.recordedValue, derived.withValue[0]?.currency) : NOT_RECORDED,
      detail: `${derived.withValue.length} of ${contractItems.length} contracts carry a value`,
      icon: Activity,
      to: "/contracts",
    },
  ];

  if (documents.isError) return <ErrorState error={documents.error} onRetry={() => void documents.refetch()} />;

  return (
    <div className="space-y-7">
      <PageHeader
        title="Overview"
        description="Where procurement documents, contracts and suppliers stand today, and how they connect. Every figure is read from the workspace database; a value that is not recorded is labelled rather than shown as zero."
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

      {/* ------------------------------------------------------------ figures */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {figures.map((figure, index) => (
          <Reveal key={figure.label} delay={index * 60}>
            <Link
              to={figure.to}
              className="group block h-full rounded-xl border border-white/10 bg-card p-5 shadow-[inset_0_1px_0_0_rgb(255_255_255_/_0.04)] transition-[border-color,transform] duration-300 hover:-translate-y-0.5 hover:border-white/20"
            >
              <div className="flex items-start justify-between">
                <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-subtle">{figure.label}</p>
                <figure.icon
                  className="h-4 w-4 text-white/25 transition-colors group-hover:text-white/70"
                  aria-hidden="true"
                />
              </div>
              <p className="tnum mt-4 text-[30px] font-semibold leading-none tracking-tight">{figure.value}</p>
              <p className="mt-2.5 text-[11.5px] text-muted-foreground">{figure.detail}</p>
            </Link>
          </Reveal>
        ))}
      </div>

      {documents.isLoading ? <LoadingRows rows={4} /> : null}

      {/* ----------------------------------------------------- chart + coverage */}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">
        <Reveal className="h-full">
          <Card className="flex h-full flex-col">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] px-5 py-4">
              <div>
                <h2 className="text-[13px] font-medium">Document activity</h2>
                <p className="mt-0.5 text-[11px] text-subtle">Uploads and updates recorded over the last {ACTIVITY_DAYS} days.</p>
              </div>
              <div className="flex items-center gap-4 text-[10.5px] text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-sm bg-white" aria-hidden="true" />
                  Uploaded
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-sm bg-white/30" aria-hidden="true" />
                  Updated
                </span>
              </div>
            </div>
            <div className="min-h-[240px] flex-1 p-4">
              {documentItems.length === 0 ? (
                <div className="flex h-full items-center justify-center">
                  <p className="text-xs text-subtle">No document activity has been recorded yet.</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={230}>
                  <AreaChart data={derived.buckets} margin={{ top: 8, right: 8, bottom: 0, left: -22 }}>
                    <defs>
                      <linearGradient id="activity-uploaded" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ffffff" stopOpacity={0.28} />
                        <stop offset="100%" stopColor="#ffffff" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="activity-updated" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ffffff" stopOpacity={0.12} />
                        <stop offset="100%" stopColor="#ffffff" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(value: Date) =>
                        value.toLocaleDateString(undefined, { day: "numeric", month: "short" })
                      }
                      stroke="rgba(255,255,255,0.18)"
                      tick={{ fill: "rgba(255,255,255,0.45)", fontSize: 10 }}
                      tickLine={false}
                      axisLine={false}
                      minTickGap={18}
                    />
                    <YAxis
                      allowDecimals={false}
                      stroke="rgba(255,255,255,0.18)"
                      tick={{ fill: "rgba(255,255,255,0.45)", fontSize: 10 }}
                      tickLine={false}
                      axisLine={false}
                      width={38}
                    />
                    <ChartTooltip
                      contentStyle={{
                        background: "#171717",
                        border: "1px solid rgba(255,255,255,0.12)",
                        borderRadius: 12,
                        fontSize: 12,
                        color: "#fff",
                      }}
                      labelFormatter={(value) => new Date(value as Date).toLocaleDateString()}
                    />
                    <Area
                      type="monotone"
                      dataKey="uploaded"
                      name="Uploaded"
                      stroke="#ffffff"
                      strokeWidth={1.6}
                      fill="url(#activity-uploaded)"
                    />
                    <Area
                      type="monotone"
                      dataKey="updated"
                      name="Updated"
                      stroke="rgba(255,255,255,0.45)"
                      strokeWidth={1.2}
                      fill="url(#activity-updated)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>
        </Reveal>

        <Reveal delay={80} className="h-full">
          <Card className="flex h-full flex-col">
            <div className="border-b border-white/[0.07] px-5 py-4">
              <h2 className="text-[13px] font-medium">Evidence coverage</h2>
              <p className="mt-0.5 text-[11px] text-subtle">How much of the repository can be cited today.</p>
            </div>
            <div className="flex-1 space-y-5 p-5">
              <CoverageBar
                label="Documents searchable"
                value={derived.searchable}
                total={documentItems.length}
                caption="indexed and available to retrieval"
              />
              <CoverageBar
                label="Contracts with a supplier"
                value={derived.withSupplier}
                total={contractItems.length}
                caption="resolved to a supplier record"
              />
              <CoverageBar
                label="Contracts with a value"
                value={derived.withValue.length}
                total={contractItems.length}
                caption="a value is recorded, not estimated"
              />
              <div className="border-t border-white/[0.07] pt-4">
                <div className="flex items-center justify-between text-[12px]">
                  <span className="text-muted-foreground">Still processing</span>
                  <span className="tnum font-medium">{derived.processing.length}</span>
                </div>
                <div className="mt-2 flex items-center justify-between text-[12px]">
                  <span className="text-muted-foreground">Needs attention</span>
                  <span className={cn("tnum font-medium", derived.needingAttention.length > 0 && "text-destructive")}>
                    {derived.needingAttention.length}
                  </span>
                </div>
              </div>
            </div>
          </Card>
        </Reveal>
      </div>

      {/* ------------------------------------------------- alerts, when present */}
      {derived.needingAttention.length > 0 || derived.expiring.length > 0 ? (
        <div className="grid gap-5 lg:grid-cols-2">
          {derived.needingAttention.length > 0 ? (
            <Card className="border-destructive/30 bg-destructive/[0.06] p-5">
              <h2 className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.12em] text-destructive">
                <CircleAlert className="h-3.5 w-3.5" aria-hidden="true" />
                Needs attention
              </h2>
              <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">
                Processing reported a problem. The document keeps its error message and its pages are not searchable
                until it is re-indexed.
              </p>
              <ul className="mt-3 space-y-1.5 text-xs">
                {derived.needingAttention.slice(0, 5).map((item) => (
                  <li key={item.id} className="flex flex-wrap items-baseline gap-2">
                    <Link to={`/documents/${item.id}`} className="font-medium hover:underline">
                      {item.title || item.filename}
                    </Link>
                    <Badge variant="destructive" className="font-normal">
                      {item.status === "needs_review" ? "Needs review" : "Processing failed"}
                    </Badge>
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          {derived.expiring.length > 0 ? (
            <Card className="p-5">
              <h2 className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                Expiring within 90 days
              </h2>
              <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">
                Based on the expiry date recorded on each document. Documents without a recorded expiry date are not
                listed here.
              </p>
              <ul className="mt-3 space-y-1.5 text-xs">
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
            </Card>
          ) : null}
        </div>
      ) : null}

      {/* -------------------------------------------------------- documents + contracts */}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <Card className="min-w-0">
          <div className="flex items-center justify-between gap-3 border-b border-white/[0.07] px-5 py-4">
            <h2 className="flex items-center gap-2 text-[13px] font-medium">
              <FileStack className="h-3.5 w-3.5 text-white/40" aria-hidden="true" />
              Recently updated documents
            </h2>
            <Link to="/documents" className="text-[11px] text-muted-foreground transition-colors hover:text-foreground">
              All documents
            </Link>
          </div>
          {documents.isLoading ? (
            <div className="p-4">
              <LoadingRows rows={4} />
            </div>
          ) : documentItems.length === 0 ? (
            <div className="p-5">
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
              <caption className="sr-only">
                The six documents that changed most recently, with their type and state.
              </caption>
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
                        <p className="mt-0.5 text-[11px] text-subtle">{item.supplier_name ?? "supplier not linked"}</p>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {documentTypeLabel(item.document_type)}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={cn("font-normal", toneClasses(lifecycle.tone))}
                          title={lifecycle.basis}
                        >
                          {lifecycle.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-[11px] text-subtle">{formatDateTime(item.updated_at)}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </Card>

        <div className="min-w-0 space-y-5">
          <Card>
            <div className="flex items-center justify-between gap-3 border-b border-white/[0.07] px-5 py-4">
              <h2 className="flex items-center gap-2 text-[13px] font-medium">
                <Users className="h-3.5 w-3.5 text-white/40" aria-hidden="true" />
                Supplier overview
              </h2>
              <Link to="/suppliers" className="text-[11px] text-muted-foreground transition-colors hover:text-foreground">
                All suppliers
              </Link>
            </div>
            {suppliers.isLoading ? (
              <div className="p-4">
                <LoadingRows rows={3} />
              </div>
            ) : derived.topSuppliers.length === 0 ? (
              <div className="p-5">
                <EmptyState
                  icon={Users}
                  title="No supplier record yet"
                  description="Suppliers are created when a contract, amendment or price sheet that names one finishes processing."
                />
              </div>
            ) : (
              <ul className="[&>li]:border-t [&>li]:border-white/[0.06] [&>li:first-child]:border-t-0">
                {derived.topSuppliers.map((supplier) => (
                  <li key={supplier.id}>
                    <Link
                      to={`/suppliers/${supplier.id}`}
                      className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-white/[0.03]"
                    >
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-white/12 bg-white/[0.05] text-[10px] font-medium uppercase">
                        {supplier.name.slice(0, 2)}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-xs font-medium">{supplier.name}</span>
                        <span className="block truncate text-[11px] text-subtle">
                          {supplier.category ?? "category not recorded"}
                          {supplier.region ? ` · ${supplier.region}` : ""}
                        </span>
                      </span>
                      <span className="tnum shrink-0 text-[11px] text-muted-foreground">
                        {supplier.document_count} docs · {supplier.contract_count} contracts
                      </span>
                      <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-white/20" aria-hidden="true" />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>

      {/* ------------------------------------------------------------- contracts */}
      <Card className="min-w-0">
        <div className="flex items-center justify-between gap-3 border-b border-white/[0.07] px-5 py-4">
          <h2 className="flex items-center gap-2 text-[13px] font-medium">
            <BadgeCheck className="h-3.5 w-3.5 text-white/40" aria-hidden="true" />
            Contracts
          </h2>
          <Link to="/contracts" className="text-[11px] text-muted-foreground transition-colors hover:text-foreground">
            All contracts
          </Link>
        </div>
        {contracts.isLoading ? (
          <div className="p-4">
            <LoadingRows rows={4} />
          </div>
        ) : contractItems.length === 0 ? (
          <div className="p-5">
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
                <TableHead scope="col">Term</TableHead>
                <TableHead scope="col" className="text-right">
                  Value
                </TableHead>
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
                    <p className="mt-0.5 text-[11px] text-subtle">{contract.title}</p>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {contract.supplier_name ?? NOT_RECORDED}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDate(contract.effective_date)} – {formatDate(contract.expiry_date)}
                  </TableCell>
                  <TableCell className="tnum text-right text-xs">
                    {contract.total_value !== null ? formatMoney(contract.total_value, contract.currency) : NOT_RECORDED}
                  </TableCell>
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
      </Card>

      {/* -------------------------------------------------------------- activity */}
      {canSeeActivity ? (
        <Card>
          <h2 className="flex items-center gap-2 border-b border-white/[0.07] px-5 py-4 text-[13px] font-medium">
            <Activity className="h-3.5 w-3.5 text-white/40" aria-hidden="true" />
            Recent activity
          </h2>
          <div className="p-5">
            {activity.isError ? (
              <ErrorState error={activity.error} onRetry={() => void activity.refetch()} />
            ) : activity.isLoading ? (
              <LoadingRows rows={3} />
            ) : (
              <ul className="space-y-2.5 text-xs">
                {(activity.data?.items ?? []).map((entry) => (
                  <li key={entry.id} className="flex flex-wrap items-baseline gap-2">
                    <span className="font-medium">{activityLabel(entry.action)}</span>
                    <span className="text-subtle">
                      {entry.resource_type ? `${titleCase(entry.resource_type)} ` : ""}
                      {entry.resource_id ?? ""}
                    </span>
                    <span className="ml-auto text-[11px] text-subtle">{formatDateTime(entry.created_at)}</span>
                  </li>
                ))}
                {(activity.data?.items.length ?? 0) === 0 ? (
                  <li className="text-muted-foreground">No activity has been recorded for this workspace yet.</li>
                ) : null}
              </ul>
            )}
          </div>
        </Card>
      ) : null}

      <p className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-white/[0.07] pt-5 text-[11px] text-subtle">
        <span className="flex items-center gap-1.5">
          <MessagesSquare className="h-3.5 w-3.5" aria-hidden="true" />
          Ready when you are: ask a question, search the repository, or compare two suppliers.
        </span>
        <Link to="/search" className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline">
          Search the repository
        </Link>
        <Link to="/compare" className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline">
          Compare suppliers
        </Link>
        {canAdminister ? (
          <Link to="/admin" className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline">
            Administration
          </Link>
        ) : null}
      </p>
    </div>
  );
}

function sameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function CoverageBar({
  label,
  value,
  total,
  caption,
}: {
  label: string;
  value: number;
  total: number;
  caption: string;
}) {
  const percent = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[12px]">{label}</p>
        <p className="tnum text-[11px] text-muted-foreground">
          {value} / {total}
        </p>
      </div>
      <div
        className="mt-2 h-1 w-full overflow-hidden rounded-full bg-white/10"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label}: ${percent}%`}
      >
        <div
          className="h-full rounded-full bg-white transition-[width] duration-700"
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className="mt-1.5 text-[10.5px] text-subtle">{caption}</p>
    </div>
  );
}
