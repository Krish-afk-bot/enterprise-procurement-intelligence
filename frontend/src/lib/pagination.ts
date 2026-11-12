/** Offset pagination maths for the list screens.
 *
 * The API accepts `limit`/`offset`, so paging is done on the server. These
 * helpers keep the UI consistent and make the edge cases testable: a total of
 * zero still has one (empty) page, and a page past the end is clamped rather
 * than requesting a range the server will answer with nothing.
 */

export const PAGE_SIZE = 25;

export function pageCount(total: number, size: number = PAGE_SIZE): number {
  if (!Number.isFinite(total) || total <= 0) return 1;
  return Math.max(1, Math.ceil(total / Math.max(1, size)));
}

export function clampPage(page: number, total: number, size: number = PAGE_SIZE): number {
  const last = pageCount(total, size) - 1;
  if (!Number.isFinite(page)) return 0;
  return Math.min(Math.max(0, Math.trunc(page)), last);
}

export function offsetFor(page: number, size: number = PAGE_SIZE): number {
  return Math.max(0, Math.trunc(page)) * Math.max(1, size);
}

/** Human label for a page, 1-based, e.g. "Page 2 of 7". */
export function pageLabel(page: number, total: number, size: number = PAGE_SIZE): string {
  return `Page ${clampPage(page, total, size) + 1} of ${pageCount(total, size)}`;
}
