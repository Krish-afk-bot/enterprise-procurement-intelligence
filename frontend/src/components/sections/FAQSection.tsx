import { useState, useRef } from "react";
import { ChevronDown } from "lucide-react";
import { WordReveal } from "@/components/animations/WordReveal";
import { cn } from "@/lib/utils";

const FAQS = [
  {
    id: "what-is-epi",
    question: "What is EPI?",
    answer:
      "EPI (Enterprise Procurement Intelligence) is a self-hosted platform that connects procurement records, supplier agreements, pricing schedules, and compliance documents into one intelligence layer. Every answer includes the source evidence it was built from, so operators can verify claims and trace decisions back to their supporting documents.",
  },
  {
    id: "how-rag-works",
    question: "How does evidence-grounded RAG work?",
    answer:
      "EPI uses hybrid retrieval (dense embeddings + BM25 sparse search + RRF fusion), cross-encoder reranking, and claim-to-passage binding. Each statement in an answer is validated against retrieved evidence, and only verified claims are presented. Citations link directly to source document pages.",
  },
  {
    id: "supported-documents",
    question: "Which procurement documents are supported?",
    answer:
      "EPI processes PDF, DOCX, XLSX, CSV, HTML, and image formats (PNG, JPG, TIFF). OCR handles scanned documents, vision models escalate for complex tables, and semantic chunking preserves context across pages. Structured procurement data (OCDS format) is also imported and modeled in the knowledge graph.",
  },
  {
    id: "citation-generation",
    question: "How are citations generated?",
    answer:
      "Every chunk retrieved during hybrid search carries its source document ID, page number, and position. When a claim is verified against a passage, that passage's metadata becomes the citation. The citation includes the document name, page, and a direct link to open that page in the document viewer.",
  },
  {
    id: "tenant-isolation",
    question: "How does tenant isolation work?",
    answer:
      "Every database row, vector, graph node, and cache key is scoped to a tenant ID. Queries filter by tenant at the lowest layer, before any business logic runs. A signed-in account can only access documents within its tenant and only at the document access level granted to that account's role.",
  },
  {
    id: "mcp-integration",
    question: "Does EPI support external AI assistants through MCP?",
    answer:
      "Yes. EPI exposes a Model Context Protocol (MCP) server that external AI assistants can invoke. Tools include document search, supplier lookup, contract retrieval, and evidence-grounded Q&A. The MCP server is scoped to one tenant and one account, so an assistant cannot widen access beyond what that account is permitted to see.",
  },
];

/**
 * FAQ Section (Scene 08).
 *
 * Features:
 * - Dark background
 * - Accordion with smooth height transitions
 * - One item open at a time
 * - Keyboard accessible
 * - First item open by default
 */
export function FAQSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const [openId, setOpenId] = useState<string>(FAQS[0].id);

  const toggleItem = (id: string) => {
    setOpenId((current) => (current === id ? "" : id));
  };

  return (
    <section
      id="faq"
      ref={sectionRef}
      className="relative scroll-mt-24 bg-ink px-5 py-24 lg:px-8 lg:py-28"
    >
      <div className="relative mx-auto w-full max-w-4xl">
        {/* Heading */}
        <div className="text-center">
          <WordReveal mode="scroll" triggerRef={sectionRef} className="text-display-sm text-balance">
            Frequently Asked Questions.
          </WordReveal>
        </div>

        {/* Accordion */}
        <div className="mt-12 space-y-2">
          {FAQS.map((faq) => (
            <FAQItem
              key={faq.id}
              faq={faq}
              isOpen={openId === faq.id}
              onToggle={() => toggleItem(faq.id)}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

/**
 * Individual FAQ accordion item.
 */
function FAQItem({
  faq,
  isOpen,
  onToggle,
}: {
  faq: (typeof FAQS)[0];
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border transition-colors duration-300",
        isOpen ? "border-white/15 bg-white/[0.04]" : "border-white/8 bg-transparent"
      )}
    >
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-4 p-5 text-left transition-colors duration-200 hover:bg-white/[0.02] focus-visible:bg-white/[0.02]"
        aria-expanded={isOpen}
      >
        {/* Chevron */}
        <div
          className={cn(
            "flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-white/10 bg-white/[0.03] transition-transform duration-300",
            isOpen && "rotate-180"
          )}
        >
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </div>

        {/* Question */}
        <span className="flex-1 text-[15px] font-medium">{faq.question}</span>
      </button>

      {/* Answer */}
      <div
        className={cn(
          "overflow-hidden transition-all duration-300 ease-out",
          isOpen ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"
        )}
      >
        <div className="px-5 pb-5 pl-[52px]">
          <p className="text-[14px] leading-relaxed text-muted-foreground">{faq.answer}</p>
        </div>
      </div>
    </div>
  );
}
