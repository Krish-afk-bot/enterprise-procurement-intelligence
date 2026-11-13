import { Link } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
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
 * Visually appealing landing page with smooth animations.
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

// Hook to detect when element enters viewport
function useInView() {
  const ref = useRef<HTMLDivElement>(null);
  const [isInView, setIsInView] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
        }
      },
      { threshold: 0.1 }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => {
      if (ref.current) {
        observer.unobserve(ref.current);
      }
    };
  }, []);

  return { ref, isInView };
}

/* ------------------------------------------------------------------ hero */

function Hero() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <section className="relative min-h-[90vh] overflow-hidden px-5 py-32 lg:px-8">
      {/* Animated gradient background */}
      <div className="pointer-events-none absolute inset-0 opacity-30">
        <div className="animate-gradient absolute left-1/2 top-0 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-gradient-to-br from-orange-500/20 via-transparent to-transparent blur-3xl" />
        <div className="animate-gradient-reverse absolute right-0 top-1/4 h-[500px] w-[500px] rounded-full bg-gradient-to-bl from-blue-500/10 via-transparent to-transparent blur-3xl" />
      </div>

      {/* Grid pattern */}
      <div className="pointer-events-none absolute inset-0 opacity-[0.02]" style={{
        backgroundImage: 'linear-gradient(to right, #fff 1px, transparent 1px), linear-gradient(to bottom, #fff 1px, transparent 1px)',
        backgroundSize: '40px 40px'
      }} aria-hidden="true" />

      <div className={`relative mx-auto w-full max-w-5xl text-center transition-all duration-1000 ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>
        <p className="animate-fade-in inline-flex items-center gap-2 rounded-md border border-white/15 bg-white/[0.04] px-3 py-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground backdrop-blur-sm">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-orange-400" aria-hidden="true" />
          Enterprise procurement intelligence
        </p>

        <h1 className="animate-fade-in-up mx-auto mt-8 max-w-4xl bg-gradient-to-br from-white via-white to-white/60 bg-clip-text text-5xl font-bold tracking-tight text-transparent sm:text-6xl lg:text-7xl">
          Procurement Intelligence.
          <span className="mt-2 block bg-gradient-to-r from-white/50 to-white/30 bg-clip-text">Powered by Evidence.</span>
        </h1>

        <p className="mx-auto mt-6 max-w-2xl animate-fade-in-up text-base leading-relaxed text-muted-foreground sm:text-lg [animation-delay:100ms]">
          Search supplier agreements, pricing schedules, amendments and compliance documents — then open the exact
          page every answer was built from.
        </p>

        <div className="mt-10 flex animate-fade-in-up flex-col items-center justify-center gap-3 sm:flex-row [animation-delay:200ms]">
          <Button size="lg" variant="glow" asChild className="group">
            <Link to="/login">
              Explore Intelligence
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" aria-hidden="true" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild className="backdrop-blur-sm">
            <a href="#platform">View Platform</a>
          </Button>
        </div>

        <p className="mt-6 animate-fade-in text-xs text-subtle [animation-delay:300ms]">
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
  const { ref, isInView } = useInView();

  return (
    <section id="platform" className="relative border-t border-white/[0.07] bg-ink-2 px-5 py-24 lg:px-8 lg:py-32">
      {/* Subtle glow effect */}
      <div className="pointer-events-none absolute left-0 top-0 h-full w-full overflow-hidden">
        <div className="absolute -left-32 top-1/4 h-[400px] w-[400px] rounded-full bg-orange-500/5 blur-3xl" />
      </div>

      <div ref={ref} className="relative mx-auto w-full max-w-7xl">
        <div className={`max-w-3xl transition-all duration-700 ${isInView ? 'translate-y-0 opacity-100' : 'translate-y-12 opacity-0'}`}>
          <p className="text-xs font-medium uppercase tracking-wider text-subtle">The platform</p>
          <h2 className="mt-4 bg-gradient-to-br from-white to-white/70 bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
            One Intelligence Layer for Procurement.
          </h2>
          <p className="mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground">
            Records, documents and the relationships between them are held in one system, so a question resolves to an
            answer and to the evidence that supports it.
          </p>
        </div>

        <div className="mt-14 grid gap-6 lg:grid-cols-3">
          {PILLARS.map((pillar, i) => (
            <article
              key={pillar.title}
              className={`glass group rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.03] to-transparent p-8 backdrop-blur-sm transition-all duration-500 hover:-translate-y-1 hover:border-white/20 hover:shadow-lg hover:shadow-orange-500/5 ${
                isInView ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'
              }`}
              style={{ transitionDelay: `${i * 100}ms` }}
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/12 bg-gradient-to-br from-orange-500/10 to-transparent text-white shadow-lg transition-all duration-300 group-hover:scale-110 group-hover:border-orange-500/30 group-hover:shadow-orange-500/20">
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
  const { ref, isInView } = useInView();

  return (
    <section className="border-t border-white/[0.07] bg-ink px-5 py-24 lg:px-8 lg:py-32">
      <div ref={ref} className="mx-auto w-full max-w-7xl">
        <div className={`text-center transition-all duration-700 ${isInView ? 'translate-y-0 opacity-100' : 'translate-y-12 opacity-0'}`}>
          <h2 className="bg-gradient-to-r from-white via-white to-white/60 bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
            Built to Connect Every Piece of Evidence.
          </h2>
        </div>

        <div className="mt-16 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((cap, i) => (
            <div
              key={cap.title}
              className={`group relative overflow-hidden rounded-xl border border-white/10 bg-gradient-to-br from-white/[0.02] to-transparent p-6 backdrop-blur-sm transition-all duration-500 hover:-translate-y-1 hover:border-orange-500/30 hover:bg-white/[0.04] ${
                isInView ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'
              }`}
              style={{ transitionDelay: `${i * 50}ms` }}
            >
              {/* Hover glow effect */}
              <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-orange-500/0 blur-2xl transition-all duration-500 group-hover:bg-orange-500/10" />
              
              <cap.icon className="relative h-8 w-8 text-orange-400 transition-transform duration-300 group-hover:scale-110" />
              <h3 className="relative mt-4 text-lg font-semibold">{cap.title}</h3>
              <p className="relative mt-2 text-sm text-muted-foreground">{cap.desc}</p>
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
  const { ref, isInView } = useInView();

  return (
    <section className="relative border-t border-white/[0.07] bg-ink-2 px-5 py-24 lg:px-8 lg:py-32">
      {/* Background glow */}
      <div className="pointer-events-none absolute right-0 top-1/3 h-[500px] w-[500px] rounded-full bg-blue-500/5 blur-3xl" />

      <div ref={ref} className="relative mx-auto w-full max-w-7xl">
        <div className={`text-center transition-all duration-700 ${isInView ? 'translate-y-0 opacity-100' : 'translate-y-12 opacity-0'}`}>
          <h2 className="bg-gradient-to-br from-white to-white/70 bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
            Intelligence Across the Procurement Lifecycle.
          </h2>
        </div>

        <div className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {USE_CASES.map((useCase, i) => (
            <article
              key={useCase.title}
              className={`group relative overflow-hidden rounded-xl border border-white/10 bg-gradient-to-br from-white/[0.02] to-transparent p-6 backdrop-blur-sm transition-all duration-500 hover:-translate-y-1 hover:border-white/20 hover:shadow-lg ${
                isInView ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'
              }`}
              style={{ transitionDelay: `${i * 60}ms` }}
            >
              {/* Animated icon background */}
              <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-gradient-to-br from-white/5 to-transparent opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-100" />
              
              <useCase.icon className="relative h-8 w-8 text-white transition-transform duration-300 group-hover:scale-110" />
              <h3 className="relative mt-4 text-lg font-semibold">{useCase.title}</h3>
              <p className="relative mt-2 text-sm text-muted-foreground">{useCase.desc}</p>
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
  const { ref, isInView } = useInView();

  return (
    <section className="border-t border-white/[0.07] bg-ink px-5 py-24 lg:px-8 lg:py-28">
      <div ref={ref} className="mx-auto w-full max-w-7xl">
        <div className={`max-w-3xl transition-all duration-700 ${isInView ? 'translate-y-0 opacity-100' : 'translate-y-12 opacity-0'}`}>
          <p className="text-xs font-medium uppercase tracking-wider text-subtle">How to read what you see</p>
          <h2 className="mt-4 bg-gradient-to-br from-white to-white/70 bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
            A value is never invented to fill a space.
          </h2>
        </div>

        <div className="mt-12 grid gap-8 lg:grid-cols-3">
          {TRUST.map((item, i) => (
            <div
              key={item.title}
              className={`group border-t border-white/10 pt-6 transition-all duration-500 hover:border-orange-500/30 ${
                isInView ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'
              }`}
              style={{ transitionDelay: `${i * 100}ms` }}
            >
              <item.icon className="h-5 w-5 text-white/60 transition-colors duration-300 group-hover:text-orange-400" aria-hidden="true" />
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
  const { ref, isInView } = useInView();

  return (
    <section className="border-t border-white/[0.07] bg-ink-2 px-5 py-24 lg:px-8 lg:py-28">
      <div ref={ref} className="mx-auto w-full max-w-4xl">
        <div className={`text-center transition-all duration-700 ${isInView ? 'translate-y-0 opacity-100' : 'translate-y-12 opacity-0'}`}>
          <h2 className="bg-gradient-to-br from-white to-white/70 bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
            Frequently Asked Questions.
          </h2>
        </div>

        <div className="mt-12 space-y-6">
          {FAQS.map((faq, i) => (
            <details
              key={i}
              className={`group rounded-xl border border-white/10 bg-gradient-to-br from-white/[0.02] to-transparent p-6 backdrop-blur-sm transition-all duration-500 hover:border-white/20 ${
                isInView ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'
              }`}
              style={{ transitionDelay: `${i * 80}ms` }}
            >
              <summary className="cursor-pointer text-base font-semibold transition-colors hover:text-white/90">
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
  const { ref, isInView } = useInView();

  return (
    <section className="relative border-t border-white/[0.07] bg-ink px-5 py-28 lg:px-8 lg:py-36">
      {/* Central glow */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[400px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-r from-orange-500/10 to-blue-500/10 blur-3xl" />

      <div ref={ref} className={`relative mx-auto max-w-3xl text-center transition-all duration-700 ${isInView ? 'translate-y-0 opacity-100' : 'translate-y-12 opacity-0'}`}>
        <h2 className="bg-gradient-to-br from-white to-white/70 bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
          Start with the evidence.
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-muted-foreground">
          Ask a question, open the page it came from, and decide for yourself. If the records do not support the
          answer, the platform will say so.
        </p>
        <div className={`mt-8 flex flex-col items-center justify-center gap-3 transition-all duration-700 delay-200 sm:flex-row ${isInView ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>
          <Button size="lg" variant="glow" asChild className="group">
            <Link to="/login">
              Open workspace
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" aria-hidden="true" />
            </Link>
          </Button>
          <Button size="lg" variant="ghost" asChild className="backdrop-blur-sm">
            <Link to="/security">Read the security model</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
