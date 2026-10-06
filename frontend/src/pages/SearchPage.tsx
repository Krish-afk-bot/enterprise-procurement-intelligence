import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FileSearch, Search as SearchIcon, SlidersHorizontal } from "lucide-react";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { SourceLink } from "@/components/common/Evidence";
import { PageHeader } from "@/components/common/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Switch } from "@/components/ui/misc";
import { api } from "@/lib/api";
import { MICROCOPY, microcopyPlain } from "@/lib/microcopy";
import type { SearchHit } from "@/lib/types";
import { useMood } from "@/lib/useMood";
import { formatDate, matchReasonPlain, titleCase } from "@/lib/utils";

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

  return (
    <div className="space-y-5">
      <PageHeader
        title="Search"
        description="Find the passage you need across the supplier agreements, pricing schedules, amendments and compliance documents in this workspace, then open the exact page it came from."
        meta={
          filters.data ? (
            <>
              <span>{filters.data.suppliers.length} suppliers</span>
              <span>{filters.data.contracts.length} contracts</span>
              <span>{filters.data.document_types.length} document types</span>
            </>
          ) : null
        }
      />

      <form
        className="rounded-lg border p-3"
        onSubmit={(event) => {
          event.preventDefault();
          if (query.trim()) search.mutate();
        }}
      >
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[260px] flex-1 space-y-1.5">
            <Label htmlFor="search-query">What are you looking for?</Label>
            <Input
              id="search-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="unit price laptop"
              autoComplete="off"
            />
          </div>
          <Button type="button" variant="outline" onClick={() => setShowFilters((value) => !value)} aria-expanded={showFilters}>
            <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
            Filters
          </Button>
          <Button type="submit" disabled={!query.trim() || search.isPending}>
            <SearchIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {search.isPending ? "Searching" : "Search"}
          </Button>
        </div>

        {showFilters ? (
          <div className="mt-3 grid gap-3 border-t pt-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-1.5">
              <Label>Supplier</Label>
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
            </div>
            <div className="space-y-1.5">
              <Label>Document type</Label>
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
            </div>
            <div className="space-y-1.5">
              <Label>Contract</Label>
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
            </div>
            <div className="space-y-1.5">
              <Label>Region</Label>
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
            </div>
            <div className="space-y-1.5">
              <Label>Category</Label>
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
            </div>
            <div className="flex items-center gap-2 pt-5">
              <Switch id="search-expired" checked={includeExpired} onCheckedChange={setIncludeExpired} />
              <label htmlFor="search-expired" className="text-xs text-muted-foreground">
                include records whose term has ended
              </label>
            </div>
          </div>
        ) : null}
      </form>

      {search.isError ? <ErrorState error={search.error} onRetry={() => search.mutate()} /> : null}
      {search.isPending ? <LoadingState label={MICROCOPY.readingDocuments} /> : null}

      {search.data ? (
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            {search.data.total} passage(s) for <span className="font-medium text-foreground">{search.data.query}</span>
          </p>

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
                  details={
                    <TechnicalHitDetails hit={hit} />
                  }
                />
              ))}
            </ol>
          )}

          <details className="rounded-lg border p-3 text-xs">
            <summary className="cursor-pointer font-medium text-foreground">Search details</summary>
            <div className="mt-3 space-y-3 text-muted-foreground">
              <div className="flex flex-wrap items-end gap-3">
                <div className="space-y-1.5">
                  <Label>Search strategy</Label>
                  <Select value={mode} onValueChange={setMode}>
                    <SelectTrigger className="w-[180px]" aria-label="Search strategy">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hybrid">meaning and exact words</SelectItem>
                      <SelectItem value="dense">meaning only</SelectItem>
                      <SelectItem value="sparse">exact words only</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Passages to show</Label>
                  <Select value={limit} onValueChange={setLimit}>
                    <SelectTrigger className="w-[110px]" aria-label="Number of passages">
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
                </div>
                <div className="flex items-center gap-2 pb-1.5">
                  <Switch id="search-rerank" checked={rerank} onCheckedChange={setRerank} />
                  <label htmlFor="search-rerank" className="text-xs text-muted-foreground">
                    re-rank the candidates against the question
                  </label>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="mb-1"
                  disabled={!query.trim() || search.isPending}
                  onClick={() => search.mutate()}
                >
                  Apply and search again
                </Button>
              </div>

              <div className="border-t pt-3">
                <h3 className="text-[11px] font-semibold uppercase tracking-wide text-foreground">What the search did</h3>
                <ol className="mt-2 space-y-2 text-[11px]">
                  {search.data.steps.map((step) => (
                    <li key={step.name} className="border-b border-border/60 pb-2 last:border-0">
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
                        <span className="ml-2 font-mono text-[10px] text-muted-foreground">{step.name}</span>
                      </p>
                      <p>{step.detail}</p>
                      <p className="tnum mt-0.5">
                        {step.candidates} candidate(s)
                        {step.latency_ms !== null ? ` · ${step.latency_ms} ms` : ""}
                      </p>
                    </li>
                  ))}
                </ol>
              </div>

              <dl className="space-y-1 border-t pt-2 text-[11px]">
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

  return (
    <li className="animate-rise rounded-lg border p-3.5" style={style}>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="tnum text-muted-foreground">{index}</span>
        <Link to={`/documents/${hit.document_id}`} className="font-medium hover:underline">
          {hit.document_name}
        </Link>
        <span className="text-muted-foreground">{hit.page ? `page ${hit.page}` : "page not recorded"}</span>
        {hit.section ? <span className="text-muted-foreground">{hit.section}</span> : null}
        {hit.clause ? <span className="text-muted-foreground">{hit.clause}</span> : null}
        <Badge variant="outline" className="font-normal">
          {titleCase(hit.content_type)}
        </Badge>
        {hit.is_synthetic ? (
          <Badge variant="outline" className="border-warning/35 font-normal text-warning">
            demo corpus
          </Badge>
        ) : null}
        {hit.version > 1 ? (
          <Badge variant="outline" className="font-normal text-muted-foreground">
            v{hit.version}
          </Badge>
        ) : null}
      </div>

      <dl className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <dt>Supplier</dt>
          <dd className="font-medium text-foreground">{context?.supplier_name ?? "not linked"}</dd>
        </div>
        <div className="flex items-center gap-1.5">
          <dt>Contract</dt>
          <dd className="font-medium text-foreground">{context?.contract_number ?? "not linked"}</dd>
        </div>
        {hit.effective_date || hit.expiry_date ? (
          <div className="flex items-center gap-1.5">
            <dt>Term</dt>
            <dd className="font-medium text-foreground">
              {formatDate(hit.effective_date)} to {formatDate(hit.expiry_date)}
            </dd>
          </div>
        ) : null}
      </dl>

      <p className="mt-2 text-xs leading-relaxed">{hit.content}</p>

      <p className="mt-2 text-[11px] text-muted-foreground">Matched on {reasons.join(", ")}.</p>

      <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px]">
        <SourceLink documentId={hit.document_id} page={hit.page} chunkId={hit.chunk_id}>
          Open source
        </SourceLink>
        {details}
      </div>
    </li>
  );
}

function TechnicalHitDetails({ hit }: { hit: SearchHit }) {
  return (
    <details>
      <summary className="cursor-pointer text-muted-foreground">Search details for this passage</summary>
      <dl className="tnum mt-1.5 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-muted-foreground sm:grid-cols-4">
        <Score label="combined" value={hit.fused_score} />
        <Score label="semantic" value={hit.dense_score} />
        <Score label="keyword" value={hit.sparse_score} />
        <Score label="selection" value={hit.rerank_score} />
      </dl>
      <p className="mt-1 text-[11px] text-muted-foreground">
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
