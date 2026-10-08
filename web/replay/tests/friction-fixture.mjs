import {createHash} from 'node:crypto';
import {summary} from '../dist/friction-contract.js';
export const digest=v=>createHash('sha256').update(v).digest('hex');
export function fixture(){
  const rows=Array.from({length:10001},(_,i)=>{const r=Array(35).fill(0);r[0]=i*.005;r[3]=.05;r[4]=1;r[13]=i?9.81:0;r[14]=i?-.5:0;r[23]=i?.0025:0;r[30]=i?.5/9.81:null;r[31]=null;r[32]=i?2:0;r[33]=i?1:0;r[34]=1;return r;});
  const f={schema_version:1,kind:'friction_case',id:'fixed-intact-s401-dt5000',seed:401,mode:'fixed',profile:'sample-hold',physics_dt_s:.005,status:'failed',failure_reason:'fixture',
    source:{source_commit:'a'.repeat(40),source_dirty:false,source_tree_sha256:'b'.repeat(64),lock_sha256:'c'.repeat(64)},capture_sha256:'d'.repeat(64),flight_checksums_sha256:'e'.repeat(64),controller_binary_sha256:'f'.repeat(64),versions:{isaacsim:'fixture'},
    gates:[{id:'fixture',label:'Synthetic gate',status:'failed',value:1,limit:0,unit:'count'}],columns:Array.from({length:35},(_,i)=>'column_'+i),rows,summary:summary(rows,0,50)};
  const body=JSON.stringify(f),entry={...Object.fromEntries(['id','seed','mode','profile','physics_dt_s','status','summary'].map(k=>[k,f[k]])),file:f.id+'.json',sha256:digest(body)};
  const index=JSON.stringify({schema_version:1,kind:'friction_index',cases:[entry]});return {f,entry,body,index,hash:digest(index)};
}
export async function routeFixture(page,{corrupt=false}={}){const b=fixture();await page.route('**/friction-config.json',r=>r.fulfill({json:{baseUrl:'/contact-fixture/',indexSha256:b.hash}}));await page.route('**/contact-fixture/index.json',r=>r.fulfill({contentType:'application/json',body:b.index}));await page.route('**/contact-fixture/*.json',r=>r.request().url().endsWith('/index.json')?r.fallback():r.fulfill({contentType:'application/json',body:corrupt?b.body+' ':b.body}));return b;}
