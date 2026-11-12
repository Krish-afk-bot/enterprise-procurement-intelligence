import { useRef, useState, useEffect } from "react";
import { WordReveal } from "@/components/animations/WordReveal";
import { CurtainTransition } from "@/components/animations/CurtainTransition";
import { useGridReveal } from "@/components/animations/useScrollReveal";
import { ChartNoAxesColumn, GitBranch, Search, ShieldCheck, FileText, Layers, Link2 } from "lucide-react";

// Real EPI capabilities for bento tiles
const BENTO_TILES = [
  {
    id: "hybrid-retrieval",
    title: "Hybrid Retrieval",
    description: "Dense embeddings, BM25 sparse retrieval, RRF fusion, and cross-encoder reranking for precision.",
    icon: Search,
    size: "large", // Takes 2 columns
    visual: "retrieval",
  },
  {
    id: "multi-agent",
    title: "Multi-Agent Intelligence",
    description: "Query planning, retrieval orchestration, evidence evaluation, answer generation, and verification.",
    icon: GitBranch,
    size: "medium",
    visual: "agents",
  },
  {
    id: "evidence-verification",
    title: "Evidence Verification",
    description: "Claim-to-passage binding with citation validation. Every statement traces to source evidence.",
    icon: ShieldCheck,
    size: "medium",
    visual: "verification",
  },
  {
    id: "knowledge-graph",
    title: "Knowledge Graph",
    description: "Suppliers, contracts, amendments, and awards modeled as a traversable relationship network.",
    icon: Layers,
    size: "medium",
    visual: "graph",
  },
  {
    id: "document-intelligence",
    title: "Document Intelligence",
    description: "OCR, layout analysis, semantic chunking, vision escalation for complex tables and diagrams.",
    icon: FileText,
    size: "medium",
    visual: "document",
  },
  {
    id: "mcp-integration",
    title: "MCP Integration",
    description: "External AI assistants can invoke EPI tools through the Model Context Protocol interface.",
    icon: Link2,
    size: "medium",
    visual: "mcp",
  },
];

/**
 * Feature Bento Section (Scene 03).
 *
 * Features:
 * - Dark curtain transition
 * - Asymmetric bento grid (1 large + 5 medium tiles)
 * - Mouse tilt interaction (desktop)
 * - Cursor-following radial highlight
 * - Staggered blur-to-sharp entrance
 * - Actual EPI technical capabilities
 */
