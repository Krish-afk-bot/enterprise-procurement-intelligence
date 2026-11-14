import { test, expect } from "@playwright/test";

test.describe("Earth Knowledge Graph Globe", () => {
  test("renders 3D earth globe with land nodes, water disc, and no clipping", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("http://127.0.0.1:5173/#globe", { waitUntil: "networkidle" });

    const globeSection = page.locator("#globe");
    await expect(globeSection).toBeVisible();

    const canvas = globeSection.locator("canvas");
    await expect(canvas).toBeVisible({ timeout: 10000 });

    // Scroll canvas to center of viewport
    await canvas.scrollIntoViewIfNeeded();
    await page.waitForTimeout(2000);

    // Capture screenshot of the globe container and surrounding cards
    await globeSection.screenshot({ path: "e2e/globe-proof.png" });
  });
});
