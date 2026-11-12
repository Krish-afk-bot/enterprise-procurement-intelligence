import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, CornerDownLeft, Loader2, MessageSquarePlus, Settings2, Square } from "lucide-react";

import { AnswerPanel } from "@/components/answer/AnswerPanel";
import { EarlyEvidence } from "@/components/answer/EarlyEvidence";
import { EvidencePanel } from "@/components/answer/EvidencePanel";
import { StatusRail } from "@/components/answer/StatusRail";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { CitationChip } from "@/components/common/Evidence";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Switch } from "@/components/ui/misc";
import { useAskStream } from "@/features/ask/useAskStream";
import { api } from "@/lib/api";
import { MICROCOPY, microcopyPlain } from "@/lib/microcopy";
import { useMood } from "@/lib/useMood";
import { cn, formatDateTime, plural } from "@/lib/utils";

const EXAMPLE_QUESTIONS = [
  "What is Supplier A's current price for the Industrial Laptop X200?",
  "What changed between the original contract and Amendment 2?",
  "Compare Supplier A and Supplier B prices for the Industrial Laptop X200.",
  "Which supplier had the lowest price for the Industrial Laptop X200 in 2025?",
  "What does the pricing table on page 4 of the Northwind master contract say?",
  "Which suppliers hold ISO 9001 certification and under which contract?",
  "What was Supplier C's price in 2030?",
];

