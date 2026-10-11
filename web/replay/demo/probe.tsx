import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import {ProbeWorkspace} from '../src/probe.js';
const root=createRoot(document.getElementById('root')!);
fetch('/probe-config.json',{credentials:'omit',redirect:'error',cache:'no-cache'})
  .then(async r=>{if(!r.ok)throw Error();const t=await r.text();if(t.length>1024)throw Error();const c=JSON.parse(t);if(Object.keys(c).sort().join()!=='baseUrl,indexSha256'||typeof c.baseUrl!=='string'||typeof c.indexSha256!=='string')throw Error();return c;})
  .then(c=>root.render(<StrictMode><ProbeWorkspace {...c}/></StrictMode>))
  .catch(()=>root.render(<main><h1>Liftoff contact probe</h1><p>Export a twelve-run matrix with tools/contact_probe.py and configure probe-config.json.</p></main>));
