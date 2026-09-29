// Synthetic display protocol fixture; never used as physics evidence.
import {readFileSync} from 'node:fs';
import {gates,hash} from './evaluation-fixture.mjs';
const profiles=['sample-hold','hold-dropout','hold-dropout-500ms','hold-dropout-1000ms','hold-dropout-2000ms'];
export function fixture({incomplete=false}={}) {
  const study=JSON.parse(readFileSync(new URL('../../../docs/evidence/isaac-outage-001.json',import.meta.url),'utf8'));
  const index={schema_version:1,kind:'outage_demo',baseline_source:'a'.repeat(40),candidate_source:'b'.repeat(40),cases:[],outcomes:study.duration_results.map(r=>({profile:r.profile,baseline:structuredClone(r),candidate:structuredClone(r)})),study_sha256:hash('{}'),display:'Synthetic protocol fixture; not flight evidence'};
  const documents={'study.json':'{}'};
  for(const [p,profile] of profiles.entries())for(const seed of [0,1,2]) {
    const row=study.results.find(r=>r.profile===profile&&r.seed===seed),duration=[0,.25,.5,1,2][p];
    const side=held=>{
      const m=structuredClone(row.metrics);
      if(incomplete){m.samples=2;m.mission.final_support=null;}
      const times=incomplete?[0,.005]:[0,17.98,18,18.1,18+duration,19,19.995,20,39.98,40,41,42,48,50].sort((a,b)=>a-b).filter((t,i,a)=>i===0||a[i-1]!==t);
      const samples=times.map(t=>{
        let source=Math.floor(Math.round(t/.005)/4)*4;
        for(const start of [18,40])if(source*.005>=start&&source*.005<start+duration)source=Math.round((start-.02)/.005);
        const age=Number((t-source*.005).toFixed(9)),position=[t/100,0,1];
        const observation={profile,source_sequence:source,source_time_s:source*.005,age_s:age,position_m:[source*.005/100,0,1],velocity_m_s:[.01,0,0]};
        const mode=held?'held':age<.02?'capture':age<=2.1?'predicting':'expired';
        return {time_s:t,position_m:position,target_m:[0,0,1.5],quaternion_wxyz:[1,0,0,0],rotor_thrust_n:[2,2,2,2],wind_velocity_m_s:[1,0,0],external_force_n:[.1,0,0],external_moment_nm:[0,0,0],mission_phase:t<2?'grounded':t<40?'hover':'landing',contact_normal_force_n:[0,0,0],support_clearance_m:.95,observation,
          feedback:{mode,position_m:mode==='predicting'?position:observation.position_m,velocity_m_s:observation.velocity_m_s,disturbance_acceleration_m_s2:[0,0,0]}};
      });
      return {status:incomplete?'failed':row.status,failure_reason:incomplete?'wind_mission_threshold':row.failure_reason,metrics:m,gates:gates(m),samples};
    };
    const pair={schema_version:1,kind:'outage_demo_pair',profile,seed,baseline:side(true),candidate:side(false)},file=`p${p}-s${seed}.json`;
    documents[file]=JSON.stringify(pair);index.cases.push({profile,seed,file,sha256:hash(documents[file]),baseline_status:pair.baseline.status,candidate_status:pair.candidate.status});
  }
  if(incomplete)for(const row of index.outcomes)for(const name of ['baseline','candidate'])Object.assign(row[name],{mission_passes:0,accepted:false});
  return {index,documents};
}
export async function routeFixture(page,options={}) {
  const data=fixture(options),bytes=JSON.stringify(data.index);
  await page.route('**/outage-config.json',r=>r.fulfill({json:{baseUrl:'/test-outage/',indexSha256:hash(bytes)}}));
  await page.route('**/test-outage/**',async r=>{
    const file=new URL(r.request().url()).pathname.split('/test-outage/')[1];
    if(options.delay&&file==='p4-s0.json')await new Promise(resolve=>setTimeout(resolve,350));
    const body=file==='index.json'?bytes:data.documents[file];
    await r.fulfill({status:body?200:404,contentType:'application/json',body:options.corrupt&&file.endsWith('s0.json')?'{}':body??'{}'}).catch(()=>{});
  });return data;
}