export function AskPage() {
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState("");
  const [strategy, setStrategy] = useState("auto");
  const [topK, setTopK] = useState("15");
  const [includeSynthetic, setIncludeSynthetic] = useState(true);
  const [includeTrace, setIncludeTrace] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [copied, setCopied] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const {
    conversationId,
    events,
    evidence,
    answer,
    error,
    streaming,
    verifying,
    ask,
    stop,
    reset,
    openConversation: openStoredConversation,
  } = useAskStream();

  // The world reacts to what the application is really doing: a question is
  // running, the answer is supported, the records disagree, or the documents do
  // not say. Nothing here is driven by a timer.
  useMood(
    error
      ? "error"
      : streaming
        ? "loading"
        : answer
          ? answer.status === "conflicting"
            ? "conflict"
            : answer.status === "insufficient_evidence"
              ? "unsupported"
              : answer.status === "error"
                ? "error"
                : "found"
          : null,
  );

  /** Open the technical details and bring them into view (they may sit below). */
  function openDetails() {
    setDetailsOpen(true);
    window.setTimeout(() => {
      document.getElementById("technical-details")?.scrollIntoView({ block: "start", behavior: "smooth" });
    }, 0);
  }

  const conversations = useQuery({
    queryKey: ["conversations"],
    queryFn: () => api.conversations({ limit: 25 }),
  });

  const transcript = useQuery({
    queryKey: ["conversation-messages", conversationId],
    queryFn: () => api.conversationMessages(conversationId!, { limit: 100 }),
    enabled: Boolean(conversationId),
  });

  const filters = useQuery({ queryKey: ["filters"], queryFn: api.filters });
  const strategies = useMemo(
    () => ["auto", ...(filters.data?.strategies ?? ["dense", "sparse", "hybrid", "hybrid_rerank", "agentic"])],
    [filters.data],
  );

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 1600);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function run() {
    const trimmed = question.trim();
    if (!trimmed || streaming) return;
    await ask({
      query: trimmed,
      strategy: strategy === "auto" ? null : strategy,
      top_k: Number(topK),
      include_trace: includeTrace,
      filters: { include_synthetic: includeSynthetic },
    });
    void queryClient.invalidateQueries({ queryKey: ["filters"] });
  }

  function startNewQuestion() {
    reset();
    setQuestion("");
    composerRef.current?.focus();
  }

  function openConversation(id: string) {
    if (id === conversationId) return;
    openStoredConversation(id);
  }

  const messageCount = conversations.data?.items.length ?? 0;

  return (
    <div className="space-y-5">
      {/* The screen opens on the corpus, then the question. A reviewer should
          not have to open another page to learn what they are asking against. */}
      <header className="flex flex-wrap items-end justify-between gap-x-10 gap-y-4 border-b border-white/[0.07] pb-5">
        <div className="min-w-0">
          <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-subtle">Ask</p>
          <h1 className="mt-2 text-[26px] font-semibold leading-[1.15] tracking-tight sm:text-[30px]">
            Put a question to the contracts
          </h1>
          <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-muted-foreground">
            Answers are assembled from cited passages and then checked against them. When the corpus does not hold
            the fact, the answer says so instead of estimating.
          </p>
        </div>
        <dl className="flex flex-wrap gap-x-8 gap-y-3">
          {[
            { label: "Suppliers", value: filters.data?.suppliers.length },
            { label: "Contracts", value: filters.data?.contracts.length },
            { label: "Document types", value: filters.data?.document_types.length },
          ].map((stat) => (
            <div key={stat.label}>
              <dt className="text-[10px] font-medium uppercase tracking-[0.14em] text-subtle">{stat.label}</dt>
              <dd className="tnum mt-1 text-xl font-semibold leading-none">
                {stat.value === undefined ? "—" : stat.value}
              </dd>
            </div>
          ))}
        </dl>
      </header>

      <p className="text-[11px] leading-relaxed text-subtle">
        Passages marked <span className="font-medium text-muted-foreground">demo corpus</span> come from files
        uploaded with that label; unlabelled passages are the imported public notices. Each citation carries its own
        label.
      </p>

      <div className="grid gap-5 xl:grid-cols-[236px_minmax(0,1fr)_minmax(320px,380px)]">
        {/* Question history: real conversations persisted by the API */}
        <aside aria-label="Question history" className="min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-[10px] font-medium uppercase tracking-[0.16em] text-subtle">
              Recent questions{messageCount > 0 ? <span className="tnum ml-1.5 text-muted-foreground">{messageCount}</span> : null}
            </h2>
            <Button variant="ghost" size="sm" className="gap-1.5 px-2" onClick={startNewQuestion}>
              <MessageSquarePlus className="h-3.5 w-3.5" aria-hidden="true" />
              New
            </Button>
          </div>
          <div className="mt-2">
            {conversations.isLoading ? (
              <LoadingState label={MICROCOPY.loadingScene} />
            ) : conversations.isError ? (
              <ErrorState error={conversations.error} onRetry={() => void conversations.refetch()} />
            ) : messageCount === 0 ? (
              <p className="rounded-md border border-dashed p-3 text-[11px] leading-relaxed text-muted-foreground">
                Nothing stored yet. Questions you ask are kept in this workspace so you can return to them.
              </p>
            ) : (
              <ul className="max-h-[320px] space-y-0.5 overflow-y-auto pr-1 scrollbar-thin xl:max-h-[calc(100vh-260px)]">
                {(conversations.data?.items ?? []).map((conversation) => (
                  <li key={conversation.id}>
                    <button
                      type="button"
                      onClick={() => openConversation(conversation.id)}
                      aria-current={conversation.id === conversationId ? "true" : undefined}
                      className={cn(
                        "w-full rounded-md border-l-2 px-2.5 py-2 text-left text-xs transition-colors duration-micro",
                        conversation.id === conversationId
                          ? "border-l-primary bg-primary/10"
                          : "border-l-transparent hover:bg-accent",
                      )}
                    >
                      <span className="line-clamp-2 font-medium">{conversation.title}</span>
                      <span className="mt-0.5 block text-[10px] text-muted-foreground">
                        {plural(conversation.message_count, "message")}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>

        {/* Composer and answer */}
        <div className="min-w-0 space-y-5">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void run();
            }}
            className="group relative overflow-hidden rounded-2xl border border-white/[0.09] bg-card/80 p-4 transition-colors duration-300 focus-within:border-white/25 sm:p-5"
          >
            <span
              aria-hidden="true"
              className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/25 to-transparent"
            />
            <div className="flex items-baseline justify-between gap-3">
              <label htmlFor="ask-question" className="text-[10px] font-medium uppercase tracking-[0.16em] text-subtle">
                Your question
              </label>
              <span className="text-[10px] text-subtle">Prices · amendments · clauses · compliance · terms</span>
            </div>
            <Textarea
              id="ask-question"
              ref={composerRef}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                  event.preventDefault();
                  void run();
                }
              }}
              placeholder="What is the current unit price for the Industrial Laptop X200?"
              className="mt-2.5 min-h-[112px] resize-y border-white/[0.08] bg-transparent text-[15px] leading-relaxed"
            />
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Button type="submit" disabled={streaming || !question.trim()}>
                {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <CornerDownLeft className="h-4 w-4" />}
                {streaming ? "Running" : "Run query"}
              </Button>
              {streaming ? (
                <Button type="button" variant="outline" onClick={stop}>
                  <Square className="h-3.5 w-3.5" />
                  Stop
                </Button>
              ) : null}
              <Button type="button" variant="ghost" size="sm" className="gap-1.5" onClick={() => setShowSettings((value) => !value)} aria-expanded={showSettings}>
                <Settings2 className="h-3.5 w-3.5" aria-hidden="true" />
                Retrieval settings
              </Button>
              <span className="ml-auto text-[11px] text-muted-foreground">Cmd or Ctrl + Enter to run</span>
            </div>

            {showSettings ? (
              <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-3 border-t pt-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  Strategy
                  <Select value={strategy} onValueChange={setStrategy}>
                    <SelectTrigger className="h-8 w-[190px]" aria-label="Retrieval strategy">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {strategies.map((item) => (
                        <SelectItem key={item} value={item}>
                          {item === "auto" ? "auto (pipeline decides)" : item}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  Candidates
                  <Select value={topK} onValueChange={setTopK}>
                    <SelectTrigger className="h-8 w-[120px]" aria-label="Number of candidates to retrieve">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {["5", "10", "15", "25", "50"].map((value) => (
                        <SelectItem key={value} value={value}>
                          top {value}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center gap-2">
                  <Switch id="ask-synthetic" checked={includeSynthetic} onCheckedChange={setIncludeSynthetic} />
                  <label htmlFor="ask-synthetic" className="text-xs text-muted-foreground">
                    include labelled demo corpus
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch id="ask-trace" checked={includeTrace} onCheckedChange={setIncludeTrace} />
                  <label htmlFor="ask-trace" className="text-xs text-muted-foreground">
                    include execution trace in the evidence panel
                  </label>
                </div>
              </div>
            ) : null}
          </form>

          {!answer && !streaming && events.length === 0 && !transcript.data ? (
            <section aria-label="Example questions" className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-[10px] font-medium uppercase tracking-[0.16em] text-subtle">Start from one</h2>
                <span className="text-[10px] text-subtle">Replace the names with ones from Search</span>
              </div>
              <ul className="mt-3 grid gap-1 sm:grid-cols-2">
                {EXAMPLE_QUESTIONS.map((example, index) => (
                  <li key={example}>
                    <button
                      type="button"
                      onClick={() => {
                        setQuestion(example);
                        composerRef.current?.focus();
                      }}
                      className="group/item flex w-full items-start gap-2.5 rounded-lg border border-transparent px-2.5 py-2 text-left text-[12px] leading-snug text-muted-foreground transition-colors duration-micro hover:border-white/10 hover:bg-white/[0.04] hover:text-foreground"
                    >
                      <span className="tnum mt-px text-[10px] text-subtle group-hover/item:text-foreground/70">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      {example}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <StatusRail events={events} streaming={streaming} verifying={verifying} />

          {!answer ? <EarlyEvidence evidence={evidence} verifying={verifying} /> : null}

          {error ? <ErrorState error={error} onRetry={() => void run()} hint="The pipeline stopped before producing a verified answer." /> : null}

          {answer ? (
            <div className="space-y-4">
              <AnswerPanel answer={answer} onShowDetails={openDetails} />
              {answer.citations.length > 0 ? (
                <div className="space-y-1.5">
                  <p className="text-xs font-medium">Sources</p>
                  <div className="flex flex-wrap gap-1.5">
                    {answer.citations.slice(0, 8).map((citation, index) => (
                      <CitationChip key={citation.chunk_id ?? index} citation={citation} index={index + 1} />
                    ))}
                  </div>
                </div>
              ) : null}
              <div className="flex flex-wrap items-center gap-2 border-t pt-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    void navigator.clipboard.writeText(answer.answer_text).then(() => setCopied(true));
                  }}
                >
                  {copied ? <Check className="h-3.5 w-3.5 text-success" /> : null}
                  {copied ? "Copied" : "Copy answer"}
                </Button>
                <span className="text-[11px] text-muted-foreground">
                  Query {answer.query_id.slice(0, 8)} · {answer.citations.length} citation(s) ·{" "}
                  {answer.conflicts.length} conflict(s)
                </span>
              </div>
            </div>
          ) : null}

          {!answer && transcript.data ? (
            <section aria-label="Stored transcript" className="rounded-lg border">
              <header className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2.5">
                <h2 className="text-xs font-medium">Stored transcript</h2>
                <span className="text-[11px] text-muted-foreground">
                  {plural(transcript.data.total, "message")} in this conversation
                </span>
              </header>
              <ol className="divide-y">
                {(transcript.data.items ?? []).map((message) => (
                  <li key={message.id} className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                      <span className="font-medium text-foreground">{message.role === "user" ? "Question" : "Answer"}</span>
                      <span>{formatDateTime(message.created_at)}</span>
                      {message.query_id ? <span className="font-mono">query {message.query_id.slice(0, 8)}</span> : null}
                    </div>
                    <p
                      className={cn(
                        "mt-1.5 text-sm leading-relaxed",
                        message.role === "user" ? "font-medium" : "whitespace-pre-wrap",
                      )}
                    >
                      {message.content}
                    </p>
                    {message.role === "user" ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="mt-1.5 h-7 px-2 text-[11px]"
                        onClick={() => {
                          setQuestion(message.content);
                          composerRef.current?.focus();
                        }}
                      >
                        Ask again
                      </Button>
                    ) : null}
                  </li>
                ))}
              </ol>
              <p className="border-t px-4 py-2.5 text-[11px] leading-relaxed text-muted-foreground">
                A stored message keeps the answer text and the query id. Ask the question again to rebuild the full
                evidence set, or inspect the stored query record in{" "}
                <Link to="/admin" className="underline hover:text-foreground">
                  Administration
                </Link>
                .
              </p>
            </section>
          ) : null}

          {!answer && !streaming && events.length === 0 && !transcript.data ? (
            <EmptyState
              title="No question run yet"
              description="Answers arrive with the pages they were built from, a verification outcome and any conflict found between contract versions. When the corpus does not answer a question, it says so instead of guessing."
            />
          ) : null}
        </div>

        {/* Evidence */}
        <aside aria-label="Evidence" className="min-w-0 xl:border-l xl:pl-5">
          {answer ? (
            <EvidencePanel
              answer={answer}
              showTrace={includeTrace}
              detailsOpen={detailsOpen}
              onDetailsOpenChange={setDetailsOpen}
            />
          ) : (
            <div className="space-y-4 text-xs leading-relaxed text-muted-foreground">
              <div>
                <h2 className="text-[10px] font-medium uppercase tracking-[0.16em] text-subtle">Evidence</h2>
                <p className="mt-2">{microcopyPlain("readingDocuments")}</p>
              </div>
              <ol className="space-y-3 border-t border-white/[0.07] pt-3">
                {[
                  { title: "Passages", body: "Each cited passage names its document, page, section and clause." },
                  { title: "Verification", body: "Every claim is checked against those passages; unsupported text is withdrawn." },
                  { title: "Retrieval steps", body: "The candidates each search contributed, and how the question was read." },
                ].map((item, index) => (
                  <li key={item.title} className="flex gap-2.5">
                    <span className="tnum mt-px text-[10px] text-subtle">{String(index + 1).padStart(2, "0")}</span>
                    <span>
                      <span className="block font-medium text-foreground">{item.title}</span>
                      {item.body}
                    </span>
                  </li>
                ))}
              </ol>
              <p className="border-t border-white/[0.07] pt-3">
                Citations are links: opening one loads the viewer on the cited page with the passage highlighted.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
