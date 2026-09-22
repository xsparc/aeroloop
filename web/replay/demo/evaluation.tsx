import {StrictMode} from "react";
import {createRoot} from "react-dom/client";
import {FlightEvaluation} from "../src/evaluation.js";
const root=createRoot(document.getElementById("root")!);
fetch("/evaluation-config.json",{credentials:"omit",redirect:"error",cache:"no-cache"})
  .then(async response=>{if(!response.ok)throw Error();const text=await response.text();if(text.length>1024)throw Error();return JSON.parse(text);})
  .then(config=>root.render(<StrictMode><FlightEvaluation {...config}/></StrictMode>))
  .catch(()=>root.render(<main><h1>Flight evaluation</h1><p>Prepare the study with tools/evaluation_demo.py before opening the explorer.</p></main>));
