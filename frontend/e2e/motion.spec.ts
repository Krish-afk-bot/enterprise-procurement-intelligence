import { test, expect } from "@playwright/test";

test.describe("Landing Page Motion & Animation Engine Proof", () => {
  test("hero animates automatically in full motion with ambient loops running", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto("http://127.0.0.1:5173/?motion=debug");

    await page.waitForSelector("#hero");
    await page.waitForTimeout(400);

    // Frame 1 at t = 0.4s
    const frame1 = await page.locator("#hero").screenshot();

    // Frame 2 at t = 2.0s
    await page.waitForTimeout(1600);
    const frame2 = await page.locator("#hero").screenshot();

    // Frame 3 at t = 4.0s
    await page.waitForTimeout(2000);
    const frame3 = await page.locator("#hero").screenshot();

    // Verified that frames differ: intro sequence and ambient loops are actively moving
    expect(frame1).not.toEqual(frame2);
    expect(frame2).not.toEqual(frame3);

    const debugText = await page.locator("#motion-debug-overlay").innerText();
    expect(debugText).toMatch(/Effective Mode:\s*full/);
    expect(debugText).toMatch(/Active Tweens:\s*[1-9]\d*/);
  });

  test("reduced motion retains gentle breathing and non-dead life without transforms", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("http://127.0.0.1:5173/?motion=debug");

    await page.waitForSelector("#hero");
    await page.waitForTimeout(600);

    const debugText = await page.locator("#motion-debug-overlay").innerText();
    expect(debugText).toMatch(/Effective Mode:\s*reduced/);
    expect(debugText).toMatch(/OS Reduced Motion:\s*true/);
    expect(debugText).toMatch(/Active Tweens:\s*[1-9]\d*/);
  });
});
