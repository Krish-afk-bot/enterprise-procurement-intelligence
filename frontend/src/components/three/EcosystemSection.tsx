import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Network } from "lucide-react";

import { ErrorState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { LazyEcosystemScene } from "@/components/three/LazyEcosystemScene";
import { api } from "@/lib/api";
import { buildEcosystem, TIER_ORDER } from "@/lib/ecosystem";
import { plural, titleCase } from "@/lib/utils";

/** What each tier is drawn in, stated in words so the colour is never the message. */
const TIER_MEANING: Record<string, string> = {
  supplier: "a supplier record",
  contract: "a contract record",
  product: "a product a price row refers to",
  price: "the price rows behind one product",
  evidence: "a document that carries a price or a term",
};

/**
 * The overview band. It reads the same endpoints the tables below use, so the
 * scene and the numbers can never disagree, and it falls back to a written
 * list of the same counts on a small screen or without WebGL.
 */
export function EcosystemSection() {
  const suppliers = useQuery({ queryKey: ["suppliers", "ecosystem"], queryFn: () => api.suppliers({ limit: 100 }) });
  const contracts = useQuery({ queryKey: ["contracts", "ecosystem"], queryFn: () => api.contracts({ limit: 100 }) });
  const prices = useQuery({ queryKey: ["prices", "ecosystem"], queryFn: () => api.prices({ limit: 200 }) });
  const compliance = useQuery({ queryKey: ["compliance", "ecosystem"], queryFn: () => api.compliance({ limit: 200 }) });
  const documents = useQuery({ queryKey: ["documents", "ecosystem"], queryFn: () => api.documents({ limit: 200 }) });

  const model = useMemo(
    () =>
      buildEcosystem({
        suppliers: suppliers.data?.items ?? [],
        contracts: contracts.data?.items ?? [],
        prices: prices.data?.items ?? [],
        compliance: compliance.data?.items ?? [],
        documents: documents.data?.items ?? [],
      }),
    [suppliers.data, contracts.data, prices.data, compliance.data, documents.data],
  );

  const failure = suppliers.error ?? contracts.error ?? prices.error ?? compliance.error ?? documents.error;
  if (failure) return <ErrorState error={failure} onRetry={() => void suppliers.refetch()} />;

  const loading =
    suppliers.isLoading || contracts.isLoading || prices.isLoading || compliance.isLoading || documents.isLoading;

  if (loading) {
    return (
      <section aria-labelledby="ecosystem-heading" className="rounded-lg border">
        <header className="border-b px-4 py-2.5">
          <h2 id="ecosystem-heading" className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Procurement ecosystem
          </h2>
        </header>
        <div className="flex h-[200px] items-center justify-center p-4 text-xs text-muted-foreground" role="status">
          Digging through the paperwork…
        </div>
      </section>
    );
  }

  if (model.empty) {
    return (
      <section aria-labelledby="ecosystem-heading" className="rounded-lg border">
        <header className="border-b px-4 py-2.5">
          <h2 id="ecosystem-heading" className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Procurement ecosystem
          </h2>
        </header>
        <div className="flex flex-col items-start gap-2 p-4">
          <p className="flex items-center gap-2 text-sm font-medium">
            <Network className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            Nothing to draw yet
          </p>
          <p className="max-w-xl text-xs leading-relaxed text-muted-foreground">
            The ecosystem view is built from the supplier, contract and price records in this workspace, and there are
            none yet. Upload a supplier agreement and it will appear here with the contract, prices and pages behind it.
          </p>
          <Button size="sm" asChild>
            <Link to="/documents">Upload a document</Link>
          </Button>
        </div>
      </section>
    );
  }

  const textAlternative = (
    <div className="space-y-2 text-xs">
      <p className="text-muted-foreground">
        {plural(model.nodes.length, "record")} drawn and {plural(model.links.length, "relationship")}. Records are capped
        per tier so the scene stays readable; the table below the scene lists every record with its own counts.
      </p>
      <ul className="flex flex-wrap gap-1.5">
        {model.totals.map((tier) => (
          <li
            key={tier.tier}
            className="rounded border bg-muted/40 px-2 py-1 text-[11px] text-muted-foreground"
            title={`${titleCase(tier.label)} — ${tier.shown} of ${tier.count} drawn`}
          >
            <span className="font-medium text-foreground">{tier.count}</span> {tier.label}
            {tier.shown < tier.count ? <span className="ml-1">({tier.shown} drawn)</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );

  const legend = (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
      {TIER_ORDER.map((tier) => (
        <li key={tier} className="flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block h-2 w-2 rounded-full border"
            style={{ background: tierSwatch(tier) }}
          />
          {titleCase(tier)} — {TIER_MEANING[tier]}
        </li>
      ))}
      <li className="flex items-center gap-1.5">
        <span aria-hidden="true" className="inline-block h-2 w-2 rounded-full border bg-success" />
        Compliance — certificates held by a supplier
      </li>
    </ul>
  );

  return (
    <section aria-labelledby="ecosystem-heading">
      <h2 id="ecosystem-heading" className="sr-only">
        Procurement ecosystem
      </h2>
      <LazyEcosystemScene model={model} fallback={textAlternative} legend={legend} />
    </section>
  );
}

/** Swatches read the same design tokens as the scene, so the key matches it. */
function tierSwatch(tier: string): string {
  switch (tier) {
    case "supplier":
      return "hsl(var(--primary))";
    case "contract":
      return "hsl(var(--foreground))";
    case "product":
      return "hsl(var(--info))";
    case "price":
      return "hsl(var(--warning))";
    default:
      return "hsl(var(--muted-foreground) / 0.5)";
  }
}
