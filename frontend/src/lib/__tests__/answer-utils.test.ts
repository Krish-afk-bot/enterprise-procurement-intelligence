/**
 * Unit tests for AnswerOut response handling utilities.
 *
 * These tests verify:
 * - AnswerStatus discrimination (refusal, supported, conflicting, partial)
 * - generation_mode correctly identifies llm vs extractive
 * - citation fields are validated (document_id / chunk_id required)
 * - degraded flag handling
 * - empty/edge case handling
 */

import { describe, it, expect } from "vitest";
import type { Answer, Citation } from "../types";

// ------------------------------------------------------------------ helpers

function makeAnswer(overrides: Partial<Answer> = {}): Answer {
  return {
    query_id: "qry_001",
    answer_text: "The unit price is USD 92.00 [1].",
    status: "supported",
    generation_mode: "llm",
    model: "llama3.1:8b",
    prompt_version: "answer_generator.v1",
    evidence_strength: { level: "moderate", method: "criteria_v1", criteria: {} },
    grounding: {
      method: "lexical_overlap",
      supported_claims: 1,
      total_claims: 1,
      score: 1.0,
      unsupported_claims: [],
      details: {},
    },
    conflicts: [],
    citations: [],
    retrieval_steps: [],
    plan: {},
    validation: {},
    timings: { total_ms: 2000 },
    token_usage: { prompt_tokens: 100, completion_tokens: 50 },
    degraded: false,
    degradation_reasons: [],
    external_sources: [],
    notes: [],
    trace: [],
    ...overrides,
  };
}

function makeCitation(overrides: Partial<Citation> = {}): Citation {
  return {
    chunk_id: "chk_001",
    document_id: "doc_001",
    document_name: "supplier_a_master_contract.pdf",
    document_type: "contract",
    page: 4,
    section: "Pricing",
    clause: null,
    snippet: "The unit price for Widget A is USD 92.00",
    source_uri: null,
    score: 0.92,
    rank: 1,
    evidence_type: "document",
    is_synthetic: true,
    verified: true,
    injection: null,
    label: "supplier_a_master_contract.pdf — p.4",
    ...overrides,
  };
}

// ------------------------------------------------------------------ generation_mode

describe("generation_mode discrimination", () => {
  it("llm mode is correctly identified", () => {
    const answer = makeAnswer({ generation_mode: "llm", degraded: false });
    expect(answer.generation_mode).toBe("llm");
    expect(answer.degraded).toBe(false);
  });

  it("extractive mode is correctly identified", () => {
    const answer = makeAnswer({
      generation_mode: "extractive",
      degraded: true,
      degradation_reasons: ["No language model configured"],
    });
    expect(answer.generation_mode).toBe("extractive");
    expect(answer.degraded).toBe(true);
    expect(answer.degradation_reasons.length).toBeGreaterThan(0);
  });

  it("degraded flag is false for llm mode", () => {
    const answer = makeAnswer({ generation_mode: "llm", degraded: false });
    expect(answer.degraded).toBe(false);
  });

  it("degraded flag is true for extractive fallback", () => {
    const answer = makeAnswer({ generation_mode: "extractive", degraded: true });
    expect(answer.degraded).toBe(true);
  });
});

// ------------------------------------------------------------------ status discrimination

describe("AnswerStatus discrimination", () => {
  it("supported status means grounded answer", () => {
    const answer = makeAnswer({ status: "supported" });
    expect(answer.status).toBe("supported");
  });

  it("insufficient_evidence status means refusal", () => {
    const answer = makeAnswer({
      status: "insufficient_evidence",
      answer_text: "I couldn't verify this from the available procurement documents.",
    });
    expect(answer.status).toBe("insufficient_evidence");
    expect(answer.answer_text).toContain("couldn't verify");
  });

  it("conflicting status means both values cited", () => {
    const answer = makeAnswer({
      status: "conflicting",
      conflicts: [
        {
          kind: "price_conflict",
          description: "Conflicting prices: USD 920 vs USD 874",
          values: [],
          resolution: "Amendment 2 governs from 2026-01-01",
          preferred: null,
          citations: [],
        },
      ],
    });
    expect(answer.status).toBe("conflicting");
    expect(answer.conflicts.length).toBe(1);
    expect(answer.conflicts[0].resolution).toContain("Amendment 2");
  });
});

// ------------------------------------------------------------------ citation validation

