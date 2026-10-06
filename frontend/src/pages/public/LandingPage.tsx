import { Link } from "react-router-dom";

import { LazyHeroScene } from "@/components/three/LazyHeroScene";
import {
  BadgeCheck,
  Banknote,
  FileSearch,
  GitBranch,
  Layers,
  ScanText,
  ShieldQuestion,
  TriangleAlert,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const FLOW_QUESTION = "What is the current unit price for the Industrial Laptop X200?";

const CAPABILITIES = [
  {
    icon: FileSearch,
    title: "Every answer carries its page",
    body: "Answers cite the document, page, section or clause they were built from. Open the citation and the viewer lands on that page.",
  },
  {
    icon: Layers,
    title: "Hybrid retrieval, not one index",
    body: "Semantic search, exact term matching and a cross-encoder rerank run over the same corpus, and the workspace shows which retriever surfaced each passage.",
  },
  {
    icon: TriangleAlert,
    title: "Version conflicts are stated",
    body: "When an amendment supersedes a price or a term, the answer says which record governs instead of silently averaging them.",
  },
  {
    icon: Banknote,
    title: "Structured pricing questions",
    body: "Questions about prices, effective dates and minimum quantities are answered from stored price rows, so the figures are the recorded ones.",
  },
  {
    icon: GitBranch,
    title: "Contracts as relationships",
    body: "Suppliers, contracts, amendments, products, prices and compliance certificates are indexed as a graph you can traverse from any record.",
  },
  {
    icon: ShieldQuestion,
    title: "Refusals instead of guesses",
    body: "If the corpus does not support a question, the system returns no verified evidence and explains what it could not find.",
  },
];

const STEPS = [
  {
    icon: ScanText,
    title: "Ingest",
    body: "PDF, DOCX, XLSX, CSV and text documents are parsed, and scanned pages fall back to OCR. Every page, table and chunk keeps its provenance.",
  },
  {
    icon: Layers,
    title: "Index",
    body: "Chunks are embedded into a vector index and mirrored into a keyword index, so both semantic and exact lookups are possible.",
  },
  {
    icon: FileSearch,
    title: "Retrieve and verify",
    body: "The query is understood, candidates are fused and reranked, then each statement in the answer is checked against the retrieved passages.",
  },
  {
    icon: BadgeCheck,
    title: "Report",
    body: "You get the answer, the evidence behind it, the verification outcome and any conflict between sources, in one view.",
  },
];

export function LandingPage() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 lg:px-6">
      <section className="grid gap-10 py-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:items-center lg:py-16">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Procurement intelligence</p>
          <h1 className="mt-3 text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
            Find the contract terms, prices and compliance requirements behind every procurement decision.
          </h1>
          <p className="mt-4 max-w-xl text-sm leading-relaxed text-muted-foreground">
            Search supplier agreements, pricing schedules, amendments and compliance documents, then open the page each
            answer came from. The workspace shows what was retrieved, what was verified and what could not be found.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button asChild size="lg">
              <Link to="/login">Open workspace</Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <a href="#how-it-works">See how it works</a>
            </Button>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            Sign-in is required because every lookup is scoped to a tenant and to the document access level of the
            signed-in account.
          </p>
        </div>

        <QueryFlowIllustration />
      </section>

      {/* The visual identity of the product, kept to one deliberate band: what
          the platform does with documents, drawn in three dimensions. */}
      <section aria-labelledby="evidence-flow-heading" className="hairline pb-12">
        <h2 id="evidence-flow-heading" className="text-sm font-semibold tracking-tight">
          Documents, the passage they support, and the answer built from it
        </h2>
        <p className="mb-4 mt-1.5 max-w-2xl text-xs leading-relaxed text-muted-foreground">
          The illustration below is interactive and optional: drag to orbit, scroll to zoom, pause the motion, reset the
          view, or switch it off. It shows the structure of the workflow only — no figures, because a schematic must not
          be mistaken for data. It is not loaded at all on a small screen or without WebGL.
        </p>
        <LazyHeroScene fallback={<HeroSceneFallback />} />
      </section>

      <section aria-labelledby="capabilities-heading" className="hairline py-12">
        <h2 id="capabilities-heading" className="text-xl font-semibold tracking-tight">
          What the workspace does
        </h2>
        <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">
          Each capability below is implemented in this build. Nothing here is a roadmap item presented as a feature.
        </p>
        <ul className="mt-6 grid gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((capability) => (
            <li key={capability.title}>
              <capability.icon className="h-4 w-4 text-primary" aria-hidden="true" />
              <h3 className="mt-2.5 text-sm font-medium">{capability.title}</h3>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{capability.body}</p>
            </li>
          ))}
        </ul>
      </section>

      <section id="how-it-works" aria-labelledby="how-heading" className="hairline scroll-mt-20 py-12">
        <h2 id="how-heading" className="text-xl font-semibold tracking-tight">
          How a document becomes an answer
        </h2>
        <ol className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, index) => (
            <li key={step.title} className="border-l pl-4">
              <span className="tnum text-[11px] font-medium text-muted-foreground">Step {index + 1}</span>
              <h3 className="mt-1 flex items-center gap-2 text-sm font-medium">
                <step.icon className="h-4 w-4 text-primary" aria-hidden="true" />
                {step.title}
              </h3>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="trust-heading" className="hairline py-12">
        <h2 id="trust-heading" className="text-xl font-semibold tracking-tight">
          How to read what you see
        </h2>
        <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">
          The workspace is built so a value is never invented to fill a space: a figure that is not recorded is labelled,
          an answer without evidence is refused, and the demo corpus is marked wherever it appears.
        </p>
        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          <div className="border-l pl-4">
            <h3 className="text-sm font-medium">Numbers come from the database</h3>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              Document, page, chunk, supplier, contract, price and compliance counts are read from the workspace
              database. Nothing is estimated to fill a panel, and a value that does not exist is labelled as not
              recorded rather than shown as zero.
            </p>
          </div>
          <div className="border-l pl-4">
            <h3 className="text-sm font-medium">Model availability is stated</h3>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              When no language model endpoint is configured, answers are composed from retrieved passages in extractive
              mode and the workspace says so on screen. The same applies to the vision model and the reranker.
            </p>
          </div>
          <div className="border-l pl-4">
            <h3 className="text-sm font-medium">Quality claims are measured</h3>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              Retrieval and answer quality are only reported as evaluation runs over a hand-labelled question set. Where
              the dataset carries no ground truth for a metric, it is reported as not evaluated rather than as a score.
            </p>
          </div>
        </div>
        <p className="mt-6 max-w-3xl text-xs leading-relaxed text-muted-foreground">
          The corpus shipped with this build is a labelled synthetic demo dataset. Documents from that set are marked in
          the interface, so demo content is never mistaken for a customer&apos;s own records.
        </p>
      </section>
    </div>
  );
}

