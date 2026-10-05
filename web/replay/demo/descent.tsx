import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import {DescentWorkspace} from '../src/descent.js';
const root=createRoot(document.getElementById('root')!);
fetch('/descent-config.json',{credentials:'omit',redirect:'error',cache:'no-cache'})
  .then(async r=>{if(!r.ok)throw Error();const text=await r.text();if(text.length>1024)throw Error();const c=JSON.parse(text);if(Object.keys(c).sort().join()!=='baseUrl,indexSha256'||typeof c.baseUrl!=='string'||typeof c.indexSha256!=='string')throw Error();return c;})
  .then(config=>root.render(<StrictMode><DescentWorkspace {...config}/></StrictMode>))
  .catch(()=>root.render(<main><h1>Descent comparison</h1><p>Prepare a verified export with tools/decay_study.py and set descent-config.json.</p></main>));
