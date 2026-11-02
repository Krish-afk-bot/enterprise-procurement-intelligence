import { describe, expect, it } from "vitest";

import { askReducer } from "../useAskStream";
import type { Answer, Citation } from "@/lib/types";

const citation: Citation = {
  chunk_id: "chk_1",
  document_id: "doc_1",
  document_name: "supplier_a_amendment_2.pdf",
  document_type: "amendment",
  page: 1,
  section: "1. Price Revision",
  clause: null,
  snippet: "The unit price for Industrial Laptop X200 is revised to USD 874.00",
  source_uri: null,
  score: 0.9,
  rank: 1,
  evidence_type: "document",
  is_synthetic: true,
  verified: true,
  label: "supplier_a_amendment_2.pdf — p.1",
};

function answer(overrides: Partial<Answer> = {}): Answer {
  return {
    query_id: "qry_1",
    conversation_id: "cnv_1",
    answer_text: "The current unit price is USD 874.00.",
    status: "supported",
    generation_mode: "llm",
    model: "qwen2.5-coder:7b",
    prompt_version: "v1",
    evidence_strength: { level: "strong", method: "criteria_v1", criteria: {} },
    grounding: {
      method: "claim_binding_v1",
      supported_claims: 1,
      total_claims: 1,
      score: 1,
      unsupported_claims: [],
      details: {},
    },
    conflicts: [],
    citations: [citation],
    retrieval_steps: [],
    plan: {},
    validation: {},
    timings: {},
    token_usage: {},
    degraded: false,
    degradation_reasons: [],
    external_sources: [],
    notes: [],
    trace: [],
    ...overrides,
  };
}

describe("askReducer", () => {
  it("starts a run by clearing the previous answer and evidence", () => {
    const state = askReducer(
      {
        conversationId: "cnv_old",
        events: [{ node: "retrieve", event: "old", detail: "" }],
        evidence: [citation],
        answer: answer(),
        error: new Error("old"),
        streaming: false,
      },
      { type: "start" },
    );
    expect(state.answer).toBeNull();
    expect(state.evidence).toEqual([]);
    expect(state.events).toEqual([]);
    expect(state.error).toBeNull();
    expect(state.streaming).toBe(true);
    expect(state.conversationId).toBe("cnv_old");
  });

  it("appends status events and renders evidence before the answer", () => {
    let state = askReducer(
      { conversationId: null, events: [], evidence: [], answer: null, error: null, streaming: false },
      { type: "start" },
    );
    state = askReducer(state, { type: "status", event: { node: "retrieve", event: "Retrieved", detail: "10" } });
    state = askReducer(state, { type: "evidence", evidence: [citation] });
    expect(state.events).toHaveLength(1);
    expect(state.evidence).toHaveLength(1);
    expect(state.answer).toBeNull();
  });

  it("adopts the conversation created by a first successful answer", () => {
    const state = askReducer(
      { conversationId: null, events: [], evidence: [citation], answer: null, error: null, streaming: true },
      { type: "answer", answer: answer() },
    );
    expect(state.conversationId).toBe("cnv_1");
    expect(state.answer?.answer_text).toContain("874.00");
    expect(state.streaming).toBe(false);
  });

  it("keeps an existing conversation when the server does not return one", () => {
    const state = askReducer(
      { conversationId: "cnv_existing", events: [], evidence: [], answer: null, error: null, streaming: true },
      { type: "answer", answer: answer({ conversation_id: null }) },
    );
    expect(state.conversationId).toBe("cnv_existing");
  });

  it("records an error and stops streaming", () => {
    const state = askReducer(
      { conversationId: "cnv_1", events: [], evidence: [], answer: null, error: null, streaming: true },
      { type: "error", error: new Error("boom") },
    );
    expect((state.error as Error).message).toBe("boom");
    expect(state.streaming).toBe(false);
  });

  it("reset clears the conversation so a failed first run leaves nothing behind", () => {
    const state = askReducer(
      {
        conversationId: "cnv_1",
        events: [{ node: "start", event: "x", detail: "" }],
        evidence: [citation],
        answer: answer(),
        error: null,
        streaming: false,
      },
      { type: "reset" },
    );
    expect(state).toMatchObject({
      conversationId: null,
      events: [],
      evidence: [],
      answer: null,
      error: null,
      streaming: false,
    });
  });
});
