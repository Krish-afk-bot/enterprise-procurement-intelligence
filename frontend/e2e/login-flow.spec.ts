import { test, expect } from "@playwright/test";

test.describe("Login and Authentication Flow", () => {
  test("admin can sign in and load workspace without 401 or 403 errors", async ({ page }) => {
    // Track any network errors
    const forbiddenRequests: string[] = [];
    page.on("response", (response) => {
      if (response.status() === 403 || (response.status() === 401 && !response.url().includes("/auth/refresh"))) {
        forbiddenRequests.push(`${response.status()} ${response.url()}`);
      }
    });

    await page.goto("http://127.0.0.1:5173/login", { waitUntil: "networkidle" });

    // Fill credentials
    await page.fill('input[type="email"], #email', "admin@epi.local");
    await page.fill('input[type="password"], #password', "admin-local-password");

    // Click submit
    await page.click('button[type="submit"]');

    // Wait for navigation to /ask
    await page.waitForURL("**/ask", { timeout: 10000 });
    await expect(page).toHaveURL(/.*\/ask/);

    // Verify workspace elements loaded
    await expect(page.locator("nav[aria-label='Workspace']")).toBeVisible();
    await expect(page.locator("textarea, input[placeholder*='question']").first()).toBeVisible();

    // Verify no 403 or unexpected 401 occurred after login
    expect(forbiddenRequests).toEqual([]);
  });

  test("buyer can sign in and load workspace cleanly", async ({ page }) => {
    const forbiddenRequests: string[] = [];
    page.on("response", (response) => {
      if (response.status() === 403 || (response.status() === 401 && !response.url().includes("/auth/refresh"))) {
        forbiddenRequests.push(`${response.status()} ${response.url()}`);
      }
    });

    await page.goto("http://127.0.0.1:5173/login", { waitUntil: "networkidle" });

    await page.fill('input[type="email"], #email', "buyer@epi.local");
    await page.fill('input[type="password"], #password', "buyer123");

    await page.click('button[type="submit"]');
    await page.waitForURL("**/ask", { timeout: 10000 });
    await expect(page).toHaveURL(/.*\/ask/);

    expect(forbiddenRequests).toEqual([]);
  });
});
