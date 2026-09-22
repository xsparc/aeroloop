import { defineConfig } from "vite";
export default defineConfig({
  build: { outDir: "demo-dist", rolldownOptions: { input: { replay: "index.html", monitor: "monitor.html", evaluation: "evaluation.html" } } },
  // Prebundle the lazy renderer too, so first enabling 3D never reloads the page.
  optimizeDeps: { include: ["three", "three/addons/controls/OrbitControls.js"] },
});
