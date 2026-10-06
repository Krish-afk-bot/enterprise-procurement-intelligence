import type { LucideIcon } from "lucide-react";
import {
  BadgeCheck,
  Boxes,
  FileStack,
  GitBranch,
  LayoutDashboard,
  LineChart,
  MessagesSquare,
  Search,
  Settings,
  Users,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Omitted for the workspace overview, which every signed-in user can read. */
  permission?: string;
}

export interface NavSection {
  label: string;
  items: NavItem[];
}

/**
 * Navigation mirrors how procurement work is done: see the state of the
 * workspace, ask, find evidence, analyse a supplier or contract, then
 * administer it.
 *
 * The procurement workspace is separated from administration on purpose. The
 * overview is readable by every signed-in account; the administration area is
 * limited to accounts that can *change* system settings (``admin:write``), which
 * in this deployment is the administrator role. Document, contract and supplier
 * permissions never hide a business page from a procurement user: they decide
 * what that user may change.
 */
export const NAV_SECTIONS: NavSection[] = [
  {
    label: "Workspace",
    items: [
      { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
      { to: "/ask", label: "Ask", icon: MessagesSquare, permission: "query:run" },
      { to: "/search", label: "Search", icon: Search, permission: "query:run" },
      { to: "/documents", label: "Documents", icon: FileStack, permission: "documents:read" },
      { to: "/contracts", label: "Contracts", icon: BadgeCheck, permission: "contracts:read" },
      { to: "/suppliers", label: "Suppliers", icon: Users, permission: "suppliers:read" },
      { to: "/compare", label: "Compare", icon: Boxes, permission: "compare:run" },
    ],
  },
  {
    label: "Analysis",
    items: [{ to: "/graph", label: "Relationships", icon: GitBranch, permission: "graph:read" }],
  },
  {
    // Administration also holds the technical views: search quality (Evaluation)
    // reports on the retrieval and answer pipeline and is not part of the
    // procurement workflow, so it lives here rather than beside the business pages.
    label: "Administration",
    items: [
      { to: "/admin", label: "Administration", icon: Settings, permission: "admin:write" },
      { to: "/evaluation", label: "Search quality", icon: LineChart, permission: "evaluation:read" },
    ],
  },
];

interface RouteMeta {
  match: RegExp;
  label: string;
  section: string;
}

/** Longest patterns first: detail routes must win over list routes. */
const ROUTE_META: RouteMeta[] = [
  { match: /^\/documents\/[^/]+$/, label: "Document", section: "Documents" },
  { match: /^\/contracts\/[^/]+$/, label: "Contract", section: "Contracts" },
  { match: /^\/suppliers\/[^/]+$/, label: "Supplier", section: "Suppliers" },
  { match: /^\/documents$/, label: "Documents", section: "Documents" },
  { match: /^\/contracts$/, label: "Contracts", section: "Contracts" },
  { match: /^\/suppliers$/, label: "Suppliers", section: "Suppliers" },
  { match: /^\/ask$/, label: "Ask", section: "Workspace" },
  { match: /^\/search$/, label: "Search", section: "Workspace" },
  { match: /^\/compare$/, label: "Compare", section: "Workspace" },
  { match: /^\/graph$/, label: "Relationships", section: "Analysis" },
  { match: /^\/evaluation$/, label: "Search quality", section: "Administration" },
  { match: /^\/dashboard$/, label: "Overview", section: "Workspace" },
  { match: /^\/admin$/, label: "Administration", section: "Administration" },
];

export function routeMeta(pathname: string): { label: string; section: string } {
  const found = ROUTE_META.find((entry) => entry.match.test(pathname));
  return found ? { label: found.label, section: found.section } : { label: "Workspace", section: "Workspace" };
}
