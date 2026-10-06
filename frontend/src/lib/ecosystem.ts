/**
 * Turns the workspace's own records into the procurement ecosystem drawn on the
 * overview page.
 *
 * This module is deliberately pure: it receives the same payloads the tables
 * below the scene use and derives every node from a real row. Nothing here
 * invents a supplier, a contract, a price or a document, and every node carries
 * the number of records it stands for so an aggregated node cannot be read as a
 * single record.
 */
import type { Compliance, Contract, DocumentSummary, Price, Supplier } from "@/lib/types";
import { NOT_RECORDED, documentTypeLabel } from "@/lib/utils";

/** Left to right: supplier → contract → product → price → evidence. */
export type EcosystemTier = "supplier" | "contract" | "product" | "price" | "evidence" | "compliance" | "amendment";

export const TIER_ORDER: EcosystemTier[] = ["supplier", "contract", "product", "price", "evidence"];

export interface EcosystemNode {
  id: string;
  tier: EcosystemTier;
  /** Business label, as recorded. */
  label: string;
  /** Second line of the tooltip: where the node came from. */
  detail: string;
  /** Real route for this record, when the workspace has a page for it. */
  href: string | null;
  /** How many stored rows this node stands for. Always ≥ 1. */
  count: number;
}

export interface EcosystemLink {
  from: string;
  to: string;
}

export interface EcosystemModel {
  nodes: EcosystemNode[];
  links: EcosystemLink[];
  /** Totals over the whole workspace, for the caption and the text alternative. */
  totals: { tier: EcosystemTier; label: string; count: number; shown: number }[];
  /** Set when the workspace holds no supplier record at all. */
  empty: boolean;
}

/** Hard caps so a large corpus cannot turn the hero band into a thicket. */
const CAP: Record<EcosystemTier, number> = {
  supplier: 8,
  contract: 14,
  product: 18,
  price: 26,
  evidence: 22,
  compliance: 8,
  amendment: 10,
};

