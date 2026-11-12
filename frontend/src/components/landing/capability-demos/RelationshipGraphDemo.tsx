import { useEffect, useState } from "react";
import { GitBranch } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Animated relationship graph showing procurement entity connections.
 * Interactive hover states reveal connections dynamically.
 */
export function RelationshipGraphDemo({ active = false }: { active?: boolean }) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string>("contract");

  useEffect(() => {
    if (!active) {
      setSelectedNode("contract");
      setHoveredNode(null);
      return;
    }

    const nodes = ["contract", "supplier", "buyer", "award"];
    let current = 0;

    const timer = setInterval(() => {
      current = (current + 1) % nodes.length;
      setSelectedNode(nodes[current]);
    }, 2400);

    return () => clearInterval(timer);
  }, [active]);

  const nodes = [
    { id: "buyer", label: "Buyer", x: "18%", y: "28%", connections: ["contract", "award"] },
    { id: "supplier", label: "Supplier", x: "78%", y: "24%", connections: ["contract", "award", "products"] },
    { id: "contract", label: "Contract", x: "24%", y: "72%", connections: ["buyer", "supplier", "award", "amendments"] },
    { id: "award", label: "Award", x: "74%", y: "68%", connections: ["buyer", "supplier", "contract"] },
    { id: "amendments", label: "Amendments", x: "48%", y: "86%", connections: ["contract"] },
    { id: "products", label: "Products", x: "88%", y: "48%", connections: ["supplier"] },
  ];

  const edges = [
    { from: "buyer", to: "contract" },
    { from: "buyer", to: "award" },
    { from: "supplier", to: "contract" },
    { from: "supplier", to: "award" },
    { from: "supplier", to: "products" },
    { from: "contract", to: "award" },
    { from: "contract", to: "amendments" },
  ];

  const isNodeActive = (nodeId: string) => {
    if (hoveredNode) return nodeId === hoveredNode;
    return nodeId === selectedNode;
  };

  const isEdgeActive = (from: string, to: string) => {
    const activeNode = hoveredNode || selectedNode;
    return from === activeNode || to === activeNode;
  };

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-white/12 bg-white/[0.04] p-3">
        <div className="flex items-center gap-2">
          <GitBranch className="h-3.5 w-3.5 text-white/50" aria-hidden="true" />
          <span className="text-[10px] uppercase tracking-[0.12em] text-subtle">procurement network</span>
        </div>
      </div>

      <div className="relative h-[200px] rounded-lg border border-white/10 bg-white/[0.02] p-4">
        {/* SVG for edges */}
        <svg className="absolute inset-0 h-full w-full" aria-hidden="true">
          {edges.map((edge) => {
            const fromNode = nodes.find((n) => n.id === edge.from);
            const toNode = nodes.find((n) => n.id === edge.to);
            if (!fromNode || !toNode) return null;

            const isActive = isEdgeActive(edge.from, edge.to);

            return (
              <line
                key={`${edge.from}-${edge.to}`}
                x1={fromNode.x}
                y1={fromNode.y}
                x2={toNode.x}
                y2={toNode.y}
                stroke={isActive ? "rgba(255, 255, 255, 0.35)" : "rgba(255, 255, 255, 0.12)"}
                strokeWidth={isActive ? "1.5" : "1"}
                className="transition-all duration-300"
              />
            );
          })}
        </svg>

        {/* Nodes */}
        {nodes.map((node) => {
          const isActive = isNodeActive(node.id);
          const isCenter = node.id === "contract" || node.id === "award";

          return (
            <button
              key={node.id}
              type="button"
              className={cn(
                "absolute -translate-x-1/2 -translate-y-1/2 rounded-full border px-2.5 py-1 text-[9px] uppercase tracking-[0.1em] transition-all duration-300",
                isActive
                  ? "z-10 border-white/30 bg-white/[0.12] text-white shadow-[0_0_24px_-4px_rgba(255,255,255,0.4)]"
                  : "border-white/15 bg-ink-3 text-muted-foreground hover:border-white/25 hover:bg-white/[0.06]",
                isCenter && "font-medium",
              )}
              style={{ left: node.x, top: node.y }}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              onClick={() => setSelectedNode(node.id)}
            >
              {node.label}
            </button>
          );
        })}
      </div>

      <p className="flex items-center gap-1.5 text-[9px] uppercase tracking-[0.12em] text-subtle">
        <span className="h-1 w-1 rounded-full bg-white/40" aria-hidden="true" />
        demonstration: hover or wait to explore
      </p>
    </div>
  );
}
