import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import {DiagnosisWorkspace} from '../src/diagnosis.js';
const root=createRoot(document.getElementById('root')!);
fetch('/diagnosis-config.json',{credentials:'omit',redirect:'error',cache:'no-cache'})
  .then(async response=>{if(!response.ok)throw Error();const text=await response.text();if(text.length>1024)throw Error();const c=JSON.parse(text);if(Object.keys(c).sort().join()!=='baseUrl,indexSha256'||typeof c.baseUrl!=='string'||typeof c.indexSha256!=='string')throw Error();return c;})
  .then(config=>root.render(<StrictMode><DiagnosisWorkspace {...config}/></StrictMode>))
  .catch(()=>root.render(<main><h1>Flight diagnosis workspace</h1><p>Prepare a verified export with tools/diagnosis_demo.py and set diagnosis-config.json.</p></main>));
