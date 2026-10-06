import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ExternalLink, GitBranch, Network, Search } from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingRows, LoadingState } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { LazyGraphScene } from "@/components/three/LazyGraphScene";
import { api } from "@/lib/api";
import { cn, isRecordId, plural, titleCase, toneClasses } from "@/lib/utils";

/** Text equivalent of the 3D neighbourhood, used when the scene is switched off. */
function NeighbourhoodFallback({
  nodes,
  edges,
}: {
  nodes: { label: string; key: string }[];
  edges: { type: string; start: { label: string; key: string }; end: { label: string; key: string } }[];
}) {
  const counts = new Map<string, number>();
  for (const node of nodes) counts.set(node.label, (counts.get(node.label) ?? 0) + 1);
  return (
    <div className="space-y-2 text-xs">
      <p className="text-muted-foreground">
        {plural(nodes.length, "record")} in this neighbourhood and {plural(edges.length, "connection")}. The table below
        lists every connection with its endpoints.
      </p>
      <ul className="flex flex-wrap gap-1.5">
        {[...counts.entries()].map(([label, count]) => (
          <li key={label}>
            <Badge variant="outline" className="font-normal">
              {titleCase(label)}: {count}
            </Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}

const LABELS = ["Supplier", "Contract", "Product", "Price", "Document", "ComplianceCertificate", "Amendment"];

/**
 * Only labels that have a real detail page are turned into links. A price or
 * compliance node has no page of its own, so its properties are shown instead
 * of sending the user to a route that does not exist.
 *
 * The 3D scene uses the same rule, so a node that is clickable in the scene is
 * always a node that opens a page.
 */
function entityHref(label: string, key: string): string | null {
  if (!isRecordId(key)) return null;
  switch (label) {
    case "Supplier":
      return `/suppliers/${key}`;
    case "Contract":
      return `/contracts/${key}`;
    case "Document":
      return `/documents/${key}`;
    default:
      return null;
  }
}

export function GraphPage() {
  const [label, setLabel] = useState("Supplier");
  const [nameContains, setNameContains] = useState("");
  const [maxHops, setMaxHops] = useState("2");
  const [selected, setSelected] = useState<{ label: string; key: string } | null>(null);

  const overview = useQuery({ queryKey: ["graph-overview"], queryFn: api.graphOverview });
  const nodes = useQuery({
    queryKey: ["graph-nodes", label, nameContains],
    queryFn: () => api.graphNodes(label, nameContains || undefined),
  });
  const paths = useMutation({
    mutationFn: (node: { label: string; key: string }) => api.graphPaths(node.label, node.key, Number(maxHops)),
    onSuccess: (_data, node) => setSelected(node),
  });

  const selectedNode = (nodes.data?.items ?? []).find(
    (node) => selected && node.label === selected.label && node.key === selected.key,
  );

  return (
    <div className="space-y-5">
      <PageHeader
        title="Relationships"
        description="A derived index over suppliers, contracts, amendments, products, prices, documents and compliance certificates. It is rebuilt when a document is re-indexed, and it is what lets a question follow a supplier to a contract to a price row."
        meta={
          overview.data ? (
            <>
              <Badge
                variant="outline"
                className={cn("font-normal", toneClasses(overview.data.available ? "success" : "danger"))}
              >
                {overview.data.available ? "Available" : "Unavailable"}
              </Badge>
              <span>provider {overview.data.provider}</span>
              <span>{plural(overview.data.nodes_total, "node")}</span>
              <span>{plural(overview.data.edges_total, "edge")}</span>
            </>
          ) : null
        }
      />

      {overview.isError ? <ErrorState error={overview.error} onRetry={() => void overview.refetch()} /> : null}

      {overview.data ? (
        <section aria-labelledby="graph-contents" className="rounded-lg border p-4">
          <h2 id="graph-contents" className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            What is in the graph
          </h2>
          <dl className="mt-3 grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
            {Object.entries(overview.data.nodes_by_label).map(([nodeLabel, count]) => (
              <div key={nodeLabel} className="flex items-baseline justify-between gap-2 border-b border-border/70 pb-1.5">
                <dt className="text-xs text-muted-foreground">{titleCase(nodeLabel)}</dt>
                <dd className="tnum text-sm font-medium">{count}</dd>
              </div>
            ))}
          </dl>
          {Object.keys(overview.data.edges_by_type).length > 0 ? (
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {Object.entries(overview.data.edges_by_type).map(([type, count]) => (
                <li key={type}>
                  <Badge variant="outline" className="font-normal text-muted-foreground">
                    {titleCase(type)}: {count}
                  </Badge>
                </li>
              ))}
            </ul>
          ) : null}
          {overview.data.notes.length > 0 ? (
            <ul className="mt-3 space-y-1 text-[11px] text-muted-foreground">
              {overview.data.notes.map((note, index) => (
                <li key={index}>{note}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
        <section aria-labelledby="find-node" className="rounded-lg border p-4">
          <h2 id="find-node" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Search className="h-3.5 w-3.5" aria-hidden="true" />
            Find a record
          </h2>
          <div className="mt-3 space-y-3">
            <div className="space-y-1.5">
              <Label>Record type</Label>
              <Select value={label} onValueChange={setLabel}>
                <SelectTrigger aria-label="Record type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LABELS.map((value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="graph-filter">Name contains</Label>
              <Input
                id="graph-filter"
                value={nameContains}
                onChange={(event) => setNameContains(event.target.value)}
                placeholder="Northwind"
              />
            </div>

            {nodes.isError ? <ErrorState error={nodes.error} onRetry={() => void nodes.refetch()} /> : null}
            {nodes.isLoading ? <LoadingState label="Listing records of this type" /> : null}

            <ul className="max-h-[380px] space-y-1 overflow-y-auto pr-1 scrollbar-thin">
              {(nodes.data?.items ?? []).map((node) => {
                const active = selected?.key === node.key && selected?.label === node.label;
                return (
                  <li key={`${node.label}-${node.key}`}>
                    <button
                      type="button"
                      onClick={() => paths.mutate({ label: node.label, key: node.key })}
                      aria-pressed={active}
                      className={cn(
                        "w-full rounded-md border px-2.5 py-2 text-left text-xs transition-colors duration-micro",
                        active ? "border-primary/45 bg-primary/10" : "hover:bg-accent",
                      )}
                    >
                      <span className="block truncate font-medium">{String(node.properties.name ?? node.key)}</span>
                      <span className="block truncate font-mono text-[10px] text-muted-foreground">{node.key}</span>
                    </button>
                  </li>
                );
              })}
            </ul>

            {nodes.data && nodes.data.items.length === 0 ? (
              <EmptyState title="No record of this type" description="Nothing of this type exists for the current tenant." />
            ) : null}
          </div>
        </section>

        <section aria-labelledby="traversal" className="min-w-0 space-y-4">
          <div className="flex flex-wrap items-end gap-3 rounded-lg border p-3">
            <h2 id="traversal" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Network className="h-3.5 w-3.5" aria-hidden="true" />
              Traversal
            </h2>
            <div className="ml-auto flex items-end gap-2">
              <div className="space-y-1.5">
                <Label>Hops</Label>
                <Select value={maxHops} onValueChange={setMaxHops}>
                  <SelectTrigger className="w-[120px]" aria-label="Traversal depth">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {["1", "2", "3", "4"].map((value) => (
                      <SelectItem key={value} value={value}>
                        {plural(Number(value), "hop")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled={!selected || paths.isPending}
                onClick={() => selected && paths.mutate(selected)}
              >
                Re-run traversal
              </Button>
            </div>
          </div>

          {paths.data && paths.data.nodes.length > 0 ? (
            <LazyGraphScene
              root={{ label: paths.data.root.label, key: paths.data.root.key, name: selectedNode ? String(selectedNode.properties.name ?? selectedNode.key) : undefined }}
              nodes={paths.data.nodes}
              edges={paths.data.edges}
              hops={paths.data.hops}
              onSelect={(node) => paths.mutate({ label: node.label, key: node.key })}
              fallback={<NeighbourhoodFallback nodes={paths.data.nodes} edges={paths.data.edges} />}
            />
          ) : null}

          {selectedNode ? (
            <div className="rounded-lg border p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium">{String(selectedNode.properties.name ?? selectedNode.key)}</p>
                  <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">{selectedNode.key}</p>
                </div>
                {entityHref(selectedNode.label, selectedNode.key) ? (
                  <Button variant="outline" size="sm" asChild>
                    <Link to={entityHref(selectedNode.label, selectedNode.key)!}>
                      Open record
                      <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                    </Link>
                  </Button>
                ) : null}
              </div>
              <dl className="mt-3 grid gap-x-6 gap-y-1.5 text-[11px] sm:grid-cols-2">
                {Object.entries(selectedNode.properties)
                  .filter(([key]) => key !== "tenant_id")
                  .map(([key, value]) => (
                    <div key={key} className="flex gap-2 border-b border-border/60 pb-1">
                      <dt className="w-32 shrink-0 text-muted-foreground">{titleCase(key)}</dt>
                      <dd className="min-w-0 truncate font-medium">
                        {value === null || value === undefined || value === "" ? "not recorded" : String(value)}
                      </dd>
                    </div>
                  ))}
              </dl>
            </div>
          ) : null}

          {paths.isPending ? <LoadingState label="Traversing the graph" /> : null}
          {paths.isError ? <ErrorState error={paths.error} onRetry={() => selected && paths.mutate(selected)} /> : null}

          {paths.data ? (
            paths.data.edges.length === 0 ? (
              <EmptyState
                icon={GitBranch}
                title="This record has no relationships yet"
                description="Relationships are created during ingestion and reconciliation, so a record that arrived before its contract may still be unattached."
              />
            ) : (
              <div className="rounded-lg border">
                <Table>
                  <caption className="sr-only">
                    Edges within {paths.data.hops} hop(s) of the selected record.
                  </caption>
                  <TableHeader>
                    <TableRow>
                      <TableHead scope="col">Relationship</TableHead>
                      <TableHead scope="col">From</TableHead>
                      <TableHead scope="col">To</TableHead>
                      <TableHead scope="col" className="text-right">
                        Link
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paths.data.edges.map((edge, index) => (
                      <TableRow key={index}>
                        <TableCell className="text-xs">
                          <Badge variant="outline" className="font-normal">
                            {titleCase(edge.type)}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs">
                          <Endpoint label={edge.start.label} nodeKey={edge.start.key} />
                        </TableCell>
                        <TableCell className="text-xs">
                          <Endpoint label={edge.end.label} nodeKey={edge.end.key} />
                        </TableCell>
                        <TableCell className="text-right">
                          {entityHref(edge.end.label, edge.end.key) ? (
                            <Link
                              to={entityHref(edge.end.label, edge.end.key)!}
                              className="text-xs font-medium text-primary hover:underline"
                            >
                              Open
                            </Link>
                          ) : (
                            <span className="text-[11px] text-muted-foreground">no page</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )
          ) : null}

          {paths.data ? (
            <p className="text-[11px] text-muted-foreground">
              {plural(paths.data.nodes.length, "record")} within {plural(paths.data.hops, "hop")} of the selected record.
              Records without a detail page show their stored properties above instead of linking nowhere.
            </p>
          ) : null}

          {!paths.data && !paths.isPending ? (
            <EmptyState
              icon={Network}
              title="Select a record to traverse"
              description="Pick a supplier, contract or document on the left to see what it is connected to."
            />
          ) : null}

          {overview.isLoading ? <LoadingRows rows={3} /> : null}
        </section>
      </div>
    </div>
  );
}

function Endpoint({ label, nodeKey }: { label: string; nodeKey: string }) {
  const href = entityHref(label, nodeKey);
  const content = (
    <>
      <span className="text-muted-foreground">{label}:</span> <span className="font-mono text-[11px]">{nodeKey.slice(0, 8)}</span>
    </>
  );
  if (!href) return <span>{content}</span>;
  return (
    <Link to={href} className="hover:underline">
      {content}
    </Link>
  );
}
