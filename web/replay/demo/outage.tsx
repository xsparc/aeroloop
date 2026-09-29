import {StrictMode} from "react";
import {createRoot} from "react-dom/client";
import {OutageDemo} from "../src/outage.js";
const root=createRoot(document.getElementById("root")!);
fetch("/outage-config.json",{credentials:"omit",redirect:"error",cache:"no-cache"})
  .then(async response=>{if(!response.ok)throw Error();const text=await response.text();if(text.length>1024)throw Error();const c=JSON.parse(text);if(Object.keys(c).sort().join()!=="baseUrl,indexSha256"||typeof c.baseUrl!=="string"||typeof c.indexSha256!=="string")throw Error();return c;})
  .then(config=>root.render(<StrictMode><OutageDemo {...config}/></StrictMode>))
  .catch(()=>root.render(<main><h1>Predictive flight demo</h1><p>Prepare a verified study with tools/prediction_demo.py and set outage-config.json before opening this demo.</p></main>));
