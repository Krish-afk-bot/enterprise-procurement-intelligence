/**
 * Compatibility shim.
 *
 * The product's copy has one home: `frontend/src/content/microcopy.ts`. This module
 * only re-exports it so the call sites written before the move keep resolving.
 */
import { MICROCOPY as LINES, type MicrocopyKey as Kind, plain, say } from "@/content/microcopy";

export const MICROCOPY = {
  readingDocuments: LINES.loading.say,
  evidenceFound: LINES.found.say,
  conflict: LINES.conflict.say,
  unsupported: LINES.unsupported.say,
  emptySearch: LINES.emptySearch.say,
  needTwoSuppliers: LINES.needTwo.say,
  noDocuments: LINES.noDocuments.say,
  indexed: LINES.indexed.say,
  singleVersion: LINES.singleVersion.say,
  loadingScene: LINES.loadingScene.say,
  processing: LINES.processing.say,
} as const;

/** The names this shim exposes, mapped onto the centralized keys. */
export type MicrocopyKey = keyof typeof MICROCOPY;

const KEY_OF: Record<MicrocopyKey, Kind> = {
  readingDocuments: "loading",
  evidenceFound: "found",
  conflict: "conflict",
  unsupported: "unsupported",
  emptySearch: "emptySearch",
  needTwoSuppliers: "needTwo",
  noDocuments: "noDocuments",
  indexed: "indexed",
  singleVersion: "singleVersion",
  loadingScene: "loadingScene",
  processing: "processing",
};

/**
 * The plain sentence that accompanies a line. Keeping both halves in one place means
 * a line cannot be shipped without the statement it is decorating.
 */
export function microcopyPlain(key: MicrocopyKey): string {
  return plain(KEY_OF[key]);
}

export { say, plain };
