import { test, expect } from "@playwright/test";
import fs from "node:fs";
const demo = JSON.parse(
  fs.readFileSync(new URL("../../public/demo-config.json", import.meta.url)),
);
const index = JSON.parse(
  fs.readFileSync(
    new URL(`../../public${demo.baseUrl}index.json`, import.meta.url),
  ),
);
const rotorFlight = index.runs[0].run_id.startsWith("isaac-");
const start = async (page) => {
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText(
    rotorFlight
      ? "Checksums verified. Isaac PhysX quadrotor recording."
      : "Checksums verified. CPU simulation recording.",
  );
};
test("loads only selected evidence, scrubs events, pauses offscreen and remounts", async ({
  page,
}) => {
  const requested = [],
    errors = [];
  page.on("request", (req) => requested.push(req.url()));
  page.on("pageerror", (e) => errors.push(e.message));
  await start(page);
  expect(requested.some((url) => url.includes(index.runs[1].run_id))).toBe(
    false,
  );
  expect(requested.some((url) => url.endsWith("samples.json"))).toBe(false);
  await expect(
    page.getByRole("button", { name: "Play replay", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Experiment").selectOption("1");
  await expect(
    page.getByRole("button", { name: "10s / target step" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "10s / target step" }).click();
  await expect(page.getByRole("slider")).toHaveValue("10");
  await page.getByRole("slider").focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("slider")).toHaveValue("10.01");
  await page.getByRole("button", { name: "Play replay", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Pause replay" }),
  ).toBeVisible();
  await page.getByText("End of local replay demo.").scrollIntoViewIfNeeded();
  await expect(
    page.getByRole("button", { name: "Play replay", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("heading", { name: "AeroLoop replay", exact: true })
    .scrollIntoViewIfNeeded();
  await page.getByRole("button", { name: "Toggle viewer" }).click();
  await expect(page.locator(".al-replay")).toHaveCount(0);
  await page.getByRole("button", { name: "Toggle viewer" }).click();
  await expect(page.getByRole("status")).toContainText("Checksums verified");
  expect(errors).toEqual([]);
});
test("checksum corruption fails closed", async ({ page }) => {
  await page.route("**/replay.json", async (route) => {
    const response = await route.fetch();
    const value = await response.json();
    value.samples[0].position_m[0] = 99;
    await route.fulfill({ response, json: value });
  });
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText(
    "Replay unavailable: recording failed verification.",
  );
  await expect(
    page.getByRole("button", { name: "Play replay", exact: true }),
  ).toBeDisabled();
});
test("reduced motion and mobile retain controls; 3D can mount and dispose", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce", colorScheme: "dark" });
  await page.setViewportSize({ width: 375, height: 900 });
  await start(page);
  await expect(page.getByText(/Reduced motion is enabled/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Play replay", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Enable 3D view" }).click();
  await expect(page.locator("canvas")).toHaveCount(1);
  await page.getByRole("button", { name: "Top view", exact: true }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Side view", exact: true }).click();
  if (rotorFlight) {
    await expect(page.getByRole("meter")).toHaveCount(4);
    await expect(page.locator(".al-badge")).toHaveText("Isaac PhysX");
  }
  await page.getByRole("button", { name: "Use schematic" }).click();
  await expect(page.locator("canvas")).toHaveCount(0);
  await page.getByRole("button", { name: "Enable 3D view" }).click();
  await expect(page.locator("canvas")).toHaveCount(1);
  await page.screenshot({
    path: "test-results/replay-mobile.png",
    fullPage: false,
  });
});
test("unavailable WebGL retains the schematic and playback", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (kind, ...rest) {
      return kind.startsWith("webgl")
        ? null
        : original.call(this, kind, ...rest);
    };
  });
  await start(page);
  await page.getByRole("button", { name: "Enable 3D view" }).click();
  await expect(
    page.getByText(
      "3D is unavailable. The schematic and recording controls remain available.",
    ),
  ).toBeVisible();
  await expect(page.locator(".al-schematic")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Play replay", exact: true }),
  ).toBeEnabled();
});
test("stale loads cannot replace a later experiment", async ({ page }) => {
  await start(page);
  let release;
  const barrier = new Promise((resolve) => {
    release = resolve;
  });
  await page.route(`**/${index.runs[1].run_id}/replay.json`, async (route) => {
    await barrier;
    try {
      await route.continue();
    } catch {}
  });
  await page.getByLabel("Experiment").selectOption("1");
  await page.getByLabel("Experiment").selectOption("2");
  release();
  await expect(
    page.getByRole("button", { name: "15s / force start" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "10s / target step" }),
  ).toHaveCount(0);
  await expect(page.getByRole("status")).toContainText("Checksums verified");
});
test("tablet and wide views fit in light and dark themes", async ({ page }) => {
  await start(page);
  for (const width of [768, 1440, 1920]) {
    for (const colorScheme of ["light", "dark"]) {
      await page.setViewportSize({ width, height: 1100 });
      await page.emulateMedia({ colorScheme });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
  }
  await page.getByLabel("Experiment").selectOption("1");
  await page.getByRole("button", { name: "10s / target step" }).click();
  await page.screenshot({
    path: "test-results/replay-wide.png",
    fullPage: false,
  });
});
