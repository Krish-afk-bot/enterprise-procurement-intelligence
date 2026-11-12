import { ArrowRight, BadgeCheck, FileStack, GitBranch, Layers, ListFilter, Quote, Table2 } from "lucide-react";

import { Reveal } from "@/components/motion/Reveal";

/**
 * Platform architecture, described in business terms.
 *
 * Each stage names a capability the deployment actually has, in the order a
 * question travels through it. Endpoint names, model choices and index
 * internals are deliberately omitted: a buyer needs to know what happens to a
 * document and why an answer can be trusted, not which library performs it.
 */
const LAYERS = [
  {
    icon: Table2,
    title: "Procurement records",
    body: "Buyers, suppliers, contracts, amendments, awards and price rows are held as structured records, each traceable to the document it was read from.",
    tag: "structured",
  },
  {
    icon: FileStack,
    title: "Document ingestion",
    body: "Uploaded files become pages, extracted text, tables and passages. The ingestion report states the stage reached and whether OCR or a vision model was involved.",
    tag: "unstructured",
  },
  {
    icon: Layers,
    title: "Hybrid retrieval",
    body: "A question is matched against both structured rows and document passages, so a price can come from a table and its conditions from the clause around it.",
    tag: "retrieval",
  },
  {
    icon: ListFilter,
    title: "Reranking",
    body: "Candidates are ordered against the question before anything is generated. Weak matches are dropped rather than passed forward as context.",
    tag: "ranking",
  },
  {
    icon: GitBranch,
    title: "Relationship resolution",
    body: "Supplier, contract, amendment and award references are resolved to one another, which is what lets an answer cross records without losing the thread.",
    tag: "graph",
  },
  {
    icon: Quote,
    title: "Answer and citation check",
    body: "The answer is composed from the selected passages, then checked against them. The outcome is shown as supported, partial or refused — with the page and clause.",
    tag: "verification",
  },
];

export function ArchitectureSection() {
  return (
    <section
      id="architecture"
      className="relative scroll-mt-24 overflow-hidden border-t border-white/[0.07] bg-ink px-5 py-24 lg:px-8 lg:py-32"
    >
      <div className="pointer-events-none absolute inset-0 grid-lines opacity-30" aria-hidden="true" />
      <div
        className="pointer-events-none absolute left-1/2 top-1/3 h-[420px] w-[760px] -translate-x-1/2 halo opacity-40"
        aria-hidden="true"
      />

      <div className="relative mx-auto w-full max-w-7xl">
        <Reveal className="max-w-2xl">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-subtle">Platform architecture</p>
          <h2 className="mt-4 text-display-sm text-balance">From record to cited answer.</h2>
          <p className="mt-4 text-[14px] leading-relaxed text-muted-foreground">
            Six stages sit between a stored document and an answer you can defend in a review. Each one is visible in
            the workspace: what was ingested, what was retrieved, what was ranked and what survived verification.
          </p>
        </Reveal>

        <ol className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/[0.06] md:grid-cols-2 lg:grid-cols-3">
          {LAYERS.map((layer, index) => (
            <Reveal as="li" key={layer.title} delay={index * 70}>
              <article className="group relative flex h-full flex-col bg-ink px-6 py-7 transition-colors duration-300 hover:bg-white/[0.025]">
                <span
                  className="absolute inset-x-0 top-0 h-px origin-left scale-x-0 bg-white/45 transition-transform duration-500 group-hover:scale-x-100"
                  aria-hidden="true"
                />
                <div className="flex items-center justify-between">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/12 bg-white/[0.04]">
                    <layer.icon className="h-4 w-4 text-white/70" aria-hidden="true" />
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-subtle">
                    {String(index + 1).padStart(2, "0")} · {layer.tag}
                  </span>
                </div>
                <h3 className="mt-5 text-[15px] font-medium tracking-tight">{layer.title}</h3>
                <p className="mt-2 text-[12.5px] leading-relaxed text-muted-foreground">{layer.body}</p>
                {index < LAYERS.length - 1 ? (
                  <ArrowRight
                    className="mt-5 h-3.5 w-3.5 text-white/20 transition-colors group-hover:text-white/40"
                    aria-hidden="true"
                  />
                ) : (
                  <BadgeCheck className="mt-5 h-3.5 w-3.5 text-white/40" aria-hidden="true" />
                )}
              </article>
            </Reveal>
          ))}
        </ol>

        <Reveal delay={120}>
          <p className="mt-6 max-w-3xl text-[12px] leading-relaxed text-subtle">
            The deployment runs on the operator&apos;s own infrastructure. No document text leaves it unless the
            operator configures an external model endpoint, in which case only the retrieved passages needed to answer
            are sent.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
