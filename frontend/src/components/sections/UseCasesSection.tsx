import { useRef } from "react";
import { FileText, Users, DollarSign, ShieldCheck, GitCompare, Network } from "lucide-react";
import { WordReveal } from "@/components/animations/WordReveal";
import { useGridReveal } from "@/components/animations/useScrollReveal";

const USE_CASES = [
  {
    id: "contract-intelligence",
    icon: FileText,
    title: "Contract Intelligence",
    description: "Search clauses, payment terms, and obligations across all supplier agreements.",
    capabilities: ["Clause detection", "Term extraction", "Amendment tracking"],
  },
  {
    id: "supplier-intelligence",
    icon: Users,
    title: "Supplier Intelligence",
    description: "Connect entities, discover relationships, and trace supplier history.",
    capabilities: ["Entity resolution", "Relationship mapping", "Historical analysis"],
  },
  {
    id: "pricing-analysis",
    icon: DollarSign,
    title: "Pricing Analysis",
    description: "Compare unit prices, identify trends, and validate procurement decisions.",
    capabilities: ["Price comparison", "Trend analysis", "Cost validation"],
  },
  {
    id: "compliance-monitoring",
    icon: ShieldCheck,
    title: "Compliance Monitoring",
    description: "Verify certifications, track requirements, and maintain audit trails.",
    capabilities: ["Certificate verification", "Requirement tracking", "Audit logging"],
  },
  {
    id: "amendment-tracking",
    icon: GitCompare,
    title: "Amendment Tracking",
    description: "Trace contract versions, compare changes, and understand evolution over time.",
    capabilities: ["Version history", "Change detection", "Timeline view"],
  },
  {
    id: "relationship-discovery",
    icon: Network,
    title: "Relationship Discovery",
    description: "Navigate the procurement network from any contract, supplier, or award.",
    capabilities: ["Graph traversal", "Connection mapping", "Network analysis"],
  },
];

/**
 * Use Cases Section (Scene 06).
 *
 * Features:
 * - 3x2 grid of use case cards
 * - Progressive left-to-right reveal
 * - CSS/SVG illustrations
 * - Hover lift interactions
 */
export function UseCasesSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const gridRef = useGridReveal<HTMLDivElement>();

  return (
    <section
      id="use-cases"
      ref={sectionRef}
      className="relative scroll-mt-24 bg-[#FAFAF9] px-5 py-24 lg:px-8 lg:py-32"
    >
      {/* Subtle top gradient */}
      <div
        className="pointer-events-none absolute left-1/2 top-0 h-[300px] w-[600px] -translate-x-1/2"
        style={{
          background: "radial-gradient(ellipse at top, rgba(251, 146, 60, 0.06), transparent 70%)",
        }}
        aria-hidden="true"
      />

      <div className="relative mx-auto w-full max-w-7xl">
        {/* Heading */}
        <div className="text-center">
          <WordReveal mode="scroll" triggerRef={sectionRef} className="text-display-sm text-balance text-zinc-900">
            Intelligence Across the Procurement Lifecycle.
          </WordReveal>
          <p className="mx-auto mt-5 max-w-2xl text-[15px] leading-relaxed text-zinc-600">
            From contract analysis to supplier relationships, EPI connects procurement intelligence at every stage.
          </p>
        </div>

        {/* Grid */}
        <div
          ref={gridRef}
          className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-3"
        >
          {USE_CASES.map((useCase) => (
            <UseCaseCard key={useCase.id} useCase={useCase} />
          ))}
        </div>
      </div>
    </section>
  );
}

/**
 * Individual use case card.
 */
function UseCaseCard({ useCase }: { useCase: (typeof USE_CASES)[0] }) {
  return (
    <article className="group flex flex-col rounded-2xl border border-zinc-200 bg-white p-7 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-zinc-300 hover:shadow-lg">
      {/* Illustration area */}
      <div className="relative mb-6 flex h-32 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-zinc-50 to-zinc-100">
        <UseCaseIllustration type={useCase.id} Icon={useCase.icon} />
      </div>

      {/* Content */}
      <div className="flex-1">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-zinc-200 bg-white transition-colors duration-300 group-hover:border-orange-500/30 group-hover:bg-orange-50">
            <useCase.icon className="h-5 w-5 text-zinc-700 transition-colors duration-300 group-hover:text-orange-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold tracking-tight text-zinc-900">{useCase.title}</h3>
          </div>
        </div>
        <p className="mt-3 text-[13px] leading-relaxed text-zinc-600">{useCase.description}</p>
      </div>

      {/* Capabilities */}
      <ul className="mt-6 space-y-2 border-t border-zinc-200 pt-5">
        {useCase.capabilities.map((capability) => (
          <li key={capability} className="flex items-center gap-2.5 text-[12.5px] text-zinc-600">
            <span className="h-px w-3 bg-orange-500/60" aria-hidden="true" />
            {capability}
          </li>
        ))}
      </ul>
    </article>
  );
}

