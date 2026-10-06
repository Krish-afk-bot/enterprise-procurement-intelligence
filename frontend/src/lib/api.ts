/**
 * Typed API client.
 *
 * In development the browser calls the same origin and Vite proxies `/api` to
 * the backend, so there is no CORS configuration to get wrong. Only the API base
 * URL is ever read from the environment. No secrets reach the bundle.
 */
import type {
  AccessModel,
  Answer,
  AuditEntry,
  ChunkOut,
  Compliance,
  Comparison,
  Contract,
  ContractDetail,
  Conversation,
  ConversationMessage,
  DashboardStats,
  DocumentDetail,
  DocumentMetadataUpdate,
  DocumentSummary,
  DocumentVersion,
  EvaluationRun,
  ExperimentInfo,
  FilterOptions,
  GoldenQuestion,
  GraphOverview,
  HealthResponse,
  IndexingSummary,
  MeResponse,
  ModelConfig,
  Page,
  PageOut,
  Price,
  ReadyResponse,
  RoutingRow,
  SearchResponse,
  StreamEvent,
  Supplier,
  SupplierDetail,
  TokenResponse,
  TraceEntry,
  UploadLimits,
  UploadResponse,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const PREFIX = "/api/v1";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("accept", "application/json");
  if (init.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  if (accessToken) {
    headers.set("authorization", `Bearer ${accessToken}`);
  }
  const response = await fetch(`${BASE}${PREFIX}${path}`, { ...init, headers });
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  const payload = text ? safeJson(text) : null;
  if (!response.ok) {
    const detail = (payload as { detail?: unknown })?.detail ?? payload;
    const message =
      typeof detail === "string"
        ? detail
        : (detail as { message?: string })?.message ?? `Request failed with ${response.status}`;
    throw new ApiError(message, response.status, detail);
  }
  return payload as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function query(params: Record<string, unknown> | undefined): string {
  if (!params) return "";
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    if (Array.isArray(value)) {
      value.forEach((item) => search.append(key, String(item)));
    } else {
      search.set(key, String(value));
    }
  });
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export const api = {
  // --------------------------------------------------------------- system
  health: () => request<HealthResponse>("/health"),
  ready: () => request<ReadyResponse>("/ready"),

  // ----------------------------------------------------------------- auth
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (email: string, password: string, fullName: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name: fullName }),
    }),
  me: () => request<MeResponse>("/auth/me"),
  logout: () => request<void>("/auth/logout", { method: "POST" }),

  // ---------------------------------------------------------------- query
  ask: (payload: {
    query: string;
    conversation_id?: string | null;
    filters?: Record<string, unknown>;
    strategy?: string | null;
    top_k?: number | null;
    max_iterations?: number | null;
    include_trace?: boolean;
  }) => request<Answer>("/query", { method: "POST", body: JSON.stringify(payload) }),
  search: (payload: {
    query: string;
    mode?: string;
    limit?: number;
    rerank?: boolean;
    filters?: Record<string, unknown>;
  }) => request<SearchResponse>("/search", { method: "POST", body: JSON.stringify(payload) }),
  filters: () => request<FilterOptions>("/filters"),

  conversations: (params?: { limit?: number; offset?: number }) =>
    request<Page<Conversation>>(`/conversations${query(params)}`),
  createConversation: (title?: string) =>
    request<Conversation>(`/conversations${query({ title })}`, { method: "POST" }),
  conversationMessages: (id: string, params?: { limit?: number }) =>
    request<Page<ConversationMessage>>(`/conversations/${id}/messages${query(params)}`),

  // ---------------------------------------------------------- procurement
  suppliers: (params?: { search?: string; limit?: number; offset?: number }) =>
    request<Page<Supplier>>(`/suppliers${query(params)}`),
  supplier: (id: string) => request<SupplierDetail>(`/suppliers/${id}`),
  contracts: (params?: { search?: string; supplier_id?: string; limit?: number; offset?: number }) =>
    request<Page<Contract>>(`/contracts${query(params)}`),
  contract: (id: string) => request<ContractDetail>(`/contracts/${id}`),
  products: (params?: { search?: string; limit?: number }) =>
    request<Page<{ id: string; sku: string; name: string; category: string | null; price_count: number }>>(
      `/products${query(params)}`,
    ),
  prices: (params?: {
    supplier_id?: string;
    product_id?: string;
    contract_id?: string;
    as_of?: string;
    current_only?: boolean;
    limit?: number;
  }) => request<Page<Price>>(`/prices${query(params)}`),
  compliance: (params?: { supplier_id?: string; limit?: number }) =>
    request<Page<Compliance>>(`/compliance${query(params)}`),
  compare: (payload: {
    supplier_ids?: string[];
    supplier_names?: string[];
    product_ids?: string[];
    product_query?: string | null;
    dimensions?: string[];
    as_of?: string | null;
  }) => request<Comparison>("/compare", { method: "POST", body: JSON.stringify(payload) }),

  // -------------------------------------------------------------- documents
  documents: (params?: {
    search?: string;
    status?: string;
    document_type?: string;
    supplier_id?: string;
    contract_id?: string;
    include_synthetic?: boolean;
    limit?: number;
    offset?: number;
  }) => request<Page<DocumentSummary>>(`/documents${query(params)}`),
  document: (id: string) => request<DocumentDetail>(`/documents/${id}`),
  /** Version history for a document, oldest first. */
  documentVersions: (id: string) => request<DocumentVersion[]>(`/documents/${id}/versions`),
  /** Persist a metadata edit on the document row. */
  updateDocument: (id: string, payload: DocumentMetadataUpdate) =>
    request<DocumentSummary>(`/documents/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  documentPage: (id: string, page: number) => request<PageOut>(`/documents/${id}/pages/${page}`),
  documentChunks: (id: string, params?: { page?: number; content_type?: string; limit?: number; offset?: number }) =>
    request<Page<ChunkOut>>(`/documents/${id}/chunks${query(params)}`),
  uploadLimits: () => request<UploadLimits>("/documents/limits"),
  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  uploadDocument: async (
    file: File,
    options: {
      document_type?: string;
      supplier_name?: string;
      title?: string;
      revision_label?: string;
      effective_date?: string;
      expiry_date?: string;
      is_synthetic?: boolean;
      /** Upload this file as the next version of an existing document. */
      replaces_document_id?: string;
    } = {},
  ) => {
    const form = new FormData();
    form.append("file", file);
    if (options.document_type) form.append("document_type", options.document_type);
    if (options.supplier_name) form.append("supplier_name", options.supplier_name);
    if (options.title) form.append("title", options.title);
    if (options.revision_label) form.append("revision_label", options.revision_label);
    if (options.effective_date) form.append("effective_date", options.effective_date);
    if (options.expiry_date) form.append("expiry_date", options.expiry_date);
    if (options.replaces_document_id) form.append("replaces_document_id", options.replaces_document_id);
    form.append("is_synthetic", String(options.is_synthetic ?? false));
    const headers = new Headers();
    if (accessToken) headers.set("authorization", `Bearer ${accessToken}`);
    const response = await fetch(`${BASE}${PREFIX}/documents/upload`, { method: "POST", body: form, headers });
    const text = await response.text();
    const payload = text ? safeJson(text) : null;
    if (!response.ok) {
      const detail = (payload as { detail?: unknown })?.detail ?? payload;
      const message =
        typeof detail === "string"
          ? detail
          : (detail as { message?: string })?.message ?? `Upload failed with ${response.status}`;
      throw new ApiError(message, response.status, detail);
    }
    return payload as UploadResponse;
  },
  reindexDocument: (id: string) => request<Record<string, unknown>>(`/documents/${id}/index`, { method: "POST" }),
  pageImageUrl: (documentId: string, page: number) => `${BASE}${PREFIX}/documents/${documentId}/pages/${page}/image`,

  // ----------------------------------------------------------------- graph
  graphOverview: () => request<GraphOverview>("/graph/overview"),
  graphNodes: (label: string, nameContains?: string) =>
    request<{ label: string; items: { label: string; key: string; properties: Record<string, unknown> }[]; total: number }>(
      `/graph/nodes${query({ label, name_contains: nameContains })}`,
    ),
  graphPaths: (label: string, key: string, maxHops = 2) =>
    request<{
      root: { label: string; key: string };
      hops: number;
      nodes: { label: string; key: string }[];
      edges: { type: string; start: { label: string; key: string }; end: { label: string; key: string } }[];
      total_edges: number;
    }>(`/graph/paths${query({ label, key, max_hops: maxHops })}`),

  // ------------------------------------------------------------ evaluation
  experiments: () => request<ExperimentInfo[]>("/evaluation/experiments"),
  evaluationDataset: () =>
    request<{ name: string; version: string; question_count: number; categories: string[]; unanswerable_count: number; questions: GoldenQuestion[] }>(
      "/evaluation/dataset",
    ),
  evaluationRuns: (params?: { limit?: number; offset?: number }) =>
    request<Page<EvaluationRun>>(`/evaluation/runs${query(params)}`),
  evaluationRun: (id: string) => request<EvaluationRun>(`/evaluation/runs/${id}`),
  runEvaluation: (payload: { experiments: string[]; categories?: string[]; max_questions?: number; top_k?: number; name?: string }) =>
    request<EvaluationRun[]>("/evaluation/runs", { method: "POST", body: JSON.stringify(payload) }),
  deleteEvaluationRun: (id: string) => request<void>(`/evaluation/runs/${id}`, { method: "DELETE" }),

  // ----------------------------------------------------------------- admin
  stats: () => request<DashboardStats>("/admin/stats"),
  accessModel: () => request<AccessModel>("/admin/access-model"),
  modelConfig: () => request<ModelConfig>("/admin/config"),
  routing: () => request<RoutingRow[]>("/admin/routing"),
  indexing: () => request<IndexingSummary>("/admin/indexing"),
  audit: (params?: { limit?: number }) => request<Page<AuditEntry>>(`/admin/audit${query(params)}`),
  traces: (params?: { limit?: number }) => request<Page<TraceEntry>>(`/admin/traces${query(params)}`),
  queryDetail: (id: string) => request<Record<string, unknown>>(`/admin/queries/${id}`),
};

/**
 * Stream a query as server-sent events. Status events describe what the system
 * did (which engine ran, how many candidates came back); the final `answer`
 * event carries the verified answer.
 */
export async function streamQuery(
  payload: {
    query: string;
    strategy?: string | null;
    top_k?: number | null;
    max_iterations?: number | null;
    conversation_id?: string | null;
    filters?: Record<string, unknown>;
    include_trace?: boolean;
  },
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const headers = new Headers({ "content-type": "application/json", accept: "text/event-stream" });
  if (accessToken) headers.set("authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${BASE}${PREFIX}/query/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new ApiError("The answer stream could not be started.", response.status, null);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const data = line.slice(5).trim();
      if (data === "[DONE]") return;
      try {
        onEvent(JSON.parse(data) as StreamEvent);
      } catch {
        // A malformed frame is ignored rather than breaking the stream.
      }
    }
  }
}
