import {StrictMode} from "react";
import {createRoot} from "react-dom/client";
import {OutageDemo} from "../src/outage.js";
const root=createRoot(document.getElementById("root")!);
fetch("/axis-config.json",{credentials:"omit",redirect:"error",cache:"no-cache"})
  .then(async response=>{if(!response.ok)throw Error();const text=await response.text();if(text.length>1024)throw Error();const c=JSON.parse(text);if(Object.keys(c).sort().join()!=="baseUrl,indexSha256"||typeof c.baseUrl!=="string"||typeof c.indexSha256!=="string")throw Error();return c;})
  .then(config=>root.render(<StrictMode><OutageDemo {...config}/></StrictMode>))
  .catch(()=>root.render(<main><h1>Axis availability demo</h1><p>Prepare a verified study with tools/axis_demo.py and set axis-config.json before opening this demo.</p></main>));
