// Synthetic protocol fixtures; never measured physics evidence.
import {fixture as diagnosisFixture} from './diagnosis-fixture.mjs';
import {hash} from './evaluation-fixture.mjs';
import {gateStatus} from '../dist/evaluation-contract.js';
import {headroom} from '../dist/diagnosis-contract.js';
import {COLUMNS,CONFIGURATION,COHORTS,SEEDS,diagnostics,gateChanges} from '../dist/approach-contract.js';
import {gainParameters} from '../dist/approach-gains.js';
export function fixture({incomplete=false}={}){
  const source=JSON.parse(diagnosisFixture().documents['q3-p1-s0.json']);
  const documents={},index={schema_version:1,kind:'approach_comparison_index',cases:[]};
  for(const [ci,cohort] of COHORTS.entries())for(const [p,profile] of ['sample-hold','hold-dropout-2000ms'].entries())for(const seed of SEEDS[ci]){
    const id=`${cohort}-p${p}-s${seed}`,body={schema_version:1,kind:'approach_comparison',id,cohort,profile,seed,columns:COLUMNS,configuration:CONFIGURATION};
    for(const mode of ['baseline','candidate']){
      const count=incomplete&&p?0:3201,rows=[];
      for(let i=0;i<count;i++){
        const t=Number((34+i*.005).toFixed(9)),contact=t>=41.2,landed=t>=41.25,armed=!landed,x=.2,y=.1,vx=-.1,z=contact?.06:1;
        const gains=mode==='candidate'?gainParameters(t,armed):[0,2.5,2.8],demand=armed?[-gains[1]*x+gains[2]*.1+.1,-gains[1]*y]:[0,0],prev=rows[i-1],dt=i?t-prev[0]:0;
        rows.push([t,x,y,vx,0,x,y,vx,0,0,0,0,0,armed?.1:0,0,0,0,...gains,...demand,1,0,0,0,0,contact?10:0,contact?.01:.95,0,Number(landed),Math.hypot(x,y),.1,
          i?prev[33]+prev[31]**2*dt:0,i?prev[34]+(prev[20]**2+prev[21]**2)*dt:0,0,.005,0,z,armed?9.8:0,armed?9.8:0,z]);
      }
      const gates=structuredClone(source.gates);
      for(const g of gates){if(g.id==='samples')g.value=count?10001:100;if(g.id==='touchdown')g.value=count?41.2:null;if(g.id==='landed')g.value=count?41.25:null;
        if(g.id==='tilt'&&cohort==='regression'&&mode==='candidate')g.value=26;
        g.status=gateStatus(g);g.headroom=headroom(g);}
      body[mode]={status:'failed',failure_reason:count?'wind_mission_support_threshold':'wind_mission_threshold',gates,rows,
        poses:count?[{time_s:0,position_m:[0,0,1],target_m:[0,0,1],quaternion_wxyz:[1,0,0,0],mission_phase:'grounded'},...rows.filter((r,i)=>i%40===0).map(r=>({time_s:r[0],position_m:[r[1],r[2],r[38]],target_m:[0,0,r[41]],quaternion_wxyz:[1,0,0,0],mission_phase:r[30]?'landed':'landing'}))]:[0,.495].map(t=>({time_s:t,position_m:[0,0,1],target_m:[0,0,1],quaternion_wxyz:[1,0,0,0],mission_phase:'grounded'})),
        touchdown_s:count?41.2:null,landed_s:count?41.25:null,diagnostics:diagnostics(rows),
        outage:p?{passed:false,recovery_passed:false,peak_distance_m:count?.3:null,rmse_change_m:count?0:null,landed_change_s:count?1:null,recovery:[0,1].map(()=>({time_s:null,passed:false,complete:!!count}))}:null,
        provenance:structuredClone(source.provenance)};
    }
    body.gate_changes=gateChanges(body.baseline.gates,body.candidate.gates);
    documents[id+'.json']=JSON.stringify(body);index.cases.push({id,cohort,profile,seed,file:id+'.json',sha256:hash(documents[id+'.json']),baseline_status:'failed',candidate_status:'failed',regressed_gates:body.gate_changes.filter(g=>g.change==='regressed').length,improved_gates:0});
  }return {index,documents};
}
export async function routeFixture(page,options={}){
  const data=fixture(options),bytes=JSON.stringify(data.index);
  await page.route('**/approach-config.json',r=>r.fulfill({json:{baseUrl:'/test-approach/',indexSha256:hash(bytes)}}));
  await page.route('**/test-approach/**',async r=>{const file=new URL(r.request().url()).pathname.split('/').at(-1),body=file==='index.json'?bytes:data.documents[file];if(options.delay===file)await new Promise(resolve=>setTimeout(resolve,700));await r.fulfill({status:body?200:404,contentType:'application/json',body:options.corrupt&&file!=='index.json'?'{}':body??'{}'}).catch(()=>{});});
  return data;
}
