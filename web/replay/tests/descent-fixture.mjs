// Synthetic browser contracts only, not physics evidence.
import {fixture as diagnosisFixture} from './diagnosis-fixture.mjs';
import {hash} from './evaluation-fixture.mjs';
import {gateStatus} from '../dist/evaluation-contract.js';
import {headroom} from '../dist/diagnosis-contract.js';
import {COLUMNS,windowMetrics} from '../dist/descent-contract.js';
export function fixture({incomplete=false}={}){
  const source=JSON.parse(diagnosisFixture().documents['q3-p1-s0.json']);
  const documents={},index={schema_version:1,kind:'descent_comparison_index',cases:[]};
  for(const cohort of ['regression','additional'])for(const [p,profile] of ['sample-hold','hold-dropout-2000ms'].entries())for(const seed of cohort==='regression'?[0,1,2]:[401,503,607]){
    const id=`${cohort}-p${p}-s${seed}`,body={schema_version:1,kind:'descent_comparison',id,cohort,profile,seed,columns:COLUMNS};
    for(const mode of ['baseline','candidate']){
      const count=incomplete&&p?100:10001;
      const rows=Array.from({length:count},(_,i)=>{const t=Number((i*.005).toFixed(9)),contact=t>=41.2,landed=t>=41.25,armed=t>=2&&!landed,z=contact?.06:1,v=contact?0:-.1;
        const age=p&&((t>=18&&t<20)||(t>=40&&t<42))?t-(t<20?17.98:39.98):i%4*.005;
        return [t,z,z,v,v,z,0,0,armed?-2.8*v:0,0,armed?-2.8*v:0,armed?9.8:0,armed?9.8:0,armed?9.8:0,0,contact?10:0,contact?.01:.95,Number(contact),contact?t-41.2:0,Number(landed),mode==='baseline'?1:Math.exp(-Math.max(0,age-.015)/.2),0,0,age];});
      const gates=structuredClone(source.gates);
      for(const g of gates){if(g.id==='samples')g.value=count;if(g.id==='touchdown')g.value=count===10001?41.2:null;if(g.id==='landed')g.value=count===10001?41.25:null;g.status=gateStatus(g);g.headroom=headroom(g);}
      body[mode]={status:'failed',failure_reason:count<10001?'wind_mission_threshold':'wind_mission_support_threshold',gates,rows,
        poses:[0,rows.at(-1)[0]].map(t=>({time_s:t,position_m:[0,0,rows[Math.round(t/.005)][1]],target_m:[0,0,rows[Math.round(t/.005)][5]],quaternion_wxyz:[1,0,0,0],mission_phase:t>=41.25?'landed':'grounded'})),
        touchdown_s:count===10001?41.2:null,landed_s:count===10001?41.25:null,window:windowMetrics(rows),
        outage:p?{passed:false,recovery_passed:false,peak_distance_m:count===10001?.3:null,rmse_change_m:count===10001?0:null,landed_change_s:count===10001?1:null,recovery:[0,1].map(()=>({time_s:null,passed:false,complete:count===10001}))}:null,
        provenance:structuredClone(source.provenance)};
    }
    documents[id+'.json']=JSON.stringify(body);index.cases.push({id,cohort,profile,seed,file:id+'.json',sha256:hash(documents[id+'.json']),baseline_status:'failed',candidate_status:'failed'});
  }return {index,documents};
}
export async function routeFixture(page,options={}){
  const data=fixture(options),bytes=JSON.stringify(data.index);
  await page.route('**/descent-config.json',r=>r.fulfill({json:{baseUrl:'/test-descent/',indexSha256:hash(bytes)}}));
  await page.route('**/test-descent/**',async r=>{const file=new URL(r.request().url()).pathname.split('/').at(-1),body=file==='index.json'?bytes:data.documents[file];await r.fulfill({status:body?200:404,contentType:'application/json',body:options.corrupt&&file!=='index.json'?'{}':body??'{}'});});
  return data;
}
