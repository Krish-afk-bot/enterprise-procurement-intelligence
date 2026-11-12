import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, FileSearch, Search as SearchIcon, SlidersHorizontal, X } from "lucide-react";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { SourceLink } from "@/components/common/Evidence";
import { PageHeader } from "@/components/common/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Switch } from "@/components/ui/misc";
import { api } from "@/lib/api";
import { MICROCOPY, microcopyPlain } from "@/lib/microcopy";
import type { SearchHit } from "@/lib/types";
import { useMood } from "@/lib/useMood";
import { cn, formatDate, matchReasonPlain, titleCase } from "@/lib/utils";

/** Where each hit came from, resolved from the repository rather than guessed. */
interface DocumentContext {
  title: string;
  supplier_name: string | null;
  contract_number: string | null;
}

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("hybrid");
  const [limit, setLimit] = useState("10");
  const [rerank, setRerank] = useState(true);
  const [supplierId, setSupplierId] = useState("all");
  const [documentType, setDocumentType] = useState("all");
  const [contractId, setContractId] = useState("all");
  const [region, setRegion] = useState("all");
  const [category, setCategory] = useState("all");
  const [includeExpired, setIncludeExpired] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  const filters = useQuery({ queryKey: ["filters"], queryFn: api.filters });
  const repository = useQuery({
    queryKey: ["documents", "search-context"],
    queryFn: () => api.documents({ limit: 200 }),
  });

  const context = useMemo(() => {
    const map = new Map<string, DocumentContext>();
    for (const item of repository.data?.items ?? []) {
      map.set(item.id, {
        title: item.title || item.filename,
        supplier_name: item.supplier_name ?? null,
        contract_number: item.contract_number ?? null,
      });
    }
    return map;
  }, [repository.data]);

  const search = useMutation({
    mutationFn: () =>
      api.search({
        query,
        mode,
        limit: Number(limit),
        rerank,
        filters: {
          supplier_ids: supplierId === "all" ? [] : [supplierId],
          document_types: documentType === "all" ? [] : [documentType],
          contract_ids: contractId === "all" ? [] : [contractId],
          regions: region === "all" ? [] : [region],
          categories: category === "all" ? [] : [category],
          include_expired: includeExpired,
        },
      }),
  });

  useMood(
    search.isPending
      ? "loading"
      : search.isError
        ? "error"
        : search.data
          ? search.data.hits.length > 0
            ? "found"
            : "empty"
          : null,
  );

  const activeFilters = [
    supplierId !== "all" ? { key: "supplier", value: filters.data?.suppliers.find((s) => s.id === supplierId)?.name ?? supplierId, clear: () => setSupplierId("all") } : null,
    documentType !== "all" ? { key: "type", value: titleCase(documentType), clear: () => setDocumentType("all") } : null,
    contractId !== "all" ? { key: "contract", value: filters.data?.contracts.find((c) => c.id === contractId)?.number ?? contractId, clear: () => setContractId("all") } : null,
    region !== "all" ? { key: "region", value: region, clear: () => setRegion("all") } : null,
    category !== "all" ? { key: "category", value: category, clear: () => setCategory("all") } : null,
    includeExpired ? { key: "term", value: "including ended terms", clear: () => setIncludeExpired(false) } : null,
  ].filter((entry): entry is { key: string; value: string; clear: () => void } => entry !== null);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Search"
        description="Find the passage you need across the supplier agreements, pricing schedules, amendments and compliance documents in this workspace, then open the exact page it came from."
        meta={
          filters.data ? (
            <>
              <span>{filters.data.suppliers.length} suppliers</span>
              <span className="text-white/20">·</span>
              <span>{filters.data.contracts.length} contracts</span>
              <span className="text-white/20">·</span>
              <span>{filters.data.document_types.length} document types</span>
            </>
          ) : null
        }
      />

      {/* ------------------------------------------------------------ query bar */}
      <form
        className="glass-strong relative overflow-hidden rounded-2xl p-5 shadow-card sm:p-6"
        onSubmit={(event) => {
          event.preventDefault();
          if (query.trim()) search.mutate();
        }}
      >
        <div
          className="pointer-events-none absolute -right-24 -top-32 h-64 w-64 rounded-full bg-[radial-gradient(closest-side,rgba(255,255,255,0.10),transparent)]"
          aria-hidden="true"
        />
        <Label htmlFor="search-query" className="sr-only">
          What are you looking for?
        </Label>
        <div className="relative flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <SearchIcon
              className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-white/35"
              aria-hidden="true"
            />
            <Input
              id="search-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search clauses, prices, suppliers or page text…"
              autoComplete="off"
              className="h-12 rounded-xl border-white/12 bg-white/[0.04] pl-11 pr-10 text-[15px] sm:h-14"
            />
            {query ? (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Clear the query"
                className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-white/35 transition-colors hover:bg-white/10 hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowFilters((value) => !value)}
              aria-expanded={showFilters}
              className="gap-2 rounded-xl"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
              Filters
              {activeFilters.length > 0 ? (
                <span className="tnum rounded-full bg-white px-1.5 text-[10px] font-semibold text-ink">
                  {activeFilters.length}
                </span>
              ) : null}
            </Button>
            <Button type="submit" disabled={!query.trim() || search.isPending} className="gap-2 rounded-xl px-5">
              <SearchIcon className="h-3.5 w-3.5" aria-hidden="true" />
              {search.isPending ? "Searching" : "Search"}
            </Button>
          </div>
        </div>

        {activeFilters.length > 0 ? (
          <ul className="mt-4 flex flex-wrap items-center gap-2">
            {activeFilters.map((filter) => (
              <li key={filter.key}>
                <button
                  type="button"
                  onClick={filter.clear}
                  className="group inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/[0.05] px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:border-white/30 hover:text-foreground"
                >
                  <span className="text-white/40">{filter.key}</span>
                  {filter.value}
                  <X className="h-3 w-3 text-white/30 group-hover:text-foreground" aria-hidden="true" />
                  <span className="sr-only">Remove this filter</span>
                </button>
              </li>
            ))}
            <li>
              <button
                type="button"
                onClick={() => {
                  setSupplierId("all");
                  setDocumentType("all");
                  setContractId("all");
                  setRegion("all");
                  setCategory("all");
                  setIncludeExpired(false);
                }}
                className="px-1 text-[11px] text-subtle underline-offset-4 transition-colors hover:text-foreground hover:underline"
              >
                Clear all
              </button>
            </li>
          </ul>
        ) : null}

        {showFilters ? (
          <div className="mt-5 grid gap-4 border-t border-white/[0.08] pt-5 sm:grid-cols-2 lg:grid-cols-3">
            <FilterField label="Supplier">
              <Select value={supplierId} onValueChange={setSupplierId}>
                <SelectTrigger aria-label="Filter by supplier">
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
            </FilterField>

            <FilterField label="Document type">
              <Select value={documentType} onValueChange={setDocumentType}>
                <SelectTrigger aria-label="Filter by document type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">all types</SelectItem>
                  {(filters.data?.document_types ?? []).map((value) => (
                    <SelectItem key={value} value={value}>
                      {titleCase(value)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FilterField>

            <FilterField label="Contract">
              <Select value={contractId} onValueChange={setContractId}>
                <SelectTrigger aria-label="Filter by contract">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">all contracts</SelectItem>
                  {(filters.data?.contracts ?? []).map((contract) => (
                    <SelectItem key={contract.id} value={contract.id}>
                      {contract.number}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FilterField>

            <FilterField label="Region">
              <Select value={region} onValueChange={setRegion}>
                <SelectTrigger aria-label="Filter by region">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">all regions</SelectItem>
                  {(filters.data?.regions ?? []).map((value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FilterField>

            <FilterField label="Category">
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger aria-label="Filter by category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">all categories</SelectItem>
                  {(filters.data?.categories ?? []).map((value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FilterField>

            <div className="flex items-center gap-2.5 pt-1">
              <Switch id="search-expired" checked={includeExpired} onCheckedChange={setIncludeExpired} />
              <label htmlFor="search-expired" className="text-xs leading-snug text-muted-foreground">
                Include records whose term has ended
              </label>
            </div>
          </div>
        ) : null}
      </form>

      {search.isError ? <ErrorState error={search.error} onRetry={() => search.mutate()} /> : null}
      {search.isPending ? <LoadingState label={MICROCOPY.readingDocuments} /> : null}

      {search.data ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-xs text-muted-foreground">
              <span className="tnum font-medium text-foreground">{search.data.total}</span> passage(s) for{" "}
              <span className="font-medium text-foreground">{search.data.query}</span>
            </p>
            <p className="text-[11px] text-subtle">
              {search.data.reranker ? `reranked by ${search.data.reranker}` : "reranking not enabled"}
            </p>
          </div>

          {search.data.hits.length === 0 ? (
            <EmptyState
              icon={FileSearch}
              title={MICROCOPY.emptySearch}
              description={`${microcopyPlain("emptySearch")} Widen the filters, try a shorter phrase, or check that the document holding the term has finished processing.`}
            />
          ) : (
            <ol className="space-y-3">
              {search.data.hits.map((hit, index) => (
                <HitCard
                  key={hit.chunk_id}
                  style={{ animationDelay: `${Math.min(index, 8) * 28}ms` }}
                  hit={hit}
                  index={index + 1}
                  context={context.get(hit.document_id)}
                  details={<TechnicalHitDetails hit={hit} />}
                />
              ))}
            </ol>
          )}

          <details className="rounded-xl border border-white/10 bg-card/60 p-4 text-xs">
            <summary className="cursor-pointer text-[12px] font-medium text-foreground">Search details</summary>
            <div className="mt-4 space-y-4 text-muted-foreground">
              <div className="flex flex-wrap items-end gap-4">
                <FilterField label="Search strategy" className="w-[200px]">
                  <Select value={mode} onValueChange={setMode}>
                    <SelectTrigger aria-label="Search strategy">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hybrid">meaning and exact words</SelectItem>
                      <SelectItem value="dense">meaning only</SelectItem>
                      <SelectItem value="sparse">exact words only</SelectItem>
                    </SelectContent>
                  </Select>
                </FilterField>
                <FilterField label="Passages" className="w-[120px]">
                  <Select value={limit} onValueChange={setLimit}>
                    <SelectTrigger aria-label="Number of passages">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {["5", "10", "20", "50"].map((value) => (
                        <SelectItem key={value} value={value}>
                          {value}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FilterField>
                <div className="flex items-center gap-2.5 pb-2">
                  <Switch id="search-rerank" checked={rerank} onCheckedChange={setRerank} />
                  <label htmlFor="search-rerank" className="text-xs leading-snug text-muted-foreground">
                    Re-rank candidates against the question
                  </label>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="mb-0.5"
                  disabled={!query.trim() || search.isPending}
                  onClick={() => search.mutate()}
                >
                  Apply and search again
                </Button>
              </div>

              <div className="border-t border-white/[0.08] pt-4">
                <h3 className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-subtle">What the search did</h3>
                <ol className="mt-3 space-y-3 text-[11px]">
                  {search.data.steps.map((step) => (
                    <li key={step.name} className="border-b border-white/[0.06] pb-3 last:border-0 last:pb-0">
                      <p className="font-medium text-foreground">
                        {step.name === "dense_search"
                          ? "Semantic search"
                          : step.name === "sparse_search"
                            ? "Keyword search"
                            : step.name === "fusion"
                              ? "Combined ranking"
                              : step.name === "rerank"
                                ? "Evidence selection"
                                : step.name === "authorization_filter"
                                  ? "Access check"
                                  : titleCase(step.name)}
                        <span className="ml-2 font-mono text-[10px] text-subtle">{step.name}</span>
                      </p>
                      <p className="mt-0.5">{step.detail}</p>
                      <p className="tnum mt-0.5 text-subtle">
                        {step.candidates} candidate(s)
                        {step.latency_ms !== null ? ` · ${step.latency_ms} ms` : ""}
                      </p>
                    </li>
                  ))}
                </ol>
              </div>

              <dl className="space-y-1.5 border-t border-white/[0.08] pt-3 text-[11px]">
                <div className="flex justify-between gap-2">
                  <dt>Evidence selection model</dt>
                  <dd className="font-medium text-foreground">{search.data.reranker ?? "not enabled"}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>Embedding model</dt>
                  <dd className="font-medium text-foreground">{search.data.embedding_model ?? "not reported"}</dd>
                </div>
              </dl>
            </div>
          </details>
        </div>
      ) : null}
    </div>
  );
}

function FilterField({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function HitCard({
  hit,
  index,
  context,
  details,
  style,
}: {
  hit: SearchHit;
  index: number;
  context: DocumentContext | undefined;
  details: React.ReactNode;
  style?: React.CSSProperties;
}) {
  const reasons = hit.matched_by.length > 0 ? hit.matched_by.map(matchReasonPlain) : ["position in the combined ranking"];
  // Only the semantic score is a bounded similarity, so it is the only one that
  // can be drawn as a bar. Fusion and rerank scores use their own scales and are
  // left in the numeric detail rather than turned into a misleading width.
  const semantic = typeof hit.dense_score === "number" ? Math.max(0, Math.min(1, hit.dense_score)) : null;

  return (
    <li className="animate-rise" style={style}>
      <Card className="group overflow-hidden transition-[border-color,transform] duration-300 hover:-translate-y-0.5 hover:border-white/20">
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5 border-b border-white/[0.06] px-5 py-3">
          <span className="tnum flex h-5 w-5 items-center justify-center rounded-md border border-white/10 bg-white/[0.04] text-[10px] text-muted-foreground">
            {index}
          </span>
          <Link
            to={`/documents/${hit.document_id}`}
            className="text-[12.5px] font-medium transition-colors hover:text-white"
          >
            {hit.document_name}
          </Link>
          <span className="text-[11px] text-subtle">{hit.page ? `page ${hit.page}` : "page not recorded"}</span>
          {hit.section ? <span className="text-[11px] text-subtle">{hit.section}</span> : null}
          {hit.clause ? <span className="text-[11px] text-subtle">{hit.clause}</span> : null}
          <div className="ml-auto flex items-center gap-1.5">
            <Badge variant="outline" className="font-normal">
              {titleCase(hit.content_type)}
            </Badge>
            {hit.is_synthetic ? (
              <Badge variant="warning" className="font-normal">
                demo corpus
              </Badge>
            ) : null}
            {hit.version > 1 ? (
              <Badge variant="outline" className="font-normal text-muted-foreground">
                v{hit.version}
              </Badge>
            ) : null}
          </div>
        </div>

        <div className="px-5 py-4">
          <p className="text-[13px] leading-relaxed text-foreground/90">{hit.content}</p>

          <dl className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[11px] text-subtle">
            <div className="flex items-center gap-1.5">
              <dt>Supplier</dt>
              <dd className="font-medium text-muted-foreground">{context?.supplier_name ?? "not linked"}</dd>
            </div>
            <div className="flex items-center gap-1.5">
              <dt>Contract</dt>
              <dd className="font-medium text-muted-foreground">{context?.contract_number ?? "not linked"}</dd>
            </div>
            {hit.effective_date || hit.expiry_date ? (
              <div className="flex items-center gap-1.5">
                <dt>Term</dt>
                <dd className="font-medium text-muted-foreground">
                  {formatDate(hit.effective_date)} to {formatDate(hit.expiry_date)}
                </dd>
              </div>
            ) : null}
          </dl>

          {semantic !== null ? (
            <div className="mt-3.5 flex items-center gap-2.5">
              <span className="text-[10px] uppercase tracking-[0.12em] text-subtle">Semantic</span>
              <span className="h-[3px] w-full max-w-[220px] overflow-hidden rounded-full bg-white/[0.08]">
                <span
                  className="block h-full rounded-full bg-white/55"
                  style={{ width: `${Math.max(3, semantic * 100)}%` }}
                />
              </span>
              <span className="tnum text-[10px] text-subtle">{semantic.toFixed(3)}</span>
            </div>
          ) : null}

          <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-white/[0.06] pt-3.5 text-[11px]">
            <SourceLink documentId={hit.document_id} page={hit.page} chunkId={hit.chunk_id}>
              Open source
            </SourceLink>
            <span className="text-white/15" aria-hidden="true">
              |
            </span>
            <span className="text-subtle">Matched on {reasons.join(", ")}.</span>
            <div className="ml-auto">{details}</div>
          </div>
        </div>
      </Card>
    </li>
  );
}

function TechnicalHitDetails({ hit }: { hit: SearchHit }) {
  return (
    <details>
      <summary className="flex cursor-pointer items-center gap-1 text-muted-foreground transition-colors hover:text-foreground">
        Scores
        <ArrowRight className="h-3 w-3 rotate-90" aria-hidden="true" />
      </summary>
      <dl className="tnum mt-2 grid grid-cols-2 gap-x-5 gap-y-1 text-[11px] text-muted-foreground sm:grid-cols-4">
        <Score label="combined" value={hit.fused_score} />
        <Score label="semantic" value={hit.dense_score} />
        <Score label="keyword" value={hit.sparse_score} />
        <Score label="selection" value={hit.rerank_score} />
      </dl>
      <p className="mt-1.5 text-[11px] text-subtle">
        Surfaced by: {(hit.matched_by.length > 0 ? hit.matched_by : ["fused"]).join(", ")} · access level {hit.access_level}
      </p>
    </details>
  );
}

function Score({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="flex justify-between gap-2">
      <dt>{label}</dt>
      <dd className="font-medium text-foreground">{value === null ? "not produced" : value.toFixed(4)}</dd>
    </div>
  );
}
