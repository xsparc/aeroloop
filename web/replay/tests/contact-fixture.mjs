// Synthetic contract and browser examples; never flight evidence.
import {fixture as descentFixture} from './descent-fixture.mjs';
import {COLUMNS,derived} from '../dist/contact-contract.js';
import {gateStatus} from '../dist/evaluation-contract.js';
import {headroom} from '../dist/diagnosis-contract.js';
import {hash} from './evaluation-fixture.mjs';
export function fixture(options={}){
  const source=descentFixture(options),index={schema_version:1,kind:'landing_contact_index',cases:[]},documents={};
  for(const entry of source.index.cases){const descent=JSON.parse(source.documents[entry.file]),body={schema_version:1,kind:'landing_contact',columns:COLUMNS,descent};
    const c={...entry};
    for(const mode of ['baseline','candidate']){const side=descent[mode];
      // Home-offset support failure, shared by both modes, with zero horizontal motion.
      for(const p of side.poses)p.position_m[0]=.4;
      const gate=side.gates.find(g=>g.id==='final_support_peak_xy_error_m');gate.value=side.rows.length===10001?.4:null;gate.status=gateStatus(gate);gate.headroom=headroom(gate);
      c[mode+'_support_error_m']=gate.value;
      body[mode]=side.rows.slice(6800).map((s,i)=>{const prev=side.rows[i+6799],armed=!s[19];
        const raw=[s[0],.4,0,0,0,.4,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,...Array(4).fill(s[12]/4),0,0,0,0,0,0,0,0];
        return [...raw,...derived(raw,armed)];
      });
    }
    documents[entry.file]=JSON.stringify(body);c.sha256=hash(documents[entry.file]);index.cases.push(c);
  }return {index,documents};
}
export async function routeFixture(page,options={}){
  const data=fixture(options),bytes=JSON.stringify(data.index);
  await page.route('**/contact-config.json',r=>r.fulfill({json:{baseUrl:'/test-contact/',indexSha256:hash(bytes)}}));
  await page.route('**/test-contact/**',async r=>{const file=new URL(r.request().url()).pathname.split('/').at(-1),body=file==='index.json'?bytes:data.documents[file];
    if(options.delay&&file===options.delay)await new Promise(resolve=>setTimeout(resolve,750));
    await r.fulfill({status:body?200:404,contentType:'application/json',body:options.corrupt&&file!=='index.json'?'{}':body??'{}'});});return data;
}
