/**
 * Which band the workspace draws for a given page.
 *
 * This module is deliberately free of three.js: the written band needs the
 * courier's suitcase label before the 3D layer has been fetched, and the eager
 * loader must not drag the renderer into the first paint to get it.
 */

export type BandRouteKey =
  | "dashboard"
  | "ask"
  | "search"
  | "documents"
  | "documentDetail"
  | "contracts"
  | "suppliers"
  | "compare"
  | "relationships"
  | "other";

export interface BandRouteConfig {
  /** The real collection the courier is carrying for this page. */
  caseLabel: string;
  /** Share of the tier's paper budget this page spends. */
  paper: number;
}

export const BAND_ROUTES: Record<BandRouteKey, BandRouteConfig> = {
  dashboard: { caseLabel: "Prices", paper: 1 },
  ask: { caseLabel: "Evidence", paper: 0.8 },
  search: { caseLabel: "Documents", paper: 0.8 },
  documents: { caseLabel: "Documents", paper: 1 },
  documentDetail: { caseLabel: "Documents", paper: 0.7 },
  contracts: { caseLabel: "Contracts", paper: 0.9 },
  suppliers: { caseLabel: "Suppliers", paper: 0.9 },
  compare: { caseLabel: "Prices", paper: 0.7 },
  relationships: { caseLabel: "Contracts", paper: 1 },
  other: { caseLabel: "Evidence", paper: 0.7 },
};

/** The real collection the courier carries for a page — used by the SVG band too. */
export function bandCaseLabel(route: BandRouteKey): string {
  return BAND_ROUTES[route]?.caseLabel ?? BAND_ROUTES.other.caseLabel;
}

/** Which band a pathname asks for. Detail pages get their own entry. */
export function bandRouteKey(pathname: string): BandRouteKey {
  const path = pathname.split("?")[0];
  if (path.startsWith("/dashboard")) return "dashboard";
  if (path.startsWith("/ask")) return "ask";
  if (path.startsWith("/search")) return "search";
  if (/^\/documents\/[^/]+/.test(path)) return "documentDetail";
  if (path.startsWith("/documents")) return "documents";
  if (path.startsWith("/contracts")) return "contracts";
  if (path.startsWith("/suppliers")) return "suppliers";
  if (path.startsWith("/compare")) return "compare";
  if (path.startsWith("/graph")) return "relationships";
  return "other";
}
