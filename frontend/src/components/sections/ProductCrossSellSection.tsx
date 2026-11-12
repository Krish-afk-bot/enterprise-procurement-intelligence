import { useRef } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Search, Network, ShieldCheck, Layers, FileText } from "lucide-react";
import { WordReveal } from "@/components/animations/WordReveal";
import { useGridReveal } from "@/components/animations/useScrollReveal";

const PLATFORM_CARDS = [
  {
    id: "procurement-intelligence",
    icon: Search,
    title: "Procurement Intelligence",
    description: "Structured procurement data, tender and award analysis, and buyer-supplier insight.",
    link: "/dashboard",
  },
  {
    id: "document-intelligence",
    icon: FileText,
    title: "Document Intelligence",
    description: "OCR, semantic chunking, vision escalation, and contextual enrichment.",
    link: "/documents",
  },
  {
    id: "knowledge-graph",
    icon: Network,
    title: "Knowledge Graph",
    description: "Suppliers, contracts, amendments, and awards modeled as a traversable network.",
    link: "/graph",
  },
  {
    id: "evidence-evaluation",
    icon: ShieldCheck,
    title: "Evidence Evaluation",
    description: "Claim-to-passage binding, citation validation, and verification workflows.",
    link: "/ask",
  },
  {
    id: "security",
    icon: ShieldCheck,
    title: "Security",
    description: "Tenant isolation, authenticated sessions, and server-enforced permissions.",
    link: "/security",
  },
  {
    id: "platform-architecture",
    icon: Layers,
    title: "Platform Architecture",
    description: "Hybrid RAG, multi-agent orchestration, and evidence-grounded generation.",
    link: "/#platform",
  },
];

/**
 * Product Cross-Sell Section (Scene 10).
 *
 * Features:
 * - Dark background
 * - Grid of capability cards
 * - Orange glow icon tiles
 * - Staggered fade-in with blur
 * - Arrow nudges right on hover
 */
export function ProductCrossSellSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const gridRef = useGridReveal<HTMLDivElement>();

  return (
    <section
      id="explore"
      ref={sectionRef}
      className="relative scroll-mt-24 bg-ink px-5 py-24 lg:px-8 lg:py-32"
    >
      <div className="relative mx-auto w-full max-w-7xl">
        {/* Heading */}
        <div className="text-center">
          <WordReveal mode="scroll" triggerRef={sectionRef} className="text-display-sm text-balance">
            Explore the EPI Platform.
          </WordReveal>
        </div>

        {/* Grid */}
        <div
          ref={gridRef}
          className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-3"
        >
          {PLATFORM_CARDS.map((card) => (
            <PlatformCard key={card.id} card={card} />
          ))}
        </div>
      </div>
    </section>
  );
}

/**
 * Individual platform card.
 */
function PlatformCard({ card }: { card: (typeof PLATFORM_CARDS)[0] }) {
  return (
    <Link
      to={card.link}
      className="glass sheen card-interactive group flex flex-col rounded-2xl p-6 transition-all duration-300"
    >
      {/* Icon tile with orange glow */}
      <div className="relative mb-5 flex h-12 w-12 items-center justify-center rounded-xl border border-white/12 bg-gradient-to-br from-orange-500/20 to-orange-600/10 transition-all duration-300 group-hover:scale-105 group-hover:shadow-[0_0_24px_rgba(251,146,60,0.4)]">
        <card.icon className="h-6 w-6 text-orange-400" />
      </div>

      {/* Content */}
      <h3 className="text-lg font-semibold tracking-tight">{card.title}</h3>
      <p className="mt-2 flex-1 text-[13px] leading-relaxed text-muted-foreground">{card.description}</p>

      {/* Learn more link */}
      <div className="mt-5 flex items-center gap-2 text-[13px] font-medium text-white/80 transition-colors duration-300 group-hover:text-white">
        <span>Learn more</span>
        <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
      </div>
    </Link>
  );
}
