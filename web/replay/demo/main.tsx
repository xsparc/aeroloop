import React, { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { ReplayViewer, type ReplayViewerProps } from "../src/index.js";
import "../src/style.css";

function Demo({ config }: { config: ReplayViewerProps }) {
  const [mounted, setMounted] = useState(true);
  return <><h1>AeroLoop replay</h1><p>Recorded CPU physics. No live flight control.</p>
    <button onClick={() => setMounted(value => !value)}>Toggle viewer</button>
    {mounted && <ReplayViewer {...config} />}
    <footer style={{ marginTop: "120vh" }}>End of local replay demo.</footer></>;
}
const root = createRoot(document.getElementById("root")!);
fetch("/demo-config.json").then(response => {
  if (!response.ok) throw Error("Missing demo evidence");
  return response.json();
}).then(config => root.render(<StrictMode><Demo config={config} /></StrictMode>))
  .catch(() => root.render(<p>Prepare recordings with tools/replay_demo.py before starting the demo.</p>));
