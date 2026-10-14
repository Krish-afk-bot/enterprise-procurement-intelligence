import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    // Exclude Playwright E2E specs — those are run by `npm run e2e`, not Vitest
    exclude: ["**/node_modules/**", "**/dist/**", "**/e2e/**"],
  },
});
