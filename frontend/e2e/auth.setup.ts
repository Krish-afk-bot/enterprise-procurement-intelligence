/**
 * Auth setup: log in and save the authentication state to a file
 * so tests can reuse the session without re-logging in each time.
 */
import { test as setup } from "@playwright/test";
import path from "node:path";

export const STORAGE_STATE = path.join(__dirname, "fixtures/auth-state.json");

const EMAIL = "admin@epi.local";
const PASSWORD = "EpiAdmin2026!";
const TENANT = "acme-procurement";

setup("authenticate as admin", async ({ page }) => {
  // Call the API directly — faster and more reliable than filling a login form
  const response = await page.request.post("/api/v1/auth/login", {
    data: { email: EMAIL, password: PASSWORD, tenant_slug: TENANT },
  });
  const body = await response.json();

  // Store the JWT in localStorage so the React app picks it up
  await page.goto("/");
  await page.evaluate(
    ({ token, user }) => {
      localStorage.setItem(
        "auth-storage",
        JSON.stringify({ state: { token, user, isAuthenticated: true } }),
      );
    },
    { token: body.access_token, user: body.user },
  );

  await page.context().storageState({ path: STORAGE_STATE });
});
