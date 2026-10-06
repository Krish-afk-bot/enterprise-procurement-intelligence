/** Types mirroring the backend schemas (`backend/app/schemas`). */

export type AnswerStatus = "supported" | "partial" | "insufficient_evidence" | "conflicting" | "error";
export type EvidenceLevel = "strong" | "moderate" | "limited" | "none";

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface ProviderStatus {
  kind: string;
  name: string;
  available: boolean;
  detail: string;
  model: string | null;
  attributes: Record<string, unknown>;
}

export interface FallbackNote {
  kind: string;
  requested: string;
  used: string;
  reason: string;
}

export interface HealthResponse {
  status: string;
  app_env: string;
  version: string;
  degraded: boolean;
  providers: Record<string, ProviderStatus>;
  fallbacks: FallbackNote[];
  capabilities: Record<string, boolean>;
  details: Record<string, unknown>;
}

export interface MeResponse {
  user_id: string;
  tenant_id: string;
  email: string;
  role: string;
  full_name: string;
  permissions: string[];
  access_ceiling: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
  expires_at?: string;
  user?: MeResponse;
}

/** Matches `app.security.injection.InjectionReport`. */
export interface InjectionReport {
  score: number;
  patterns: string[];
  suspicious: boolean;
}

export interface Citation {
  chunk_id: string | null;
  document_id: string | null;
  document_name: string | null;
  document_type: string | null;
  page: number | null;
  section: string | null;
  clause: string | null;
  snippet: string;
  source_uri: string | null;
  score: number | null;
  rank: number | null;
  evidence_type: string;
  is_synthetic: boolean;
  verified: boolean;
  /** Present only when the passage contains instruction-like text. */
  injection?: InjectionReport | null;
  label: string;
}

export interface EvidenceStrength {
  level: EvidenceLevel;
  method: string;
  criteria: Record<string, unknown>;
}

export interface Grounding {
  method: string;
  supported_claims: number;
  total_claims: number;
  score: number | null;
  unsupported_claims: string[];
  details: Record<string, unknown>;
}

export interface Conflict {
  kind: string;
  description: string;
  values: Record<string, unknown>[];
  resolution: string;
  preferred: Record<string, unknown> | null;
  citations: Citation[];
}

export interface RetrievalStep {
  name: string;
  status: string;
  detail: string;
  candidates: number;
  latency_ms: number | null;
  metadata: Record<string, unknown>;
}

export interface Answer {
  query_id: string;
  answer_text: string;
  status: AnswerStatus;
  generation_mode: string;
  model: string | null;
  prompt_version: string | null;
  evidence_strength: EvidenceStrength;
  grounding: Grounding;
  conflicts: Conflict[];
  citations: Citation[];
  retrieval_steps: RetrievalStep[];
  plan: Record<string, unknown>;
  validation: Record<string, unknown>;
  timings: Record<string, number>;
  token_usage: Record<string, number>;
  degraded: boolean;
  degradation_reasons: string[];
  external_sources: Record<string, unknown>[];
  notes: string[];
  trace: Record<string, unknown>[];
}

export interface QueryFilters {
  supplier_ids?: string[];
  contract_ids?: string[];
  document_ids?: string[];
  document_types?: string[];
  categories?: string[];
  regions?: string[];
  include_expired?: boolean;
  include_synthetic?: boolean;
}

export interface SearchHit {
  chunk_id: string;
  document_id: string;
  document_name: string;
  document_type: string | null;
  page: number | null;
  section: string | null;
  clause: string | null;
  content: string;
  content_type: string;
  score: number | null;
  dense_score: number | null;
  sparse_score: number | null;
  rerank_score: number | null;
  fused_score: number | null;
  rank: number | null;
  is_synthetic: boolean;
  access_level: string;
  effective_date: string | null;
  expiry_date: string | null;
  version: number;
  matched_by: string[];
}

export interface SearchResponse {
  query: string;
  mode: string;
  hits: SearchHit[];
  total: number;
  steps: RetrievalStep[];
  reranker: string | null;
  embedding_model: string | null;
}

export interface FilterOptions {
  suppliers: { id: string; name: string }[];
  products: { id: string; name: string; sku: string }[];
  contracts: { id: string; number: string }[];
  regions: string[];
  categories: string[];
  document_types: string[];
  strategies: string[];
  limits: Record<string, number>;
}

export interface Supplier {
  id: string;
  name: string;
  normalized_name: string;
  category: string | null;
  country: string | null;
  region: string | null;
  status: string;
  is_synthetic: boolean;
  source: string | null;
  source_url: string | null;
  license: string | null;
  attributes: Record<string, unknown>;
  contract_count: number;
  document_count: number;
  price_count: number;
}

export interface Contract {
  id: string;
  supplier_id: string | null;
  supplier_name: string | null;
  contract_number: string;
  title: string;
  contract_type: string | null;
  currency: string;
  total_value: number | null;
  effective_date: string | null;
  expiry_date: string | null;
  status: string;
  version: number;
  metadata_json: Record<string, unknown>;
  is_expired?: boolean;
  price_count?: number;
  amendment_count?: number;
}

