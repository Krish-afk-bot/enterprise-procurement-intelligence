import { titleCase } from "@/lib/utils";

/** Real ingestion stages, in the order the pipeline reports them. */
export const STAGE_LABELS: Record<string, string> = {
  load: "Document received",
  parse: "Document read",
  ocr: "Scanned pages read",
  vision: "Page imagery read",
  layout: "Layout analysed",
  chunk: "Sections identified",
  persist_chunks: "Sections stored",
  vector_index: "Added to the search index",
  structured_and_graph: "Prices, contracts and relationships identified",
  indexed: "Ready to search",
  indexed_without_embeddings: "Ready to search (keyword index only)",
  failed: "Processing failed",
};

/** The stages the pipeline reports, in order, for the progress view. */
export const PIPELINE_ORDER = [
  "load",
  "parse",
  "ocr",
  "layout",
  "chunk",
  "persist_chunks",
  "vector_index",
  "structured_and_graph",
  "indexed",
];

export function stageLabel(stage: string | null | undefined): string {
  if (!stage) return "not reported";
  return STAGE_LABELS[stage] ?? titleCase(stage);
}
