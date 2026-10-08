import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import {FrictionWorkspace,FrictionLive} from '../src/friction.js';
const root=createRoot(document.getElementById('root')!);
if(location.pathname==='/friction-live.html')root.render(<StrictMode><FrictionLive/></StrictMode>);
else fetch('/friction-config.json',{credentials:'omit',redirect:'error',cache:'no-cache'})
  .then(async r=>{if(!r.ok)throw Error();const t=await r.text();if(t.length>1024)throw Error();const c=JSON.parse(t);if(Object.keys(c).sort().join()!=='baseUrl,indexSha256'||typeof c.baseUrl!=='string'||typeof c.indexSha256!=='string')throw Error();return c;})
  .then(c=>root.render(<StrictMode><FrictionWorkspace {...c}/></StrictMode>))
  .catch(()=>root.render(<main><h1>Contact physics lab</h1><p>Prepare a verified bundle with tools/friction_study.py and set friction-config.json.</p></main>));