export function buildEcosystem({
  suppliers,
  contracts,
  prices,
  compliance,
  documents,
}: {
  suppliers: Supplier[];
  contracts: Contract[];
  prices: Price[];
  compliance: Compliance[];
  documents: DocumentSummary[];
}): EcosystemModel {
  const nodes: EcosystemNode[] = [];
  const links: EcosystemLink[] = [];
  const link = (from: string, to: string) => links.push({ from, to });

  // ------------------------------------------------------------- suppliers
  [...suppliers]
    .sort((a, b) => a.name.localeCompare(b.name))
    .slice(0, CAP.supplier)
    .forEach((supplier) => {
      const node: EcosystemNode = {
        id: `supplier:${supplier.id}`,
        tier: "supplier",
        label: supplier.name,
        detail: [
          supplier.category ?? "no category recorded",
          `${supplier.contract_count} contract(s)`,
          `${supplier.price_count} price row(s)`,
        ].join(" · "),
        href: `/suppliers/${supplier.id}`,
        count: Math.max(supplier.contract_count + supplier.document_count + supplier.price_count, 1),
      };
      nodes.push(node);
    });
  const supplierById = new Map(suppliers.map((supplier) => [supplier.id, supplier]));

  // ------------------------------------------------------------- contracts
  const contractNodes = [...contracts]
    .sort((a, b) => a.contract_number.localeCompare(b.contract_number))
    .slice(0, CAP.contract)
    .map((contract) => {
      const node: EcosystemNode = {
        id: `contract:${contract.id}`,
        tier: "contract",
        label: contract.contract_number,
        detail: [
          contract.title,
          supplierById.get(contract.supplier_id ?? "")?.name ?? contract.supplier_name ?? "supplier not linked",
          contract.is_expired ? "term has ended" : "in force as recorded",
        ].join(" · "),
        href: `/contracts/${contract.id}`,
        count: Math.max((contract.price_count ?? 0) + (contract.amendment_count ?? 0), 1),
      };
      nodes.push(node);
      if (contract.supplier_id && nodes.some((item) => item.id === `supplier:${contract.supplier_id}`)) {
        link(`supplier:${contract.supplier_id}`, node.id);
      }
      return node;
    });
  const contractIds = new Set(contractNodes.map((node) => node.id.replace("contract:", "")));

  // -------------------------------------------------- products and prices
  // One product node per contract/product pair, carrying the real number of
  // price rows behind it, so the product tier stays readable.
  interface ProductGroup {
    key: string;
    contractId: string | null;
    productId: string | null;
    name: string;
    rows: Price[];
  }
  const groups = new Map<string, ProductGroup>();
  for (const price of prices) {
    const key = `${price.contract_id ?? "no-contract"}|${price.product_id ?? price.product_name ?? "no-product"}`;
    const group = groups.get(key) ?? {
      key,
      contractId: price.contract_id,
      productId: price.product_id,
      name: price.product_name ?? NOT_RECORDED,
      rows: [],
    };
    group.rows.push(price);
    groups.set(key, group);
  }

  const orderedGroups = [...groups.values()].sort((a, b) => a.name.localeCompare(b.name));
  const productNodes = orderedGroups.slice(0, CAP.product).map((group) => {
    const id = `product:${group.key}`;
    const node: EcosystemNode = {
      id,
      tier: "product",
      label: group.name,
      detail: [
        `${group.rows.length} price row(s)`,
        supplierById.get(group.rows[0]?.supplier_id ?? "")?.name ?? group.rows[0]?.supplier_name ?? "supplier not linked",
      ].join(" · "),
      href: null,
      count: group.rows.length,
    };
    nodes.push(node);
    if (group.contractId && contractIds.has(group.contractId)) {
      link(`contract:${group.contractId}`, id);
    }
    return node;
  });
  const productIds = new Set(productNodes.map((node) => node.id.replace("product:", "")));

  // Price nodes aggregate the rows behind one product, keeping the newest
  // recorded effective date and the amendment that set it.
  const priceNodes = orderedGroups
    .filter((group) => productIds.has(group.key))
    .slice(0, CAP.price)
    .map((group) => {
      const rows = [...group.rows].sort((a, b) =>
        (b.effective_date ?? "").localeCompare(a.effective_date ?? ""),
      );
      const newest = rows[0];
      const amendments = [...new Set(rows.map((row) => row.amendment_ref).filter(Boolean))];
      const id = `price:${group.key}`;
      const node: EcosystemNode = {
        id,
        tier: "price",
        label: `${group.name} · ${newest.currency} ${newest.unit_price}`,
        detail: [
          `${rows.length} price row(s)`,
          newest.effective_date ? `newest effective ${newest.effective_date}` : "no effective date recorded",
          amendments.length > 0 ? `set by ${amendments.join(", ")}` : "no amendment referenced",
        ].join(" · "),
        href: newest.source_document_id
          ? `/documents/${newest.source_document_id}${newest.source_page ? `?page=${newest.source_page}` : ""}`
          : null,
        count: rows.length,
      };
      nodes.push(node);
      link(`product:${group.key}`, id);
      return { node, group, rows };
    });

  // ---------------------------------------------------------------- evidence
  const documentNodes = [...documents]
    .sort((a, b) => (a.title || a.filename).localeCompare(b.title || b.filename))
    .slice(0, CAP.evidence)
    .map((document) => {
      const node: EcosystemNode = {
        id: `evidence:${document.id}`,
        tier: "evidence",
        label: document.title || document.filename,
        detail: [
          documentTypeLabel(document.document_type),
          document.version && document.version > 1 ? `version ${document.version}` : "version 1",
          document.page_count ? `${document.page_count} page(s)` : "page count not recorded",
        ].join(" · "),
        href: `/documents/${document.id}`,
        count: document.chunk_count ?? document.page_count ?? 1,
      };
      nodes.push(node);
      return node;
    });
  const documentIds = new Set(documentNodes.map((node) => node.id.replace("evidence:", "")));
  for (const { node, rows } of priceNodes) {
    for (const documentId of new Set(rows.map((row) => row.source_document_id).filter(Boolean))) {
      if (documentId && documentIds.has(documentId)) link(node.id, `evidence:${documentId}`);
    }
  }

  // -------------------------------------------------------------- compliance
  const complianceBySupplier = new Map<string, Compliance[]>();
  for (const certificate of compliance) {
    const list = complianceBySupplier.get(certificate.supplier_id) ?? [];
    list.push(certificate);
    complianceBySupplier.set(certificate.supplier_id, list);
  }
  for (const [supplierId, certificates] of complianceBySupplier) {
    const supplierNode = `supplier:${supplierId}`;
    if (!nodes.some((node) => node.id === supplierNode)) continue;
    const expiring = certificates.filter((certificate) => certificate.status !== "valid").length;
    const node: EcosystemNode = {
      id: `compliance:${supplierId}`,
      tier: "compliance",
      label: `${certificates.length} certificate(s)`,
      detail: [
        supplierById.get(supplierId)?.name ?? "supplier",
        expiring > 0 ? `${expiring} not recorded as valid` : "all recorded as valid",
      ].join(" · "),
      href: `/suppliers/${supplierId}`,
      count: certificates.length,
    };
    nodes.push(node);
    link(supplierNode, node.id);
  }

  // --------------------------------------------------------------- amendments
  const amendmentsByContract = new Map<string, Set<string>>();
  for (const price of prices) {
    if (!price.amendment_ref || !price.contract_id) continue;
    const set = amendmentsByContract.get(price.contract_id) ?? new Set<string>();
    set.add(price.amendment_ref);
    amendmentsByContract.set(price.contract_id, set);
  }
  let amendmentShown = 0;
  for (const [contractId, references] of amendmentsByContract) {
    if (amendmentShown >= CAP.amendment) break;
    const contractNode = `contract:${contractId}`;
    if (!nodes.some((node) => node.id === contractNode)) continue;
    for (const reference of [...references].sort()) {
      if (amendmentShown >= CAP.amendment) break;
      const id = `amendment:${contractId}:${reference}`;
      nodes.push({
        id,
        tier: "amendment",
        label: reference,
        detail: [
          `amendment referenced by price rows of ${contracts.find((contract) => contract.id === contractId)?.contract_number ?? "a contract"}`,
          "no separate page in the workspace",
        ].join(" · "),
        href: null,
        count: 1,
      });
      link(contractNode, id);
      amendmentShown += 1;
    }
  }

  const totals = TIER_ORDER.map((tier) => ({
    tier,
    label: tier,
    count:
      tier === "supplier"
        ? suppliers.length
        : tier === "contract"
          ? contracts.length
          : tier === "product"
            ? groups.size
            : tier === "price"
              ? prices.length
              : documents.length,
    shown: nodes.filter((node) => node.tier === tier).length,
  }));

  return { nodes, links, totals, empty: suppliers.length === 0 };
}
