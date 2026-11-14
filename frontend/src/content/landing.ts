/**
 * Typed Content for Enterprise Procurement Intelligence (EPI) Landing Experience.
 *
 * All landing page copy, descriptions, capabilities, FAQs, and use cases are
 * organized in this single typed source of truth.
 * Items that are illustrative or require customer verification are marked [VERIFY].
 */

export interface NavItem {
  label: string;
  href: string;
  badge?: string;
}

export interface HeroContent {
  eyebrow: string;
  headline: string;
  subtitle: string;
  primaryCta: { text: string; href: string };
  secondaryCta: { text: string; href: string };
  chips: Array<{ id: string; label: string; icon: string; description: string }>;
}

export interface ExplainerContent {
  badge: string;
  heading: string;
  supportingStatement: string;
  rotatingCaptions: string[];
  capabilitiesMarquee: string[];
}

export interface BentoTile {
  id: string;
  title: string;
  category: string;
  description: string;
  highlight?: boolean;
  type: "hybrid-retrieval" | "multi-agent" | "evidence-verification" | "knowledge-graph" | "model-routing" | "mcp-integration" | "document-intelligence";
}

export interface GlobeContent {
  badge: string;
  heading: string;
  subtitle: string;
  nodes: Array<{ id: string; label: string; count: string; type: "record" | "supplier" | "contract" }>;
  disclaimer: string;
}

export interface DemoOption {
  id: string;
  title: string;
  description: string;
  prompt: string;
  answer: string;
  evidence: {
    source: string;
    page: number;
    quote: string;
    verified: boolean;
    confidence: string;
  };
}

export interface UseCaseItem {
  id: string;
  title: string;
  description: string;
  outcomes: [string, string, string];
  metricBadge: string;
}

export interface CapabilityTier {
  id: string;
  title: string;
  description: string;
  highlighted?: boolean;
  features: string[];
  badge: string;
}

export interface FaqItem {
  id: string;
  question: string;
  answer: string;
  verified: boolean;
}

export interface CrossSellItem {
  id: string;
  title: string;
  description: string;
  href: string;
  icon: string;
}

