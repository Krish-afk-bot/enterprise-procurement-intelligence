/**
 * Auth setup: log in once and save the resulting browser context state so other
 * tests can reuse the session.
 *
 * The access token is held in memory only, so the durable credential is the
 * httpOnly refresh cookie the backend sets on login. `storageState` persists
 * cookies, so saving it is enough — nothing is written to localStorage.
 */
import { test as setup } from "@playwright/test";
import path from "node:path";

export const STORAGE_STATE = path.join(__dirname, "fixtures/auth-state.json");

const EMAIL = "admin@epi.local";
const PASSWORD = "EpiAdmin2026!";
const TENANT = "acme-procurement";

setup("authenticate as admin", async ({ page }) => {
  // Call the API directly — faster and more reliable than filling a login form.
  // The response sets the refresh cookie on this browser context.
  const response = await page.request.post("/api/v1/auth/login", {
    data: { email: EMAIL, password: PASSWORD, tenant_slug: TENANT },
  });
  if (!response.ok()) {
    throw new Error(`Login failed with ${response.status()}: ${await response.text()}`);
  }

  const cookies = await page.context().cookies();
  if (!cookies.some((cookie) => cookie.name === "epi_refresh")) {
    throw new Error("Login did not set the httpOnly refresh cookie.");
  }

  await page.context().storageState({ path: STORAGE_STATE });
});