export interface Price {
  id: string;
  supplier_id: string | null;
  supplier_name: string | null;
  contract_id: string | null;
  product_id: string | null;
  product_name: string | null;
  unit_price: number;
  currency: string;
  minimum_quantity: number | null;
  discount_percent: number | null;
  payment_terms: string | null;
  delivery_terms: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  amendment_ref: string | null;
  source_document_id: string | null;
  source_page: number | null;
  is_synthetic: boolean;
}

export interface Compliance {
  id: string;
  supplier_id: string;
  certificate_type: string;
  certificate_number: string | null;
  issued_date: string | null;
  expiry_date: string | null;
  status: string;
  scope: string | null;
  source_document_id: string | null;
  source_page: number | null;
}

export interface SupplierDetail extends Supplier {
  contracts: Contract[];
  products: { id: string; sku: string; name: string }[];
  prices: Price[];
  compliance: Compliance[];
  documents: DocumentSummary[];
  timeline: { date: string | null; kind: string; label: string; document_name: string | null; page: number | null }[];
  current_price: {
    unit_price: number;
    currency: string;
    product_name: string | null;
    effective_date: string | null;
    amendment_ref: string | null;
    document_name: string | null;
    page: number | null;
  } | null;
}

export interface ContractDetail extends Contract {
  prices: Price[];
  documents: (DocumentSummary & { version: number })[];
  versions: {
    id: string;
    contract_number: string;
    version: number;
    title: string;
    effective_date: string | null;
    expiry_date: string | null;
    status: string;
    relation: string;
  }[];
  clauses: {
    chunk_id: string;
    page: number | null;
    section: string | null;
    clause: string | null;
    content: string;
    content_type: string;
    document_id: string;
  }[];
  compliance: Compliance[];
}

export interface DocumentSummary {
  id: string;
  title: string;
  filename: string;
  document_type: string | null;
  status: string;
  stage?: string | null;
  progress?: number;
  access_level: string;
  is_synthetic?: boolean;
  size_bytes?: number;
  mime_type?: string | null;
  checksum?: string;
  version?: number;
  revision_label?: string | null;
  page_count?: number;
  chunk_count?: number;
  table_count?: number;
  scanned_page_count?: number;
  ocr_applied?: boolean;
  vision_applied?: boolean;
  effective_date: string | null;
  expiry_date: string | null;
  supplier_id?: string | null;
  contract_id?: string | null;
  source?: string | null;
  source_url?: string | null;
  source_uri?: string | null;
  license?: string | null;
  retrieved_at?: string | null;
  error_message?: string | null;
  created_at?: string;
  updated_at?: string | null;
  /** Set when a newer version of this document has been uploaded. */
  superseded_by_id?: string | null;
  /** Supplier and contract names resolved by the backend, never by the client. */
  supplier_name?: string | null;
  contract_number?: string | null;
}

/** One row of a document's version history (`GET /documents/{id}/versions`). */
export interface DocumentVersion extends DocumentSummary {
  /** True for the version that currently governs. */
  is_current: boolean;
}

/** A table extracted from a page, with the page it was extracted from. */
export interface TableOut {
  id: string;
  page_number: number;
  table_index: number;
  caption: string | null;
  headers: unknown[];
  rows: unknown[];
  coordinates: unknown[];
  extraction_method: string;
  complexity_score: number;
  markdown: string;
  chunk_id: string | null;
}

export interface PageOut {
  id: string;
  page_number: number;
  width: number | null;
  height: number | null;
  has_text_layer: boolean;
  is_scanned: boolean;
  needs_vision: boolean;
  extraction_method: string;
  raw_text: string | null;
  ocr_text: string | null;
  vision_summary: string | null;
  image_url: string | null;
  char_count: number;
  tables: TableOut[];
}

