/**
 * Accessibility and visual-regression checks for the main pages.
 *
 * Prerequisites are the same as the other E2E specs: the backend on :8000, the
 * frontend on :5173 and the seeded admin account. Baselines for the visual
 * snapshots are created with:
 *
 *   npx playwright test e2e/a11y-visual.spec.ts --update-snapshots
 *
 * and reviewed as normal PNGs under e2e/a11y-visual.spec.ts-snapshots/.
 */

import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const API = "http://localhost:8000/api/v1";
const EMAIL = "admin@epi.local";
const PASSWORD = "EpiAdmin2026!";
const TENANT = "acme-procurement";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function signIn(page: Page) {
  // Log in through the page's request context: the access token stays in
  // memory and the httpOnly refresh cookie rebuilds the session on load.
  const response = await page.request.post(`${API}/auth/login`, {
    data: { email: EMAIL, password: PASSWORD, tenant_slug: TENANT },
  });
  expect(response.ok()).toBeTruthy();
  await page.goto("/ask");
  await expect(page.getByPlaceholder(/unit price for the Industrial Laptop/i)).toBeVisible({ timeout: 30_000 });
}

function describeViolations(violations: Awaited<ReturnType<AxeBuilder["analyze"]>>["violations"]): string {
  return violations
    .map((violation) => `${violation.id} (${violation.impact ?? "unknown"}): ${violation.help} — ${violation.nodes.length} node(s)`)
    .join("\n");
}

test("Ask page has no WCAG A/AA violations", async ({ page }) => {
  await signIn(page);
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  expect(results.violations, describeViolations(results.violations)).toEqual([]);
});

test("Documents page has no WCAG A/AA violations", async ({ page }) => {
  await signIn(page);
  await page.goto("/documents");
  await expect(page.getByRole("heading", { name: "Documents", level: 1 })).toBeVisible({ timeout: 30_000 });
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  expect(results.violations, describeViolations(results.violations)).toEqual([]);
});

test("Login page has no WCAG A/AA violations", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign in", level: 1 })).toBeVisible({ timeout: 30_000 });
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  expect(results.violations, describeViolations(results.violations)).toEqual([]);
});

// ------------------------------------------------------------------ snapshots

for (const scheme of ["light", "dark"] as const) {
  test(`Ask page visual snapshot (${scheme})`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme });
    await signIn(page);
    await expect(page).toHaveScreenshot(`ask-${scheme}.png`, { fullPage: true, animations: "disabled" });
  });

  test(`Documents page visual snapshot (${scheme})`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme });
    await signIn(page);
    await page.goto("/documents");
    await expect(page.getByRole("heading", { name: "Documents", level: 1 })).toBeVisible({ timeout: 30_000 });
    await expect(page).toHaveScreenshot(`documents-${scheme}.png`, { fullPage: true, animations: "disabled" });
  });

  test(`Login page visual snapshot (${scheme})`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme });
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Sign in", level: 1 })).toBeVisible({ timeout: 30_000 });
    await expect(page).toHaveScreenshot(`login-${scheme}.png`, { fullPage: true, animations: "disabled" });
  });
}
