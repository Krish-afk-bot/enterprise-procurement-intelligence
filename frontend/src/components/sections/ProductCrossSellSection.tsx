import { Link } from "react-router-dom";
import { LANDING_CONTENT } from "@/content/landing";
import { WordReveal } from "@/components/animations/WordReveal";
import {
  Search,
  FileText,
  Building2,
  Scroll,
  Network,
  BarChart3,
  ArrowRight,
  Layers,
} from "lucide-react";

const ICON_MAP: Record<string, React.ReactNode> = {
  Search: <Search className="w-5 h-5 text-[#FF4D00]" />,
  FileText: <FileText className="w-5 h-5 text-[#FF4D00]" />,
  Building2: <Building2 className="w-5 h-5 text-[#FF4D00]" />,
  Scroll: <Scroll className="w-5 h-5 text-[#FF4D00]" />,
  Network: <Network className="w-5 h-5 text-[#FF4D00]" />,
  BarChart3: <BarChart3 className="w-5 h-5 text-[#FF4D00]" />,
};

const MODULE_ACTION_LABELS: Record<string, string> = {
  "cs-1": "Open Procurement Search",
  "cs-2": "Open Documents",
  "cs-3": "Open Suppliers",
  "cs-4": "Open Contracts",
  "cs-5": "Open Graph",
  "cs-6": "Open Evaluation",
};

export function ProductCrossSellSection() {
  return (
    <section id="cross-sell" className="relative py-28 px-6 bg-[#0B0B0C] text-white scroll-mt-[112px]">
      <div className="max-w-7xl mx-auto">
        {/* Header: Vertical Stack, Badge Above (F6.2) */}
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-16 gap-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider uppercase bg-white/5 border border-white/10 text-white/80">
            <Layers className="w-3.5 h-3.5 text-[#FF4D00]" />
            <span>{LANDING_CONTENT.crossSell.badge}</span>
          </div>

          <WordReveal
            as="h2"
            mode="scroll"
            className="text-3xl sm:text-5xl font-bold tracking-tight text-white leading-tight w-full"
          >
            {LANDING_CONTENT.crossSell.heading}
          </WordReveal>
        </div>

        {/* 6 Grid Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {LANDING_CONTENT.crossSell.cards.map((card) => (
            <Link
              key={card.id}
              to={card.href}
              className="group p-6 rounded-3xl bg-white/[0.03] border border-white/10 hover:border-[#FF4D00]/50 hover:bg-white/[0.06] transition-all duration-300 flex flex-col justify-between shadow-lg hover:-translate-y-1"
            >
              <div>
                <div className="w-10 h-10 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                  {ICON_MAP[card.icon] ?? <Search className="w-5 h-5 text-[#FF4D00]" />}
                </div>

                <h3 className="text-lg font-bold text-white mb-2 tracking-tight group-hover:text-[#FF7A1A] transition-colors">
                  {card.title}
                </h3>
                <p className="text-xs sm:text-sm text-white/60 leading-relaxed mb-6">
                  {card.description}
                </p>
              </div>

              <div className="flex items-center gap-1.5 text-xs font-semibold text-white/80 group-hover:text-white pt-4 border-t border-white/5">
                <span>{MODULE_ACTION_LABELS[card.id] || "Open workspace"}</span>
                <ArrowRight className="w-3.5 h-3.5 text-[#FF4D00] transform group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
