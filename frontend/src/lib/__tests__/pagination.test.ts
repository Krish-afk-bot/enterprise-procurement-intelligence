import { describe, expect, it } from "vitest";

import { PAGE_SIZE, clampPage, offsetFor, pageCount, pageLabel } from "../pagination";

describe("pagination", () => {
  it("treats an empty result as one empty page", () => {
    expect(pageCount(0)).toBe(1);
    expect(pageLabel(0, 0)).toBe("Page 1 of 1");
  });

  it("rounds a partial last page up", () => {
    expect(pageCount(1)).toBe(1);
    expect(pageCount(PAGE_SIZE)).toBe(1);
    expect(pageCount(PAGE_SIZE + 1)).toBe(2);
    expect(pageCount(PAGE_SIZE * 3 + 7)).toBe(4);
  });

  it("computes offsets from a zero-based page", () => {
    expect(offsetFor(0)).toBe(0);
    expect(offsetFor(2)).toBe(2 * PAGE_SIZE);
  });

  it("clamps a page past the end instead of requesting nothing", () => {
    expect(clampPage(99, PAGE_SIZE * 2)).toBe(1);
    expect(clampPage(-4, PAGE_SIZE * 2)).toBe(0);
    expect(clampPage(Number.NaN, 10)).toBe(0);
  });

  it("clamps before formatting the label", () => {
    expect(pageLabel(9, PAGE_SIZE + 1)).toBe("Page 2 of 2");
  });

  it("normalises a non-positive page size to one", () => {
    expect(pageCount(10, 0)).toBe(10);
    expect(offsetFor(3, 0)).toBe(3);
  });
});