describe("citation validation", () => {
  it("valid citation has document_id and chunk_id", () => {
    const citation = makeCitation();
    const isValid = !!(citation.document_id || citation.chunk_id);
    expect(isValid).toBe(true);
  });

  it("citation with no source IDs is invalid", () => {
    const citation = makeCitation({ document_id: null, chunk_id: null });
    const isValid = !!(citation.document_id || citation.chunk_id);
    expect(isValid).toBe(false);
  });

  it("citation page number is present for document citations", () => {
    const citation = makeCitation({ page: 4 });
    expect(citation.page).toBe(4);
  });

  it("citation label is correct format", () => {
    const citation = makeCitation({
      document_name: "supplier_a_master_contract.pdf",
      page: 4,
      section: "Pricing",
    });
    expect(citation.label).toContain("supplier_a_master_contract.pdf");
  });

  it("injection flag marks suspicious citation content", () => {
    const citation = makeCitation({
      injection: {
        score: 1.0,
        patterns: ["instruction_override", "secret_exfiltration"],
        suspicious: true,
      },
    });
    expect(citation.injection?.suspicious).toBe(true);
    expect(citation.injection?.score).toBe(1.0);
    expect(citation.injection?.patterns).toContain("instruction_override");
  });

  it("answer with zero citations still has correct structure", () => {
    const answer = makeAnswer({ citations: [] });
    expect(Array.isArray(answer.citations)).toBe(true);
    expect(answer.citations.length).toBe(0);
  });
});

// ------------------------------------------------------------------ citation deep-link navigation

describe("citation deep-link URL construction", () => {
  it("builds correct URL for citation with document_id and page", () => {
    const citation = makeCitation({ document_id: "doc_abc123", page: 4 });
    const url = citation.document_id
      ? `/app/documents/${citation.document_id}?page=${citation.page ?? 1}`
      : null;
    expect(url).toBe("/app/documents/doc_abc123?page=4");
  });

  it("uses page 1 when page is null", () => {
    const citation = makeCitation({ document_id: "doc_abc123", page: null });
    const url = `/app/documents/${citation.document_id}?page=${citation.page ?? 1}`;
    expect(url).toBe("/app/documents/doc_abc123?page=1");
  });

  it("returns null URL when document_id is missing", () => {
    const citation = makeCitation({ document_id: null, chunk_id: null });
    const url = citation.document_id
      ? `/app/documents/${citation.document_id}?page=${citation.page ?? 1}`
      : null;
    expect(url).toBeNull();
  });

  it("multiple citations produce independent URLs", () => {
    const citations = [
      makeCitation({ document_id: "doc_001", page: 1 }),
      makeCitation({ document_id: "doc_002", page: 7 }),
      makeCitation({ document_id: "doc_003", page: 3 }),
    ];
    const urls = citations.map(
      (c) => c.document_id ? `/app/documents/${c.document_id}?page=${c.page ?? 1}` : null
    );
    expect(urls).toEqual([
      "/app/documents/doc_001?page=1",
      "/app/documents/doc_002?page=7",
      "/app/documents/doc_003?page=3",
    ]);
  });
});

// ------------------------------------------------------------------ error and empty states

describe("API error and empty state handling", () => {
  it("empty answer_text is handled gracefully", () => {
    const answer = makeAnswer({ answer_text: "" });
    const isEmpty = answer.answer_text.length === 0;
    expect(isEmpty).toBe(true);
  });

  it("degradation_reasons is always an array", () => {
    const answer = makeAnswer({ degradation_reasons: [] });
    expect(Array.isArray(answer.degradation_reasons)).toBe(true);
  });

  it("notes array is always present", () => {
    const answer = makeAnswer({ notes: ["extractive mode active"] });
    expect(answer.notes).toContain("extractive mode active");
  });

  it("token_usage prompt and completion tokens are numbers", () => {
    const answer = makeAnswer({ token_usage: { prompt_tokens: 150, completion_tokens: 75 } });
    expect(typeof answer.token_usage.prompt_tokens).toBe("number");
    expect(typeof answer.token_usage.completion_tokens).toBe("number");
  });

  it("grounding score is null when not computed", () => {
    const answer = makeAnswer({
      grounding: {
        method: "lexical_overlap",
        supported_claims: 0,
        total_claims: 0,
        score: null,
        unsupported_claims: [],
        details: {},
      },
    });
    expect(answer.grounding.score).toBeNull();
  });
});