/**
 * Illustrations for each use case.
 */
function UseCaseIllustration({ type, Icon }: { type: string; Icon: React.ElementType }) {
  switch (type) {
    case "contract-intelligence":
      return (
        <div className="relative">
          {/* Document pages */}
          <div className="flex gap-2">
            <div className="h-20 w-16 rounded-lg border-2 border-zinc-300 bg-white shadow-sm">
              <div className="p-2 space-y-1">
                <div className="h-1 rounded-full bg-orange-500/40" />
                <div className="h-1 w-3/4 rounded-full bg-zinc-200" />
                <div className="h-1 w-2/3 rounded-full bg-zinc-200" />
              </div>
            </div>
            <div className="h-20 w-16 rounded-lg border-2 border-zinc-200 bg-white/60" />
          </div>
        </div>
      );

    case "supplier-intelligence":
      return (
        <svg viewBox="0 0 120 80" className="h-full w-full">
          {/* Entity nodes */}
          <line x1="30" y1="40" x2="60" y2="25" stroke="#FB923C" strokeWidth="1.5" opacity="0.4" />
          <line x1="30" y1="40" x2="60" y2="55" stroke="#FB923C" strokeWidth="1.5" opacity="0.4" />
          <line x1="60" y1="25" x2="90" y2="40" stroke="#FB923C" strokeWidth="1.5" opacity="0.4" />
          <line x1="60" y1="55" x2="90" y2="40" stroke="#FB923C" strokeWidth="1.5" opacity="0.4" />

          <circle cx="30" cy="40" r="10" fill="#FB923C" fillOpacity="0.2" stroke="#FB923C" strokeWidth="2" />
          <circle cx="60" cy="25" r="8" fill="white" stroke="#d4d4d8" strokeWidth="2" />
          <circle cx="60" cy="55" r="8" fill="white" stroke="#d4d4d8" strokeWidth="2" />
          <circle cx="90" cy="40" r="10" fill="#FB923C" fillOpacity="0.2" stroke="#FB923C" strokeWidth="2" />
        </svg>
      );

    case "pricing-analysis":
      return (
        <div className="relative h-full w-full">
          {/* Price chart */}
          <svg viewBox="0 0 120 60" className="h-full w-full">
            <polyline
              points="10,50 30,35 50,40 70,25 90,30 110,20"
              fill="none"
              stroke="#FB923C"
              strokeWidth="2"
              opacity="0.6"
            />
            {[10, 30, 50, 70, 90, 110].map((x, i) => (
              <circle key={i} cx={x} cy={[50, 35, 40, 25, 30, 20][i]} r="3" fill="#FB923C" />
            ))}
          </svg>
        </div>
      );

    case "compliance-monitoring":
      return (
        <div className="flex items-center gap-3">
          {/* Certificate */}
          <div className="h-20 w-16 rounded-lg border-2 border-zinc-300 bg-white p-2 shadow-sm">
            <div className="flex h-full flex-col items-center justify-center">
              <Icon className="h-6 w-6 text-orange-500" />
              <div className="mt-1 h-px w-8 bg-zinc-300" />
            </div>
          </div>
          {/* Checkmark */}
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
            <ShieldCheck className="h-6 w-6 text-green-600" />
          </div>
        </div>
      );

    case "amendment-tracking":
      return (
        <div className="relative h-full">
          {/* Version timeline */}
          <div className="flex items-center gap-2">
            {[1, 2, 3].map((v, i) => (
              <div
                key={v}
                className={`flex h-16 w-12 flex-col items-center justify-center rounded-lg border-2 ${
                  i === 2 ? "border-orange-500 bg-orange-50" : "border-zinc-200 bg-white"
                }`}
              >
                <div className="text-[10px] font-medium text-zinc-500">v{v}</div>
                {i < 2 && <div className="absolute top-8 h-px w-2 bg-zinc-300" style={{ left: `${(i + 1) * 52}px` }} />}
              </div>
            ))}
          </div>
        </div>
      );

    case "relationship-discovery":
      return (
        <svg viewBox="0 0 100 80" className="h-full w-full">
          {/* Small procurement graph */}
          <circle cx="50" cy="40" r="12" fill="#FB923C" fillOpacity="0.2" stroke="#FB923C" strokeWidth="2" />
          {[0, 90, 180, 270].map((angle, i) => {
            const x = 50 + Math.cos((angle * Math.PI) / 180) * 30;
            const y = 40 + Math.sin((angle * Math.PI) / 180) * 30;
            return (
              <g key={i}>
                <line x1="50" y1="40" x2={x} y2={y} stroke="#FB923C" strokeWidth="1" opacity="0.3" />
                <circle cx={x} cy={y} r="6" fill="white" stroke="#d4d4d8" strokeWidth="1.5" />
              </g>
            );
          })}
        </svg>
      );

    default:
      return <Icon className="h-12 w-12 text-zinc-400" />;
  }
}
