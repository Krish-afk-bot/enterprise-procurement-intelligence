import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E test configuration.
 *
 * Requires the following to be running before the tests execute:
 *   - Backend API at http://localhost:8000
 *   - Frontend dev server at http://localhost:5173
 *
 * Start them with:
 *   cd backend && python -m uvicorn app.main:app --port 8000
 *   cd frontend && npm run dev
 *
 * Run tests with:
 *   cd frontend && npm run e2e
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "e2e/results/results.json" }]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    // LLM queries can take 30–60 s on a local 8B model
    actionTimeout: 90_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], headless: true },
    },
  ],
  // Do NOT use webServer — the backend and frontend must already be running.
  // This keeps the E2E suite decoupled from process management.
});
