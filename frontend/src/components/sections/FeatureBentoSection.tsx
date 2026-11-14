import { useRef } from "react";
import { LANDING_CONTENT, BentoTile } from "@/content/landing";
import { CurtainTransition } from "@/components/animations/CurtainTransition";
import { WordReveal } from "@/components/animations/WordReveal";
import { cn } from "@/lib/utils";
import {
  Bot,
  ShieldCheck,
  Network,
  Split,
  Cpu,
  FileCheck2,
  ArrowRight,
  Layers,
} from "lucide-react";

interface BentoCardProps {
  tile: BentoTile;
  className?: string;
}

function BentoCard({ tile, className }: BentoCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current;
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const rotateX = ((y - centerY) / centerY) * -5;
    const rotateY = ((x - centerX) / centerX) * 5;

    card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.01, 1.01, 1.01)`;
    card.style.setProperty("--mouse-x", `${x}px`);
    card.style.setProperty("--mouse-y", `${y}px`);
  };

  const handleMouseLeave = () => {
    const card = cardRef.current;
    if (!card) return;
    card.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)";
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={cn(
        "group relative rounded-3xl bg-[#0B0B0C] border border-white/10 p-6 sm:p-8 overflow-hidden transition-transform duration-200 ease-out flex flex-col justify-between shadow-xl",
        className
      )}
    >
      {/* Radial cursor highlight */}
      <div
        className="pointer-events-none absolute -inset-px opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-3xl"
        style={{
          background: `radial-gradient(400px circle at var(--mouse-x, 150px) var(--mouse-y, 150px), rgba(255, 77, 0, 0.12), transparent 70%)`,
        }}
      />

      {/* Top Header */}
      <div className="relative z-10 flex items-center justify-between mb-4">
        <span className="text-[11px] font-mono tracking-widest text-[#FF4D00] uppercase font-semibold">
          {tile.category}
        </span>
        <span className="w-2 h-2 rounded-full bg-white/20 group-hover:bg-[#FF4D00] transition-colors" />
      </div>

      {/* Visualizers */}
      <div className="relative z-10 my-3 flex items-center justify-center py-2">
        {tile.type === "hybrid-retrieval" && (
          <div className="w-full flex items-center justify-around gap-2 text-xs font-mono text-white/70 py-4 px-4 rounded-2xl bg-white/[0.02] border border-white/10">
            <div className="flex flex-col items-center">
              <span className="text-[#FF7A1A] font-bold">Dense Vector</span>
              <span className="text-[10px] text-white/40">Cosine Sim</span>
            </div>
            <ArrowRight className="w-4 h-4 text-white/30" />
            <div className="flex flex-col items-center p-2 rounded-lg bg-[#FF4D00]/10 border border-[#FF4D00]/30">
              <span className="text-[#FF4D00] font-bold">RRF Fusion</span>
              <span className="text-[10px] text-white/60">Rank Reciprocal</span>
            </div>
            <ArrowRight className="w-4 h-4 text-white/30" />
            <div className="flex flex-col items-center">
              <span className="text-white font-bold">Cross-Encoder</span>
              <span className="text-[10px] text-white/40">Re-ranking</span>
            </div>
          </div>
        )}

        {tile.type === "multi-agent" && (
          <div className="flex items-center gap-4 py-2">
            <div className="w-12 h-12 rounded-xl bg-[#FF4D00]/15 border border-[#FF4D00]/40 flex items-center justify-center text-[#FF4D00]">
              <Bot className="w-6 h-6" />
            </div>
            <div className="flex flex-col gap-1 text-[11px] font-mono text-white/60">
              <span className="text-white font-semibold">Planner Agent</span>
              <span className="text-[#FF7A1A]">Evaluator & Synthesizer</span>
            </div>
          </div>
        )}

        {tile.type === "evidence-verification" && (
          <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-white/5 border border-white/10">
            <ShieldCheck className="w-5 h-5 text-[#FF4D00]" />
            <span className="text-xs font-mono text-white/80">Page 14 • Confidence shown as example</span>
          </div>
        )}

        {tile.type === "knowledge-graph" && (
          <div className="flex items-center gap-3">
            <Network className="w-8 h-8 text-[#FF4D00]" />
            <span className="text-xs font-mono text-white/70">Buyer ➔ Award ➔ Supplier</span>
          </div>
        )}

        {tile.type === "model-routing" && (
          <div className="flex items-center gap-3">
            <Split className="w-6 h-6 text-[#FF7A1A]" />
            <span className="text-xs font-mono text-white/70">Deterministic SQL + LLM</span>
          </div>
        )}

        {tile.type === "mcp-integration" && (
          <div className="flex items-center gap-3">
            <Cpu className="w-6 h-6 text-[#FF4D00]" />
            <span className="text-xs font-mono text-white/70">Model Context Protocol</span>
          </div>
        )}

        {tile.type === "document-intelligence" && (
          <div className="w-full flex items-center justify-between gap-3 text-xs font-mono text-white/70 py-3 px-4 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center gap-2">
              <FileCheck2 className="w-5 h-5 text-[#FF7A1A]" />
              <span>Multi-page PDF</span>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-white/30" />
            <span>Table Extraction</span>
            <ArrowRight className="w-3.5 h-3.5 text-white/30" />
            <span className="text-[#FF4D00]">Semantic Chunks</span>
          </div>
        )}
      </div>

      {/* Title & Description */}
      <div className="relative z-10 mt-auto">
        <h4 className="text-lg font-bold tracking-tight text-white mb-1.5">
          {tile.title}
        </h4>
        <p className="text-xs text-white/60 leading-relaxed font-normal">
          {tile.description}
        </p>
      </div>
    </div>
  );
}

export function FeatureBentoSection() {
  const tiles = LANDING_CONTENT.bento.tiles;

  return (
    <CurtainTransition from="light" to="dark" id="bento">
      <div className="relative pt-24 sm:pt-28 pb-12 sm:pb-16 px-6 max-w-7xl mx-auto scroll-mt-[112px]">
        {/* Section Heading: Centered Stack */}
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-16 gap-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider uppercase bg-white/5 border border-white/10 text-white/80">
            <Layers className="w-3.5 h-3.5 text-[#FF4D00]" />
            <span>{LANDING_CONTENT.bento.badge}</span>
          </div>

          <WordReveal
            as="h2"
            mode="scroll"
            className="text-3xl sm:text-5xl font-bold tracking-tight text-white leading-tight w-full"
          >
            {LANDING_CONTENT.bento.heading}
          </WordReveal>
        </div>

        {/* Rebalanced Bento Grid (F6.4): Row 1 (8+4), Row 2 (4+4+4), Row 3 (Full width 12) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Row 1: Hybrid Retrieval (8) + Multi-Agent (4) */}
          <BentoCard tile={tiles[0]} className="lg:col-span-8 min-h-[300px]" />
          <BentoCard tile={tiles[1]} className="lg:col-span-4 min-h-[300px]" />

          {/* Row 2: Evidence Verification (4) + Knowledge Graph (4) + Model Routing (4) */}
          <BentoCard tile={tiles[2]} className="lg:col-span-4 min-h-[260px]" />
          <BentoCard tile={tiles[3]} className="lg:col-span-4 min-h-[260px]" />
          <BentoCard tile={tiles[4]} className="lg:col-span-4 min-h-[260px]" />

          {/* Row 3: MCP (4) + Full Width Document AI (8) */}
          <BentoCard tile={tiles[5]} className="lg:col-span-4 min-h-[260px]" />
          <BentoCard tile={tiles[6]} className="lg:col-span-8 min-h-[260px]" />
        </div>
      </div>
    </CurtainTransition>
  );
}
