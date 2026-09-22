import React from "react";
import { createRoot } from "react-dom/client";
import { LiveMonitor } from "../src/live.js";
import "../src/style.css";
import "../src/live.css";
createRoot(document.getElementById("root")!).render(<React.StrictMode><LiveMonitor/></React.StrictMode>);
