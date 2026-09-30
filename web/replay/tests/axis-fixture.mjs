// Synthetic display contract fixture, never measured flight evidence.
import {fixture as outageFixture} from './outage-fixture.mjs';
import {hash} from './evaluation-fixture.mjs';
export function fixture({incomplete=false}={}) {
  const old=outageFixture({incomplete}),profile='hold-dropout-2000ms';
  const cohorts=[{id:'regression',seeds:[0,1,2],profiles:[profile],baseline_source:'a'.repeat(40),candidate_source:'b'.repeat(40)},{id:'prior-validation',seeds:[101,202,303],profiles:[profile],baseline_source:'c'.repeat(40),candidate_source:'b'.repeat(40)}];
  const index={...old.index,schema_version:3,kind:'axis_demo',cohorts,cases:[],outcomes:[]},documents={'study.json':'{}'};
  for(const [c,cohort] of cohorts.entries())for(const [a,axes] of ['vertical','horizontal'].entries()) {
    const outcome=structuredClone(old.index.outcomes.find(o=>o.profile===profile));outcome.baseline=structuredClone(outcome.candidate);
    index.outcomes.push({...outcome,cohort:cohort.id,fresh_axis:axes});
    for(const [j,seed] of cohort.seeds.entries()) {
      const entry=old.index.cases.find(e=>e.profile===profile&&e.seed===j),original=JSON.parse(old.documents[entry.file]);
      const pair={...original,schema_version:3,kind:'axis_demo_pair',cohort:cohort.id,fresh_axis:axes,seed,baseline:structuredClone(original.candidate)};
      for(const s of pair.candidate.samples) {
        const sequence=Math.round(s.time_s/.005),source=Math.floor(sequence/4)*4,selected=i=>axes==='vertical'?i===2:i<2;
        s.axis_observation={available_axes:axes,source_sequence:source,source_time_s:source*.005,age_s:(sequence-source)*.005,position_m:s.position_m.map((v,i)=>selected(i)?v:null),velocity_m_s:[0,0,0].map((v,i)=>selected(i)?v:null)};
        s.axis_feedback={mode:axes+'-fresh',...Object.fromEntries(['position_m','velocity_m_s'].map(k=>[k,s.feedback[k].map((v,i)=>selected(i)?s.axis_observation[k][i]:v)]))};
      }
      const file=`c${c}-a${a}-s${j}.json`;documents[file]=JSON.stringify(pair);
      index.cases.push({...entry,cohort:cohort.id,fresh_axis:axes,seed,file,sha256:hash(documents[file]),baseline_status:pair.baseline.status});
    }
  }return {index,documents};
}
export async function routeFixture(page,options={}) {
  const data=fixture(options),bytes=JSON.stringify(data.index);
  await page.route('**/axis-config.json',r=>r.fulfill({json:{baseUrl:'/test-axis/',indexSha256:hash(bytes)}}));
  await page.route('**/test-axis/**',async r=>{
    const file=new URL(r.request().url()).pathname.split('/test-axis/')[1];
    if(options.delay&&file==='c0-a0-s0.json')await new Promise(resolve=>setTimeout(resolve,350));
    const body=file==='index.json'?bytes:data.documents[file];
    await r.fulfill({status:body?200:404,contentType:'application/json',body:options.corrupt&&file.startsWith('c')?'{}':body??'{}'}).catch(()=>{});
  });return data;
}
