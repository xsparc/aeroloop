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
const windFlight = index.runs[0].scenario === "turbulence-hold";
const firstEvent = (n) =>
  JSON.parse(
    fs.readFileSync(
      new URL(
        `../../public${demo.baseUrl}${index.runs[n].run_id}/events.json`,
        import.meta.url,
      ),
    ),
  )[0];
const eventOne = firstEvent(1),
  eventTwo = firstEvent(2);
const eventLabel = (event) =>
  `${event.time_s}s / ${event.type.replaceAll("_", " ")}`;
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
    page.getByRole("button", { name: eventLabel(eventOne) }),
  ).toBeVisible();
  await page.getByRole("button", { name: eventLabel(eventOne) }).click();
  await expect(page.getByRole("slider")).toHaveValue(String(eventOne.time_s));
  await page.getByRole("slider").focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("slider")).toHaveValue(
    String(eventOne.time_s + 0.01),
  );
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
    page.getByRole("button", { name: eventLabel(eventTwo) }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: eventLabel(eventOne) }),
  ).toHaveCount(0);
  await expect(page.getByRole("status")).toContainText("Checksums verified");
});
test("tablet and wide views fit in light and dark themes", async ({ page }) => {
  await start(page);
  for (const width of [768, 1440, 1920]) {
    for (const colorScheme of ["light", "dark"]) {
      await page.setViewportSize({ width, height: 1100 });
      await page.emulateMedia({ colorScheme });
      if (windFlight) {
        const contrast = await page
          .locator(".al-wind-intro")
          .evaluate((element) => {
            const style = getComputedStyle(element);
            const luminance = (color) =>
              color
                .match(/[\d.]+/g)
                .slice(0, 3)
                .map(Number)
                .map((n) => n / 255)
                .map((n) =>
                  n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4,
                )
                .reduce(
                  (sum, n, i) => sum + n * [0.2126, 0.7152, 0.0722][i],
                  0,
                );
            const a = luminance(style.color),
              b = luminance(style.backgroundColor);
            return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
          });
        expect(contrast).toBeGreaterThanOrEqual(4.5);
      }
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
  }
  await page.getByLabel("Experiment").selectOption("1");
  await page.getByRole("button", { name: eventLabel(eventOne) }).click();
  await page.screenshot({
    path: "test-results/replay-wide.png",
    fullPage: false,
  });
});

test("turbulence exposes measured forces, recovery and a verified reference comparison", async ({
  page,
}) => {
  test.skip(
    !windFlight,
    "Requires retained Isaac turbulence evidence; CPU CI does not simulate Isaac.",
  );
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await start(page);
  await expect(
    page.getByText("Position hold enabled", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Enable 3D view" }).click();
  await expect(page.locator("canvas")).toHaveCount(1);
  await page.getByRole("slider").fill("13");
  await expect(page.getByText("Stronger gust", { exact: true })).toBeVisible();
  await expect(page.getByRole("meter")).toHaveCount(4);
  await page
    .getByRole("button", { name: "Compare reference", exact: true })
    .click();
  await expect(page.getByLabel("Stabilization comparison")).toContainText(
    "less position error during wind",
  );
  await expect(page.locator(".al-comparison-message")).toContainText(
    "Same seed, initial position, wind samples and source verified",
  );
  await expect(page.locator(".al-plot polyline")).toHaveCount(2);
  await page
    .locator(".al-replay")
    .screenshot({ path: "test-results/turbulence-comparison.png" });
  await page.getByRole("slider").fill("30");
  await expect(
    page.getByText("Recovery in calm air", { exact: true }),
  ).toBeVisible();
  const error = await page
    .getByText("Position error now", { exact: true })
    .locator("..")
    .locator("dd")
    .textContent();
  expect(parseFloat(error)).toBeLessThan(0.1);
  await page.getByLabel("Experiment").selectOption("1");
  await expect(
    page.getByText("Reference completed (position hold disabled)", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByLabel("Stabilization comparison")).toHaveCount(0);
  await page.getByRole("slider").fill("30");
  await page.getByRole("button", { name: "Side view", exact: true }).click();
  expect(errors).toEqual([]);
});

test("corrupted comparison cannot claim stabilization evidence", async ({
  page,
}) => {
  test.skip(!windFlight, "Requires retained Isaac turbulence evidence.");
  await start(page);
  await page.route(`**/${index.runs[1].run_id}/replay.json`, async (route) => {
    const response = await route.fetch();
    const value = await response.json();
    value.samples[1].wind_velocity_m_s[0] += 1;
    await route.fulfill({ response, json: value });
  });
  await page
    .getByRole("button", { name: "Compare reference", exact: true })
    .click();
  await expect(page.locator(".al-comparison-message")).toHaveText(
    "Comparison unavailable: matching evidence failed verification.",
  );
  await expect(page.getByLabel("Stabilization comparison")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Play replay", exact: true }),
  ).toBeEnabled();
});
