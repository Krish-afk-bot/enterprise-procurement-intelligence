import { expect, test } from "@playwright/test";

/**
 * The three journeys a reviewer actually performs: the public page renders, a
 * real account can sign in, and a real question returns evidence from the
 * indexed corpus. The search assertion is intentionally about a known notice so
 * a regression in retrieval or in the page's rendering fails the test rather
 * than passing on a generic "results" heading.
 */
const EMAIL = process.env.EPI_E2E_EMAIL ?? "admin@epi.local";
const PASSWORD = process.env.EPI_E2E_PASSWORD ?? "admin-local-password";

test("public landing page renders", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Enterprise Procurement Intelligence/i);
  await expect(page.getByRole("link", { name: /sign in/i }).first()).toBeVisible();
});

test("a real account can sign in", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel(/^email$/i).fill(EMAIL);
  await page.getByLabel(/^password$/i).fill(PASSWORD);
  await page.getByRole("button", { name: /^sign in$/i }).click();
  await expect(page).toHaveURL(/\/ask\b/, { timeout: 45_000 });
  await expect(page.getByRole("navigation")).toBeVisible();
});

test("search returns the indexed notice for a subject query", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel(/^email$/i).fill(EMAIL);
  await page.getByLabel(/^password$/i).fill(PASSWORD);
  await page.getByRole("button", { name: /^sign in$/i }).click();
  await expect(page).toHaveURL(/\/ask\b/, { timeout: 45_000 });

  await page.goto("/search");
  await page.getByLabel(/what are you looking for/i).fill("master vendor contingent workforce recruitment");
  await page.getByRole("button", { name: /^search$/i }).click();
  await expect(page.getByText(/064670/).first()).toBeVisible({ timeout: 60_000 });
});

test("a signed-out visitor is redirected away from the workspace", async ({ page }) => {
  await page.goto("/contracts");
  await expect(page).toHaveURL(/\/login\b|\/$/);
});

test("the ask, library and search screens render without runtime errors", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/login");
  await page.getByLabel(/^email$/i).fill(EMAIL);
  await page.getByLabel(/^password$/i).fill(PASSWORD);
  await page.getByRole("button", { name: /^sign in$/i }).click();
  await expect(page).toHaveURL(/\/ask\b/, { timeout: 45_000 });

  await expect(page.getByRole("heading", { name: /put a question to the contracts/i })).toBeVisible();

  await page.goto("/documents");
  await expect(page.getByRole("heading", { name: /^documents$/i })).toBeVisible();
  await expect(page.getByLabel("Documents by lifecycle")).toBeVisible();

  await page.goto("/search");
  await expect(page.getByRole("heading", { name: /^search$/i })).toBeVisible();

  expect(pageErrors).toEqual([]);
});