/** Text equivalent of the 3D band, shown whenever the scene is switched off. */
function HeroSceneFallback() {
  return (
    <ol className="space-y-2 text-xs">
      {[
        "A master contract, an amendment and a pricing schedule are retrieved separately.",
        "The passage that supports the answer is quoted and marked as cited evidence.",
        "The answer is composed from that passage, with the document and page attached to it.",
      ].map((step, index) => (
        <li key={step} className="flex gap-2">
          <span className="tnum text-muted-foreground">{index + 1}.</span>
          <span>{step}</span>
        </li>
      ))}
    </ol>
  );
}

/**
 * The hero visual is the product itself: a question, the evidence it resolved
 * to, the answer, and the verification outcome. It is labelled as an example so
 * it cannot be read as a live measurement.
 */
function QueryFlowIllustration() {
  return (
    <figure className="rounded-lg border bg-card">
      <figcaption className="flex items-center justify-between gap-3 border-b px-4 py-2.5">
        <span className="text-xs font-medium">Example query flow</span>
        <span className="text-[11px] text-muted-foreground">illustrative, not a live measurement</span>
      </figcaption>

      <div className="space-y-4 p-4">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Question</p>
          <p className="mt-1 rounded-md border bg-muted/40 px-3 py-2 text-sm">{FLOW_QUESTION}</p>
        </div>

        <div>
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Evidence retrieved</p>
          <ul className="mt-1.5 space-y-2">
            <EvidenceRow
              document="Master Supply Agreement"
              page="page 18"
              section="Pricing Schedule"
              detail="Original unit price row for the X200, effective from the contract start date."
              tone="neutral"
            />
            <EvidenceRow
              document="Amendment 2"
              page="page 2"
              section="Revised unit price"
              detail="Supersedes the original row and sets the price from its own effective date."
              tone="primary"
            />
          </ul>
        </div>

        <div className="rounded-md border border-success/35 bg-success/5 p-3">
          <p className="text-[11px] uppercase tracking-wide text-success">Answer</p>
          <p className="mt-1 text-sm leading-relaxed">
            The price in force is the one set by Amendment 2. The original pricing schedule row no longer governs,
            because the amendment supersedes it from its effective date.
          </p>
          <p className="mt-2 text-[11px] text-muted-foreground">
            Verification: supported. Two citations, one superseded row detected, no unresolved conflict.
          </p>
        </div>
      </div>
    </figure>
  );
}

function EvidenceRow({
  document,
  page,
  section,
  detail,
  tone,
}: {
  document: string;
  page: string;
  section: string;
  detail: string;
  tone: "neutral" | "primary";
}) {
  return (
    <li
      className={cn(
        "rounded-md border px-3 py-2",
        tone === "primary" ? "border-primary/35 bg-primary/5" : "bg-background",
      )}
    >
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-medium">{document}</span>
        <span className="text-muted-foreground">{page}</span>
        <span className="text-muted-foreground">{section}</span>
        {tone === "primary" ? (
          <span className="ml-auto rounded border border-primary/35 px-1.5 text-[10px] text-primary">supersedes</span>
        ) : null}
      </div>
      <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{detail}</p>
    </li>
  );
}
