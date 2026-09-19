import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/browser", fullyParallel: false, workers: 1,
  use: { baseURL: "http://127.0.0.1:8766", browserName: "chromium", viewport: { width: 1100, height: 1000 } },
  webServer: { command: "npm run dev -- --port 8766 --strictPort", url: "http://127.0.0.1:8766", reuseExistingServer: false },
});
