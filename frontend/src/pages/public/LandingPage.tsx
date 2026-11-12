import { Link } from "react-router-dom";
import {
  ArrowRight,
  ChartNoAxesColumn,
  FileText,
  GitBranch,
  Layers,
  Link2,
  Search,
  ShieldCheck,
  Users,
  DollarSign,
  GitCompare,
  Network,
  Sparkles,
  TriangleAlert,
} from "lucide-react";

import { ScrollProgress } from "@/components/motion/ScrollProgress";
import { Button } from "@/components/ui/button";

/**
 * Simple, clean landing page.
 * No heavy animations, no 3D, just clear content and basic interactions.
 */
export function LandingPage() {
  return (
    <div className="bg-ink text-foreground">
      <ScrollProgress />
      <Hero />
      <Platform />
      <Capabilities />
      <UseCases />
      <Trust />
      <FAQ />
      <CTA />
    </div>
  );
}

/* ------------------------------------------------------------------ hero */

function Hero() {
  return (
    <section className="relative min-h-[90vh] px-5 py-32 lg:px-8">
      {/* Simple grid background */}
      <div className="pointer-events-none absolute inset-0 opacity-[0.02]" style={{
        backgroundImage: 'linear-gradient(to right, #fff 1px, transparent 1px), linear-gradient(to bottom, #fff 1px, transparent 1px)',
        backgroundSize: '40px 40px'
      }} aria-hidden="true" />

      <div className="relative mx-auto w-full max-w-5xl text-center">
        <p className="inline-flex items-center gap-2 rounded-md border border-white/15 bg-white/[0.04] px-3 py-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-white" aria-hidden="true" />
          Enterprise procurement intelligence
        </p>

        <h1 className="mx-auto mt-8 max-w-4xl text-5xl font-bold tracking-tight sm:text-6xl lg:text-7xl">
          Procurement Intelligence.
          <span className="mt-2 block text-white/50">Powered by Evidence.</span>
        </h1>

        <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
          Search supplier agreements, pricing schedules, amendments and compliance documents — then open the exact
          page every answer was built from.
        </p>

        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button size="lg" variant="glow" asChild>
            <Link to="/login">
              Explore Intelligence
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <a href="#platform">View Platform</a>
          </Button>
        </div>

        <p className="mt-6 text-xs text-subtle">
          Sign-in required: every lookup is scoped to a tenant and document access level.
        </p>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------- platform */

const PILLARS = [
  {
    icon: ChartNoAxesColumn,
    title: "Procurement Intelligence",
    body: "Structured procurement data, tender and award analysis, and buyer and supplier insight in one place.",
  },
  {
    icon: Link2,
    title: "Evidence-Based RAG",
    body: "Retrieval that answers from the documents you hold, and shows the page each statement came from.",
  },
  {
    icon: GitBranch,
    title: "Relationship Intelligence",
    body: "Suppliers, contracts, amendments and awards modelled as a network you can traverse from any record.",
  },
];

function Platform() {
  return (
    <section id="platform" className="border-t border-white/[0.07] bg-ink-2 px-5 py-24 lg:px-8 lg:py-32">
      <div className="mx-auto w-full max-w-7xl">
        <div className="max-w-3xl">
          <p className="text-xs font-medium uppercase tracking-wider text-subtle">The platform</p>
          <h2 className="mt-4 text-4xl font-bold tracking-tight sm:text-5xl">
            One Intelligence Layer for Procurement.
          </h2>
          <p className="mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground">
            Records, documents and the relationships between them are held in one system, so a question resolves to an
            answer and to the evidence that supports it.
          </p>
        </div>

        <div className="mt-14 grid gap-6 lg:grid-cols-3">
          {PILLARS.map((pillar) => (
            <article
              key={pillar.title}
              className="glass group rounded-2xl border border-white/10 p-8 transition-all duration-200 hover:border-white/20"
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/12 bg-white/[0.05] text-white">
                <pillar.icon className="h-6 w-6" aria-hidden="true" />
              </span>
              <h3 className="mt-6 text-xl font-semibold tracking-tight">{pillar.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{pillar.body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------- capabilities */

const CAPABILITIES = [
  { icon: Search, title: "Hybrid Retrieval", desc: "Dense embeddings + BM25 + cross-encoder reranking" },
  { icon: GitBranch, title: "Multi-Agent Intelligence", desc: "Query planning, retrieval, and verification" },
  { icon: ShieldCheck, title: "Evidence Verification", desc: "Claim-to-passage binding with citations" },
  { icon: Layers, title: "Knowledge Graph", desc: "Suppliers, contracts, and relationship networks" },
  { icon: FileText, title: "Document Intelligence", desc: "OCR, chunking, and vision escalation" },
  { icon: Link2, title: "MCP Integration", desc: "External AI assistant tool invocation" },
];

function Capabilities() {
  return (
    <section className="border-t border-white/[0.07] bg-ink px-5 py-24 lg:px-8 lg:py-32">
      <div className="mx-auto w-full max-w-7xl">
        <div className="text-center">
          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Built to Connect Every Piece of Evidence.
          </h2>
        </div>

        <div className="mt-16 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((cap) => (
            <div
              key={cap.title}
              className="group rounded-xl border border-white/10 p-6 transition-all duration-200 hover:border-white/20 hover:bg-white/[0.02]"
            >
              <cap.icon className="h-8 w-8 text-orange-400" />
              <h3 className="mt-4 text-lg font-semibold">{cap.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{cap.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------- use cases */

const USE_CASES = [
  { icon: FileText, title: "Contract Intelligence", desc: "Search clauses, terms, and obligations" },
  { icon: Users, title: "Supplier Intelligence", desc: "Entity resolution and relationship discovery" },
  { icon: DollarSign, title: "Pricing Analysis", desc: "Compare prices and validate decisions" },
  { icon: ShieldCheck, title: "Compliance Monitoring", desc: "Verify certifications and track requirements" },
  { icon: GitCompare, title: "Amendment Tracking", desc: "Trace versions and understand changes" },
  { icon: Network, title: "Relationship Discovery", desc: "Navigate the procurement network" },
];

function UseCases() {
  return (
    <section className="border-t border-white/[0.07] bg-ink-2 px-5 py-24 lg:px-8 lg:py-32">
      <div className="mx-auto w-full max-w-7xl">
        <div className="text-center">
          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Intelligence Across the Procurement Lifecycle.
          </h2>
        </div>

        <div className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {USE_CASES.map((useCase) => (
            <article
              key={useCase.title}
              className="rounded-xl border border-white/10 bg-white/[0.02] p-6 transition-all duration-200 hover:border-white/20"
            >
              <useCase.icon className="h-8 w-8 text-white" />
              <h3 className="mt-4 text-lg font-semibold">{useCase.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{useCase.desc}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- trust */

const TRUST = [
  {
    icon: Layers,
    title: "Numbers come from the database",
    body: "Document, page, chunk, supplier, contract and price counts are read from the workspace database.",
  },
  {
    icon: Sparkles,
    title: "Model availability is stated",
    body: "When no language model is configured, answers are composed from retrieved passages in extractive mode.",
  },
  {
    icon: TriangleAlert,
    title: "Refusals instead of guesses",
    body: "If the corpus does not support a question, the platform returns no verified evidence and explains why.",
  },
];

function Trust() {
  return (
    <section className="border-t border-white/[0.07] bg-ink px-5 py-24 lg:px-8 lg:py-28">
      <div className="mx-auto w-full max-w-7xl">
        <div className="max-w-3xl">
          <p className="text-xs font-medium uppercase tracking-wider text-subtle">How to read what you see</p>
          <h2 className="mt-4 text-4xl font-bold tracking-tight sm:text-5xl">
            A value is never invented to fill a space.
          </h2>
        </div>

        <div className="mt-12 grid gap-8 lg:grid-cols-3">
          {TRUST.map((item) => (
            <div key={item.title} className="border-t border-white/10 pt-6">
              <item.icon className="h-5 w-5 text-white/60" aria-hidden="true" />
              <h3 className="mt-4 text-base font-semibold">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{item.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------- faq */

const FAQS = [
  {
    q: "What is EPI?",
    a: "EPI is a self-hosted platform connecting procurement records, supplier agreements, pricing schedules, and compliance documents into one intelligence layer with source evidence for every answer.",
  },
  {
    q: "How does evidence-grounded RAG work?",
    a: "EPI uses hybrid retrieval (dense + sparse + fusion), cross-encoder reranking, and claim-to-passage binding. Each statement is validated against retrieved evidence.",
  },
  {
    q: "Which documents are supported?",
    a: "EPI processes PDF, DOCX, XLSX, CSV, HTML, and images. OCR handles scanned documents, and vision models escalate for complex tables.",
  },
  {
    q: "How are citations generated?",
    a: "Every retrieved chunk carries its source document ID, page number, and position. When a claim is verified, that metadata becomes the citation with a direct link.",
  },
];

function FAQ() {
  return (
    <section className="border-t border-white/[0.07] bg-ink-2 px-5 py-24 lg:px-8 lg:py-28">
      <div className="mx-auto w-full max-w-4xl">
        <div className="text-center">
          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Frequently Asked Questions.
          </h2>
        </div>

        <div className="mt-12 space-y-6">
          {FAQS.map((faq, i) => (
            <details key={i} className="group rounded-xl border border-white/10 bg-white/[0.02] p-6">
              <summary className="cursor-pointer text-base font-semibold">
                {faq.q}
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{faq.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------- cta */

function CTA() {
  return (
    <section className="border-t border-white/[0.07] bg-ink px-5 py-28 lg:px-8 lg:py-36">
      <div className="relative mx-auto max-w-3xl text-center">
        <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Start with the evidence.
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-muted-foreground">
          Ask a question, open the page it came from, and decide for yourself. If the records do not support the
          answer, the platform will say so.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button size="lg" variant="glow" asChild>
            <Link to="/login">
              Open workspace
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
          <Button size="lg" variant="ghost" asChild>
            <Link to="/security">Read the security model</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