export function FeatureBentoSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const gridRef = useGridReveal<HTMLDivElement>();

  return (
    <section
      id="capabilities"
      ref={sectionRef}
      className="relative scroll-mt-24 overflow-hidden bg-ink px-5 py-24 lg:px-8 lg:py-32"
    >
      {/* Curtain transition */}
      <CurtainTransition theme="dark" triggerRef={sectionRef} />

      <div className="relative mx-auto w-full max-w-7xl">
        {/* Badge and heading */}
        <div className="text-center">
          <div className="animate-rise">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground backdrop-blur">
              <ChartNoAxesColumn className="h-3 w-3" />
              Platform capabilities
            </span>
          </div>
          <WordReveal
            mode="scroll"
            triggerRef={sectionRef}
            className="mx-auto mt-6 max-w-4xl text-display-sm text-balance"
          >
            Built to Connect Every Piece of Procurement Evidence.
          </WordReveal>
        </div>

        {/* Bento grid */}
        <div
          ref={gridRef}
          className="mt-16 grid auto-rows-fr gap-4 md:grid-cols-2 lg:grid-cols-3"
        >
          {BENTO_TILES.map((tile, index) => (
            <BentoTile key={tile.id} tile={tile} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}

/**
 * Individual bento tile with tilt interaction.
 */
function BentoTile({ tile }: { tile: (typeof BENTO_TILES)[0]; index: number }) {
  const tileRef = useRef<HTMLDivElement>(null);
  const [cursorPos, setCursorPos] = useState({ x: 0.5, y: 0.5 });

  // Mouse tilt effect (desktop only)
  useEffect(() => {
    const element = tileRef.current;
    if (!element) return;

    const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fine || reduce) return;

    const onMove = (event: MouseEvent) => {
      const rect = element.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width;
      const y = (event.clientY - rect.top) / rect.height;
      setCursorPos({ x, y });

      const rotateX = (y - 0.5) * -6;
      const rotateY = (x - 0.5) * 6;

      element.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
    };

    const onLeave = () => {
      element.style.transform = "";
      setCursorPos({ x: 0.5, y: 0.5 });
    };

    element.addEventListener("mousemove", onMove);
    element.addEventListener("mouseleave", onLeave);

    return () => {
      element.removeEventListener("mousemove", onMove);
      element.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  const gridClass = tile.size === "large" ? "md:col-span-2" : "";

  return (
    <div
      ref={tileRef}
      className={`glass sheen card-interactive group relative overflow-hidden rounded-3xl p-8 transition-transform duration-300 ${gridClass}`}
      style={{
        transformStyle: "preserve-3d",
      }}
    >
      {/* Cursor-following radial highlight */}
      <div
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: `radial-gradient(600px circle at ${cursorPos.x * 100}% ${cursorPos.y * 100}%, rgba(251, 146, 60, 0.1), transparent 40%)`,
        }}
        aria-hidden="true"
      />

      {/* Icon */}
      <div className="relative z-10 flex h-12 w-12 items-center justify-center rounded-xl border border-white/12 bg-white/[0.05] transition-transform duration-300 group-hover:-translate-y-1">
        <tile.icon className="h-6 w-6 text-white" />
      </div>

      {/* Content */}
      <div className="relative z-10 mt-6">
        <h3 className="text-xl font-semibold tracking-tight">{tile.title}</h3>
        <p className="mt-3 text-[14px] leading-relaxed text-muted-foreground">{tile.description}</p>
      </div>

      {/* Visual illustration */}
      <div className="relative z-10 mt-8">
        <TileVisual type={tile.visual} />
      </div>
    </div>
  );
}

/**
 * Visual illustrations for each capability.
 */
function TileVisual({ type }: { type: string }) {
  switch (type) {
    case "retrieval":
      return <RetrievalVisual />;
    case "agents":
      return <AgentsVisual />;
    case "verification":
      return <VerificationVisual />;
    case "graph":
      return <GraphVisual />;
    case "document":
      return <DocumentVisual />;
    case "mcp":
      return <MCPVisual />;
    default:
      return null;
  }
}

function RetrievalVisual() {
  return (
    <div className="flex gap-2">
      {/* Dense, Sparse, Fusion stages */}
      {["Dense", "Sparse", "Fusion"].map((stage, i) => (
        <div
          key={stage}
          className="flex-1 rounded-lg border border-white/10 bg-white/[0.03] p-3 text-center transition-all duration-300 hover:border-orange-500/30 hover:bg-orange-500/10"
          style={{ animationDelay: `${i * 100}ms` }}
        >
          <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{stage}</div>
          <div className="mt-1 h-1 w-full rounded-full bg-orange-500/40" />
        </div>
      ))}
    </div>
  );
}

function AgentsVisual() {
  return (
    <div className="relative h-32">
      {/* Central node */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <div className="h-8 w-8 rounded-full border-2 border-orange-500/50 bg-orange-500/20" />
      </div>
      {/* Orbiting nodes */}
      {[0, 72, 144, 216, 288].map((angle, i) => {
        const x = Math.cos((angle * Math.PI) / 180) * 40;
        const y = Math.sin((angle * Math.PI) / 180) * 40;
        return (
          <div
            key={i}
            className="absolute left-1/2 top-1/2 h-4 w-4 rounded-full border border-white/20 bg-white/10"
            style={{
              transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`,
            }}
          />
        );
      })}
    </div>
  );
}

function VerificationVisual() {
  return (
    <div className="space-y-2">
      <div className="rounded-lg border-l-2 border-l-orange-500 bg-white/[0.03] p-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-orange-500" />
          <span className="text-[11px] text-muted-foreground">Claim verified</span>
        </div>
      </div>
      <div className="text-[10px] text-subtle">→ Source passage ID: chunk_42</div>
    </div>
  );
}

function GraphVisual() {
  return (
    <div className="relative h-28">
      <svg viewBox="0 0 200 100" className="h-full w-full">
        {/* Connections */}
        <line x1="40" y1="50" x2="100" y2="30" stroke="rgba(251, 146, 60, 0.3)" strokeWidth="1" />
        <line x1="40" y1="50" x2="100" y2="70" stroke="rgba(251, 146, 60, 0.3)" strokeWidth="1" />
        <line x1="100" y1="30" x2="160" y2="50" stroke="rgba(251, 146, 60, 0.3)" strokeWidth="1" />
        <line x1="100" y1="70" x2="160" y2="50" stroke="rgba(251, 146, 60, 0.3)" strokeWidth="1" />
        {/* Nodes */}
        <circle cx="40" cy="50" r="8" fill="rgba(251, 146, 60, 0.2)" stroke="rgba(251, 146, 60, 0.6)" strokeWidth="2" />
        <circle cx="100" cy="30" r="6" fill="rgba(255, 255, 255, 0.1)" stroke="rgba(255, 255, 255, 0.3)" strokeWidth="1" />
        <circle cx="100" cy="70" r="6" fill="rgba(255, 255, 255, 0.1)" stroke="rgba(255, 255, 255, 0.3)" strokeWidth="1" />
        <circle cx="160" cy="50" r="8" fill="rgba(251, 146, 60, 0.2)" stroke="rgba(251, 146, 60, 0.6)" strokeWidth="2" />
      </svg>
    </div>
  );
}

function DocumentVisual() {
  return (
    <div className="space-y-2">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex gap-2">
          <div className="h-2 w-2 rounded-full bg-orange-500/40" />
          <div className="flex-1 h-2 rounded-full bg-white/10" />
        </div>
      ))}
    </div>
  );
}

function MCPVisual() {
  return (
    <div className="flex items-center justify-between">
      <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2">
        <span className="text-[10px] font-mono text-muted-foreground">AI Assistant</span>
      </div>
      <div className="flex-1 border-t border-dashed border-white/20" />
      <div className="rounded-lg border border-orange-500/30 bg-orange-500/10 p-2">
        <span className="text-[10px] font-mono text-orange-400">EPI Tools</span>
      </div>
    </div>
  );
}