export interface IngestionJob {
  id: string;
  document_id: string;
  status: string;
  stage: string | null;
  progress: number;
  attempts: number;
  error_message: string | null;
  stages_completed: unknown[];
  metrics: Record<string, unknown>;
  queued_at: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface DocumentDetail extends DocumentSummary {
  pages: PageOut[];
  job: IngestionJob | null;
  chunk_type_counts: Record<string, number>;
  /** Display name of the account that uploaded the file, when it still exists. */
  uploaded_by_name?: string | null;
}

/** Fields a person may change on a document. Omitted fields are left untouched. */
export interface DocumentMetadataUpdate {
  title?: string;
  document_type?: string;
  supplier_id?: string | null;
  contract_id?: string | null;
  effective_date?: string | null;
  expiry_date?: string | null;
  access_level?: string;
  revision_label?: string | null;
}

export interface ChunkOut {
  id: string;
  document_id: string;
  page_number: number | null;
  parent_chunk_id: string | null;
  chunk_index: number;
  section: string | null;
  subsection: string | null;
  clause: string | null;
  content: string;
  contextual_content: string | null;
  content_type: string;
  token_count: number;
  supplier_id: string | null;
  contract_id: string | null;
  document_type: string | null;
  version: number;
  effective_date: string | null;
  expiry_date: string | null;
  access_level: string;
  is_synthetic: boolean;
  table_id: string | null;
  embedding_indexed: boolean;
}

export interface UploadLimits {
  max_upload_mb: number;
  allowed_extensions: string[];
  supported_mime_types: string[];
}

export interface UploadResponse {
  document: DocumentSummary;
  job: IngestionJob | null;
  duplicate_of: string | null;
  message: string;
}

export interface Conversation {
  id: string;
  title: string;
  summary?: string | null;
  message_count: number;
}

export interface ConversationMessage {
  id: string;
  role: string;
  content: string;
  query_id: string | null;
  created_at: string | null;
}

export interface ComparisonCell {
  key: string;
  value: unknown;
  formatted: string;
  source: string;
  citations: Citation[];
  notes: string[];
}

export interface Comparison {
  dimensions: string[];
  columns: { supplier_id: string | null; supplier_name: string; cells: Record<string, ComparisonCell> }[];
  product: Record<string, unknown> | null;
  generated_at: string | null;
  notes: string[];
  unresolved: string[];
}

export interface ExperimentInfo {
  name: string;
  description: string;
  requires: string[];
  runnable: boolean;
  unavailable_reason: string | null;
}

export interface GoldenQuestion {
  id: string;
  question: string;
  category: string;
  difficulty: string;
  expected_answer: string | null;
  expected_documents: string[];
  expected_pages: number[];
  expected_keywords: string[];
  is_unanswerable: boolean;
  notes: string | null;
}

export interface MetricSummary {
  name: string;
  value: number | null;
  count: number;
  display: string;
  description: string;
}

export interface EvaluationRun {
  id: string;
  name: string;
  experiment: string;
  dataset_name: string | null;
  status: string;
  question_count: number;
  summary: Record<string, unknown>;
  metrics: MetricSummary[];
  config: Record<string, unknown>;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
  results?: EvaluationResult[];
}

export interface EvaluationResult {
  id: string;
  question_id: string;
  question: string;
  category: string | null;
  difficulty: string | null;
  expected_answer: string | null;
  answer_text: string | null;
  answer_status: string | null;
  retrieved_document_ids: string[];
  retrieved_pages: number[];
  metrics: Record<string, unknown>;
  latency_ms: number | null;
  error: string | null;
}

/** The access model the API enforces (`GET /admin/access-model`). */
export interface AccessModel {
  roles: string[];
  permissions: string[];
  role_permissions: Record<string, string[]>;
  role_access_ceiling: Record<string, string>;
  access_levels: string[];
  note: string;
}

export interface ModelConfig {
  llm_provider: string;
  llm_model: string | null;
  llm_configured: boolean;
  llm_base_url_host: string | null;
  small_llm_model: string | null;
  vlm_model: string | null;
  vlm_configured: boolean;
  embedding_provider: string;
  embedding_model: string;
  embedding_device: string | null;
  reranker_provider: string;
  reranker_model: string | null;
  reranker_enabled: boolean;
  ocr_enabled: boolean;
  vision_escalation_enabled: boolean;
  max_agent_iterations: number;
  notes: string[];
}

export interface RoutingRow {
  task: string;
  engine: string;
  model: string | null;
  reason: string;
}

export interface DashboardStats {
  documents_indexed: number;
  documents_pending: number;
  documents_failed: number;
  pages: number;
  chunks: number;
  chunks_embedded: number;
  tables: number;
  scanned_pages: number;
  suppliers: number;
  contracts: number;
  products: number;
  prices: number;
  compliance_certificates: number;
  queries_total: number;
  queries_insufficient_evidence: number;
  evaluation_runs: number;
  graph_nodes: number;
  graph_edges: number;
  synthetic_documents: number;
  breakdown: { label: string; value: number; detail: string | null }[];
  notes: string[];
}

export interface GraphOverview {
  provider: string;
  available: boolean;
  detail: string;
  nodes_total: number;
  edges_total: number;
  nodes_by_label: Record<string, number>;
  edges_by_type: Record<string, number>;
  notes: string[];
}

export interface StreamEvent {
  type: "status" | "answer" | "error";
  event?: { node: string; event: string; detail: string; data?: Record<string, unknown> };
  answer?: Answer;
  error?: { code: string; message: string };
}

/** Result row returned by the retry-free acceptance script endpoints. */
export interface ReadyResponse {
  ready: boolean;
  database: boolean;
  blocking: string[];
}

export interface IndexingSummary {
  queued?: number;
  running?: number;
  succeeded?: number;
  failed?: number;
  notes?: string[];
  [key: string]: unknown;
}

export interface AuditEntry {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  outcome: string | null;
  request_id: string | null;
  created_at: string | null;
  [key: string]: unknown;
}

export interface TraceEntry {
  id: string;
  query_id: string | null;
  duration_ms: number | null;
  iterations: number | null;
  events: { node: string; event: string; detail: string }[];
  created_at: string | null;
  [key: string]: unknown;
}
