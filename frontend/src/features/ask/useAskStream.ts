import { useCallback, useEffect, useReducer, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { streamQuery } from "@/lib/api";
import type { Answer, Citation, StreamEvent } from "@/lib/types";

type PipelineEvent = NonNullable<StreamEvent["event"]>;

export interface AskPayload {
  query: string;
  strategy?: string | null;
  top_k?: number | null;
  max_iterations?: number | null;
  filters?: Record<string, unknown>;
  include_trace?: boolean;
}

interface AskState {
  conversationId: string | null;
  events: PipelineEvent[];
  /** Retrieved passages, shown while the answer is still being verified. */
  evidence: Citation[];
  answer: Answer | null;
  error: unknown;
  streaming: boolean;
}

type Action =
  | { type: "start" }
  | { type: "status"; event: PipelineEvent }
  | { type: "evidence"; evidence: Citation[] }
  | { type: "answer"; answer: Answer }
  | { type: "error"; error: unknown }
  | { type: "settled" }
  | { type: "open"; conversationId: string }
  | { type: "reset" };

const INITIAL: AskState = {
  conversationId: null,
  events: [],
  evidence: [],
  answer: null,
  error: null,
  streaming: false,
};

export function askReducer(state: AskState, action: Action): AskState {
  switch (action.type) {
    case "start":
      return { ...state, events: [], evidence: [], answer: null, error: null, streaming: true };
    case "status":
      return { ...state, events: [...state.events, action.event] };
    case "evidence":
      return { ...state, evidence: action.evidence };
    case "answer":
      return {
        ...state,
        answer: action.answer,
        // The server creates the conversation when it persists the answer, so
        // the first question adopts the id it returns instead of pre-creating an
        // empty conversation that a failure would leave behind.
        conversationId: action.answer.conversation_id ?? state.conversationId,
        streaming: false,
      };
    case "error":
      return { ...state, error: action.error, streaming: false };
    case "settled":
      return { ...state, streaming: false };
    case "open":
      return { ...INITIAL, conversationId: action.conversationId };
    case "reset":
      return { ...INITIAL };
    default:
      return state;
  }
}

/**
 * Owns the Ask page's stream: reducer state, abort, and cache invalidation.
 *
 * The page keeps only composer inputs; everything that describes an in-flight or
 * completed query lives here so the streaming rules are testable without a DOM.
 */
export function useAskStream() {
  const [state, dispatch] = useReducer(askReducer, INITIAL);
  const controllerRef = useRef<AbortController | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    return () => controllerRef.current?.abort();
  }, []);

  const stop = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    dispatch({ type: "settled" });
  }, []);

  const reset = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    dispatch({ type: "reset" });
  }, []);

  const openConversation = useCallback((conversationId: string) => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    dispatch({ type: "open", conversationId });
  }, []);

  const ask = useCallback(
    async (payload: AskPayload) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      dispatch({ type: "start" });

      let answeredConversation: string | null = null;
      try {
        await streamQuery(
          { ...payload, conversation_id: state.conversationId },
          (event: StreamEvent) => {
            if (event.type === "status" && event.event) {
              dispatch({ type: "status", event: event.event });
            } else if (event.type === "evidence" && event.evidence) {
              dispatch({ type: "evidence", evidence: event.evidence });
            } else if (event.type === "answer" && event.answer) {
              answeredConversation = event.answer.conversation_id ?? state.conversationId;
              dispatch({ type: "answer", answer: event.answer });
            } else if (event.type === "error") {
              dispatch({
                type: "error",
                error: new Error(event.error?.message ?? "The pipeline could not finish this query."),
              });
            }
          },
          controller.signal,
        );
      } catch (caught) {
        if ((caught as Error).name !== "AbortError") dispatch({ type: "error", error: caught });
      } finally {
        dispatch({ type: "settled" });
        if (controllerRef.current === controller) controllerRef.current = null;
      }

      if (answeredConversation) {
        void queryClient.invalidateQueries({ queryKey: ["conversations"] });
        void queryClient.invalidateQueries({ queryKey: ["conversation-messages", answeredConversation] });
      }
    },
    [queryClient, state.conversationId],
  );

  return {
    ...state,
    verifying: state.streaming && state.evidence.length > 0 && !state.answer,
    ask,
    stop,
    reset,
    openConversation,
  };
}
