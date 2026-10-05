import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import {ContactWorkspace} from '../src/contact.js';
const root=createRoot(document.getElementById('root')!);
fetch('/contact-config.json',{credentials:'omit',redirect:'error',cache:'no-cache'})
  .then(async r=>{if(!r.ok)throw Error();const text=await r.text();if(text.length>1024)throw Error();const c=JSON.parse(text);if(Object.keys(c).sort().join()!=='baseUrl,indexSha256'||typeof c.baseUrl!=='string'||typeof c.indexSha256!=='string')throw Error();return c;})
  .then(config=>root.render(<StrictMode><ContactWorkspace {...config}/></StrictMode>))
  .catch(()=>root.render(<main><h1>Landing contact lab</h1><p>Prepare a verified export with tools/contact_study.py and set contact-config.json.</p></main>));