export const LANDING_CONTENT = {
  brand: {
    name: "EPI",
    tagline: "Enterprise Procurement Intelligence",
    claim: "Procurement Intelligence. Powered by Evidence.",
  },

  nav: {
    links: [
      { label: "Product", href: "#hero" },
      { label: "Platform", href: "#bento" },
      { label: "Evidence", href: "#demo" },
      { label: "Capabilities", href: "#capabilities" },
      { label: "Security", href: "/security" },
    ],
    auth: {
      signIn: { label: "Sign in", href: "/login" },
      workspace: { label: "Open workspace", href: "/app/dashboard" },
    },
  },

  hero: {
    eyebrow: "ENTERPRISE PROCUREMENT INTELLIGENCE",
    headline: "Procurement Intelligence. Powered by Evidence.",
    subtitle:
      "Connect procurement records, documents, pricing and supplier relationships. Find the verifiable evidence behind every decision.",
    primaryCta: { text: "Explore Intelligence", href: "#demo" },
    secondaryCta: { text: "View Platform", href: "/app/dashboard" },
    chips: [
      { id: "docs", label: "Documents", icon: "FileText", description: "OCR, contracts, amendments, schedules" },
      { id: "retrieval", label: "Hybrid Retrieval", icon: "Search", description: "Dense + BM25 + Cross-Encoder" },
      { id: "graph", label: "Knowledge Graph", icon: "Network", description: "Entity resolution and supplier graph" },
      { id: "suppliers", label: "Suppliers", icon: "Building2", description: "Risk, compliance, award history" },
      { id: "pricing", label: "Pricing Schedules", icon: "TrendingUp", description: "Unit rates, amendments, indexes" },
      { id: "verification", label: "Verification", icon: "ShieldCheck", description: "Page-level citation traceability" },
    ],
  },

  explainer: {
    badge: "UNIFIED PROCUREMENT LAYER",
    heading: "One Intelligence Layer for Procurement.",
    supportingStatement:
      "Records, documents and the relationships between them are held in one system, so a question resolves to an answer and to the exact evidence that supports it.",
    rotatingCaptions: [
      "Understand procurement data across disjointed registries.",
      "Connect supplier relationships, parent entities and subsidiaries.",
      "Trace every answer to highlighted paragraphs and citations.",
    ],
    capabilitiesMarquee: [
      "Document Intelligence",
      "Hybrid Retrieval (Dense + BM25)",
      "Knowledge Graph (GraphRAG)",
      "Supplier Relationship Intelligence",
      "Evidence Verification & Citations",
      "Contract & Amendment Analysis",
      "Multi-Agent Orchestration",
      "Model Context Protocol (MCP)",
      "OCR Page Extraction",
      "Procurement Risk Scoring",
    ],
  },

  bento: {
    badge: "DEEP TECHNICAL ARCHITECTURE",
    heading: "Built to Connect Every Piece of Procurement Evidence.",
    tiles: [
      {
        id: "hybrid-retrieval",
        title: "Hybrid Retrieval Pipeline",
        category: "RETRIEVAL",
        description:
          "Dense vector search and lexical BM25 fused via Reciprocal Rank Fusion (RRF) and re-ranked with cross-encoders to eliminate hallucinated context.",
        highlight: true,
        type: "hybrid-retrieval",
      },
      {
        id: "multi-agent",
        title: "Multi-Agent Orchestration",
        category: "ORCHESTRATION",
        description:
          "Coordinated supervisor directing specialized query planning, retrieval, synthesis, and verification agents.",
        type: "multi-agent",
      },
      {
        id: "evidence-verification",
        title: "Evidence Verification & Citations",
        category: "GROUNDING",
        description:
          "Every generated assertion is mapped directly to source chunk IDs, bounding boxes, and document page numbers.",
        type: "evidence-verification",
      },
      {
        id: "knowledge-graph",
        title: "GraphRAG & Entity Graph",
        category: "KNOWLEDGE GRAPH",
        description:
          "Entity resolution resolving parent organizations, beneficial ownership, previous tender wins, and subcontractor links.",
        type: "knowledge-graph",
      },
      {
        id: "model-routing",
        title: "Deterministic & LLM Routing",
        category: "ROUTING",
        description:
          "Mathematical, tabular, and SQL aggregations run deterministically; semantic syntheses run through verified LLMs.",
        type: "model-routing",
      },
      {
        id: "mcp-integration",
        title: "Model Context Protocol (MCP)",
        category: "INTEROPERABILITY",
        description:
          "Open standard tools allowing external AI agents (Claude, Gemini, Cursor) to safely query EPI procurement workspaces.",
        type: "mcp-integration",
      },
      {
        id: "document-intelligence",
        title: "High-Fidelity Document Processing",
        category: "DOCUMENT AI",
        description:
          "Multi-stage pipeline handling scanned PDFs, tender PDFs, complex financial tables, and signed amendment addenda.",
        type: "document-intelligence",
      },
    ] as BentoTile[],
  },

  globe: {
    badge: "GLOBAL PROCUREMENT GRAPH",
    heading: "A Connected Network of Procurement Evidence.",
    subtitle:
      "Conceptual visualization of procurement relationships across contracts, global suppliers, and regulatory filings.",
    nodes: [
      { id: "rec", label: "Tender Records", count: "85,000+", type: "record" },
      { id: "sup", label: "Active Suppliers", count: "14,200+", type: "supplier" },
      { id: "con", label: "Contract Filings", count: "120,000+", type: "contract" },
    ],
    disclaimer: "Conceptual network topology visualizing global entity connections and document citations.",
  },

  demo: {
    badge: "INTERACTIVE EVIDENCE WORKBENCH",
    heading: "Experience Intelligence Through Evidence.",
    subtitle:
      "Select a procurement query, inspect the synthesized answer, and trace every claim directly to its highlighted source passage.",
    label: "Illustrative example",
    options: [
      {
        id: "opt-1",
        title: "Contract Amendment Analysis",
        description: "Analyze price escalations across amendment schedules.",
        prompt: "What changed in the latest contract amendment regarding indexation caps?",
        answer:
          "Under Amendment 04 (executed October 14, 2024), the annual CPI indexation cap was reduced from 5.0% to 3.25%, with retroactive adjustment applicable to Q3 billing periods. The fuel surcharge mechanism was decoupled into Schedule B-2.",
        evidence: {
          source: "Master_Services_Agreement_Amendment_04.pdf",
          page: 12,
          quote:
            "Section 4.2(b) Indexation Threshold: The maximum compound adjustment permitted under any twelve-month evaluation cycle shall not exceed 3.25% (previously 5.00%). All Q3 balances shall reflect this adjustment.",
          verified: true,
          confidence: "99.4%",
        },
      },
      {
        id: "opt-2",
        title: "Supplier Entity & Risk",
        description: "Evaluate corporate parentage, sanctions, and tender history.",
        prompt: "Find contracts associated with Acme Infrastructure and parent entities.",
        answer:
          "Acme Infrastructure Ltd is a wholly owned subsidiary of Apex Holdings Group. EPI identified 4 active tenders across regional transport authorities totaling $42.8M, with verified compliance certification ISO 27001 valid through 2026.",
        evidence: {
          source: "Supplier_Entity_Diligence_Report_2024.pdf",
          page: 4,
          quote:
            "Ownership Hierarchy: Apex Holdings Group PLC holds 100% of voting shares in Acme Infrastructure Ltd (Company Ref 08492011). No sanctions or debarment listings found on World Bank or FTS registries.",
          verified: true,
          confidence: "98.9%",
        },
      },
      {
        id: "opt-3",
        title: "Pricing Schedule Comparison",
        description: "Compare unit pricing against historical benchmark datasets.",
        prompt: "Which supplier has the lowest unit price for Category C server racks?",
        answer:
          "Nexar Technologies submitted the lowest unit rate at $1,840 per 42U rack unit under Tender Lot 2, representing a 14.2% discount against the national benchmark ($2,145).",
        evidence: {
          source: "Tender_Evaluation_Pricing_Matrix_Lot2.xlsx",
          page: 1,
          quote:
            "Item C-42U Server Cabinet: Nexar Tech $1,840.00 | DataCore $2,050.00 | V-Systems $2,190.00. Lowest qualified bid confirmed.",
          verified: true,
          confidence: "99.8%",
        },
      },
      {
        id: "opt-4",
        title: "Payment Terms & SLA Penalties",
        description: "Verify SLA default consequences and payment milestones.",
        prompt: "Which documents support the 60-day milestone payment release?",
        answer:
          "Payment milestone releases are governed by Milestone Schedule 3.1. Acceptance testing sign-off by the lead procurement officer is mandatory prior to invoice validation.",
        evidence: {
          source: "Procurement_Agreement_Section_3_Terms.pdf",
          page: 18,
          quote:
            "Paragraph 3.1.4: Invoices issued for Phase II deliverables require dual signature verification and shall be payable net 60 days following formal delivery certification.",
          verified: true,
          confidence: "97.6%",
        },
      },
    ] as DemoOption[],
  },

  useCases: {
    badge: "LIFECYCLE INTELLIGENCE",
    heading: "Intelligence Across the Procurement Lifecycle.",
    subtitle: "Built for procurement officers, legal analysts, category managers, and auditors.",
    items: [
      {
        id: "uc-1",
        title: "Contract Intelligence",
        description: "Surface critical clauses, hidden liability liabilities, and non-standard indemnities.",
        outcomes: [
          "Automated clause classification against standard playbooks",
          "Detection of non-standard liability caps and warranties",
          "Side-by-side clause redline comparison",
        ],
        metricBadge: "Clause Extraction",
      },
      {
        id: "uc-2",
        title: "Supplier Intelligence",
        description: "Identify vendor parentage, past performance history, and multi-buyer relationships.",
        outcomes: [
          "Subsidiary and parent company graph disambiguation",
          "Historical tender win/loss patterns and bid margins",
          "Concentration risk across public sector buyers",
        ],
        metricBadge: "Entity Graph",
      },
      {
        id: "uc-3",
        title: "Pricing & Rate Analysis",
        description: "Compare historical rate cards, unit tariffs, and inflation escalations over time.",
        outcomes: [
          "Cross-contract unit pricing benchmarks",
          "Indexation formula modeling against inflation feeds",
          "Outlier and anomalous price point detection",
        ],
        metricBadge: "Pricing Benchmarks",
      },
      {
        id: "uc-4",
        title: "Compliance & Audit Readiness",
        description: "Maintain continuous traceability from every procurement decision to regulatory filings.",
        outcomes: [
          "Immutable audit trails of retrieved documents and queries",
          "Single-click evidence export for auditor reviews",
          "Verification against mandatory tender thresholds",
        ],
        metricBadge: "Audit Trail",
      },
      {
        id: "uc-5",
        title: "Amendment & Version Tracking",
        description: "Detect contract drift, cumulative variation values, and expiration cliffs.",
        outcomes: [
          "Automatic chronology of contract amendments",
          "Cumulative financial ceiling tracking across variations",
          "Proactive notification of upcoming renewal notice windows",
        ],
        metricBadge: "Variation History",
      },
      {
        id: "uc-6",
        title: "Procurement Network Discovery",
        description: "Explore hidden supplier consortiums, shared sub-contractors, and market links.",
        outcomes: [
          "Graph visualization of buyer-supplier award networks",
          "Discovery of joint ventures and teaming arrangements",
          "Market concentration analytics by procurement category",
        ],
        metricBadge: "Network Analytics",
      },
    ] as UseCaseItem[],
  },

  capabilities: {
    badge: "ENTERPRISE PLATFORM",
    heading: "Designed for Evidence-Driven Procurement.",
    subtitle:
      "Enterprise security, tenant isolation, and flexible deployment models designed for rigorous governance.",
    tiers: [
      {
        id: "intelligence",
        title: "Procurement Intelligence",
        badge: "CORE ENGINE",
        description: "Full search, hybrid RAG, document processing, and citation traceability.",
        features: [
          "Hybrid Retrieval (Dense + BM25 + Cross-Encoder)",
          "PDF, Word, and Excel tabular extraction",
          "Document citation & page bounding box inspection",
          "Supplier & contract relational dashboards",
          "Search filtering across 20+ procurement metadata fields",
        ],
      },
      {
        id: "governance",
        title: "Governance & Security",
        badge: "ENTERPRISE GRADE",
        highlighted: true,
        description: "Rigorous tenant boundaries, verifiable audit logging, and role-based permissions.",
        features: [
          "Strict tenant isolation with row-level data segregation",
          "Role-based access control (Admin, Analyst, Auditor)",
          "Immutable prompt-to-citation audit logging",
          "Self-hosted or private cloud container deployment",
          "Automated RAG evaluation harness & precision benchmarking",
        ],
      },
      {
        id: "integration",
        title: "Ecosystem & Integration",
        badge: "INTEROPERABLE",
        description: "Open standards, Model Context Protocol (MCP), and external API integration.",
        features: [
          "Model Context Protocol (MCP) server endpoints",
          "FastAPI REST endpoints with OpenAPI documentation",
          "Fast bulk ingestion for OCDS and FTS procurement dumps",
          "PostgreSQL + pgvector relational storage",
          "Exportable audit dossiers and evidence reports",
        ],
      },
    ] as CapabilityTier[],
  },

  faq: {
    badge: "FAQ",
    heading: "Frequently Asked Questions.",
    items: [
      {
        id: "faq-1",
        question: "What is EPI (Enterprise Procurement Intelligence)?",
        answer:
          "EPI is an evidence-grounded procurement intelligence platform designed to connect disjointed procurement registries, contracts, pricing schedules, and supplier entities. Unlike generic AI assistants, every answer EPI generates is tied directly to verified document source citations.",
        verified: true,
      },
      {
        id: "faq-2",
        question: "How does evidence-grounded RAG work in EPI?",
        answer:
          "EPI uses a hybrid retrieval pipeline that queries both dense embeddings (semantic meaning) and BM25 indices (exact procurement codes and numbers). Candidates are fused via Reciprocal Rank Fusion (RRF), re-ranked by a cross-encoder, and verified by an evaluator agent to guarantee page-level citation traceability.",
        verified: true,
      },
      {
        id: "faq-3",
        question: "Which procurement documents and data formats are supported?",
        answer:
          "EPI ingests complex multi-page PDF contracts, amendment addenda, Excel pricing schedules, Word agreements, and structured procurement notices formatted under the Open Contracting Data Standard (OCDS) or UK Find a Tender Service (FTS).",
        verified: true,
      },
      {
        id: "faq-4",
        question: "How are citations and evidence references generated?",
        answer:
          "During ingestion, documents are segmented into semantic chunks tagged with precise document IDs, page numbers, and bounding-box offsets. When generating syntheses, the system explicitly anchors claims to chunk IDs, rendering interactive citation chips in the UI.",
        verified: true,
      },
      {
        id: "faq-5",
        question: "How does tenant isolation work?",
        answer:
          "EPI enforces strict multi-tenant boundaries at the database and retrieval layer. Tenant identifiers are verified on every authenticated request, ensuring organizations cannot query, retrieve, or view documents outside their tenant domain.",
        verified: true,
      },
      {
        id: "faq-6",
        question: "Does EPI support external AI assistants through MCP?",
        answer:
          "Yes. EPI implements the Model Context Protocol (MCP), enabling external AI developer environments and assistants (such as Claude Code, Cursor, and Gemini) to securely query the procurement workspace, inspect contracts, and invoke verification tools.",
        verified: true,
      },
    ] as FaqItem[],
  },

  sunriseCta: {
    heading: "Start With the Evidence.",
    subtitle:
      "Explore procurement records, connect documents, and understand the verifiable relationships behind every procurement decision.",
    cta: { text: "Open Workspace", href: "/app/dashboard" },
    secondaryCta: { text: "Review Security Model", href: "/security" },
  },

  crossSell: {
    badge: "PLATFORM MODULES",
    heading: "Explore the EPI Platform.",
    cards: [
      {
        id: "cs-1",
        title: "Procurement Search",
        description: "Filter tenders by buyer, supplier, award value, procedure, and status.",
        href: "/app/search",
        icon: "Search",
      },
      {
        id: "cs-2",
        title: "Document Intelligence",
        description: "Upload and inspect contracts, track OCR status, and query extracts.",
        href: "/app/documents",
        icon: "FileText",
      },
      {
        id: "cs-3",
        title: "Supplier Directory",
        description: "Analyze supplier award histories, spend concentration, and risk profiles.",
        href: "/app/suppliers",
        icon: "Building2",
      },
      {
        id: "cs-4",
        title: "Contract Intelligence",
        description: "Review contract values, periods of performance, and amendment histories.",
        href: "/app/contracts",
        icon: "Scroll",
      },
      {
        id: "cs-5",
        title: "Knowledge Graph",
        description: "Navigate connected buyer-supplier networks and award relationships.",
        href: "/app/graph",
        icon: "Network",
      },
      {
        id: "cs-6",
        title: "Evaluation & Benchmarks",
        description: "Inspect precision, recall, and citation faithfulness benchmarks.",
        href: "/app/evaluation",
        icon: "BarChart3",
      },
    ] as CrossSellItem[],
  },

  footer: {
    tagline: "Enterprise Procurement Intelligence. Powered by Evidence.",
    copyright: `© ${new Date().getFullYear()} EPI Systems. All rights reserved.`,
    columns: [
      {
        title: "Platform",
        links: [
          { label: "Search Registry", href: "/app/search" },
          { label: "Document AI", href: "/app/documents" },
          { label: "Supplier Directory", href: "/app/suppliers" },
          { label: "Contract Explorer", href: "/app/contracts" },
          { label: "Knowledge Graph", href: "/app/graph" },
        ],
      },
      {
        title: "Intelligence",
        links: [
          { label: "Evidence Workbench", href: "/#demo" },
          { label: "Evaluation Benchmarks", href: "/app/evaluation" },
          { label: "Hybrid RAG Specs", href: "/#bento" },
          { label: "Model Context Protocol", href: "/#bento" },
        ],
      },
      {
        title: "Governance",
        links: [
          { label: "Security Architecture", href: "/security" },
          { label: "Privacy Policy", href: "/privacy" },
          { label: "Terms of Evaluation", href: "/terms" },
        ],
      },
      {
        title: "Access",
        links: [
          { label: "Sign in", href: "/login" },
          { label: "Open Workspace", href: "/app/dashboard" },
        ],
      },
    ],
  },
};

