import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

const PROOF_DIR = path.resolve(process.cwd(), "e2e/proof");
if (!fs.existsSync(PROOF_DIR)) {
  fs.mkdirSync(PROOF_DIR, { recursive: true });
}

test.describe("Hero Section Round 2 Verification", () => {
  test.beforeEach(async ({ page }) => {
    // Skip first-visit intro loader so tests can inspect page states immediately
    await page.addInitScript(() => {
      sessionStorage.setItem("epi_loader_seen", "true");
    });
  });

  test("Desktop 1440x900 screenshots at t = 0.5s, 2s, 5s and computed styles", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });

    // Wait 500ms
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(PROOF_DIR, "hero-1440-t0.5s.png"), fullPage: false });

    // Wait until t = 2s
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(PROOF_DIR, "hero-1440-t2.0s.png"), fullPage: false });

    // Wait until t = 5s
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(PROOF_DIR, "hero-1440-t5.0s.png"), fullPage: false });

    // Verify presence and visibility of all key elements
    const eyebrow = page.locator(".hero-eyebrow");
    const primaryCta = page.locator(".hero-cta-primary");
    const secondaryCta = page.locator(".hero-cta").nth(1);
    const chip = page.locator(".hero-chip-badge");
    const headline = page.locator(".hero-headline");
    const headlineSpans = page.locator(".hero-headline-span");
    const cards = page.locator(".hero-card");
    const traces = page.locator(".hero-trace");

    await expect(eyebrow).toBeVisible();
    await expect(primaryCta).toBeVisible();
    await expect(secondaryCta).toBeVisible();
    await expect(chip).toBeVisible();
    await expect(headline).toBeVisible();
    await expect(headlineSpans).toHaveCount(2);
    await expect(cards).toHaveCount(6);
    await expect(traces).toHaveCount(6);

    // Verify all 6 cards are visible in the 1440x900 viewport without scrolling
    for (let i = 0; i < 6; i++) {
      const card = cards.nth(i);
      await expect(card).toBeVisible();
      const box = await card.boundingBox();
      expect(box).not.toBeNull();
      if (box) {
        expect(box.y + box.height).toBeLessThanOrEqual(900);
      }
    }

    // DevTools computed styles check
    const styles = await page.evaluate(() => {
      const getStyles = (selector: string) => {
        const el = document.querySelector(selector);
        if (!el) return null;
        const comp = window.getComputedStyle(el);
        return {
          opacity: comp.opacity,
          visibility: comp.visibility,
          display: comp.display,
        };
      };

      return {
        eyebrow: getStyles(".hero-eyebrow"),
        primaryCta: getStyles(".hero-cta-primary"),
        secondaryCta: getStyles(".hero-cta:nth-child(2)"),
        firstCard: getStyles(".hero-card"),
        headline: getStyles(".hero-headline"),
      };
    });

    console.log("Computed Styles at t=5s:", JSON.stringify(styles, null, 2));

    expect(styles.eyebrow?.opacity).toBe("1");
    expect(styles.eyebrow?.visibility).toBe("visible");
    expect(styles.primaryCta?.opacity).toBe("1");
    expect(styles.primaryCta?.visibility).toBe("visible");
    expect(styles.secondaryCta?.opacity).toBe("1");
    expect(styles.secondaryCta?.visibility).toBe("visible");
    expect(styles.firstCard?.opacity).toBe("1");
    expect(styles.firstCard?.visibility).toBe("visible");
  });

  test("Desktop 1920x1080 screenshots at t = 0.5s, 2s, 5s", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });

    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(PROOF_DIR, "hero-1920-t0.5s.png"), fullPage: false });

    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(PROOF_DIR, "hero-1920-t2.0s.png"), fullPage: false });

    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(PROOF_DIR, "hero-1920-t5.0s.png"), fullPage: false });

    const cards = page.locator(".hero-card");
    await expect(cards).toHaveCount(6);
    for (let i = 0; i < 6; i++) {
      await expect(cards.nth(i)).toBeVisible();
    }
  });

  test("Header Top State vs Pill State on scroll", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
    await page.waitForTimeout(400);

    // Scroll = 0: Top state with lockup (Logo + EPI text)
    const header = page.locator("header.site-header");
    await expect(header).toHaveAttribute("data-state", "top");
    await page.screenshot({ path: path.join(PROOF_DIR, "header-scroll-0.png"), fullPage: false });

    // Scroll = 200: Pill state with mark only
    await page.evaluate(() => window.scrollTo(0, 200));
    await page.waitForTimeout(500);
    await expect(header).toHaveAttribute("data-state", "pill");
    await page.screenshot({ path: path.join(PROOF_DIR, "header-scroll-200.png"), fullPage: false });
  });

  test("Hero-to-Explainer Curtain at 50% scroll progress", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
    await page.waitForTimeout(400);

    // Scroll so that the boundary between hero and explainer is centered at 50% viewport
    const explainer = page.locator("#explainer");
    await expect(explainer).toBeVisible();

    await page.evaluate(() => {
      const el = document.getElementById("explainer");
      if (el) {
        const top = el.getBoundingClientRect().top + window.scrollY;
        // Position top of explainer 450px down from viewport top (50% of 900px)
        window.scrollTo(0, top - 450);
      }
    });

    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(PROOF_DIR, "curtain-50percent.png"), fullPage: false });
  });

  test("Frame-diff test proving ambient pulse loops differ over time", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });

    // Let intro settle to t = 3.5s
    await page.waitForTimeout(3500);
    const bufferA = await page.screenshot();

    // Wait to t = 5.5s (ambient pulses have moved)
    await page.waitForTimeout(2000);
    const bufferB = await page.screenshot();

    // Verify bufferA and bufferB are not identical (pulses are travelling!)
    expect(bufferA.equals(bufferB)).toBe(false);
  });
});
