import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import {ApproachWorkspace} from '../src/approach.js';
const root=createRoot(document.getElementById('root')!);
fetch('/approach-config.json',{credentials:'omit',redirect:'error',cache:'no-cache'})
  .then(async r=>{if(!r.ok)throw Error();const text=await r.text();if(text.length>1024)throw Error();const c=JSON.parse(text);if(Object.keys(c).sort().join()!=='baseUrl,indexSha256'||typeof c.baseUrl!=='string'||typeof c.indexSha256!=='string')throw Error();return c;})
  .then(config=>root.render(<StrictMode><ApproachWorkspace {...config}/></StrictMode>))
  .catch(()=>root.render(<main><h1>Approach gain study</h1><p>Prepare a verified export with tools/approach_study.py and set approach-config.json.</p></main>));
