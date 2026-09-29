// Display protocol fixture only; never flight evidence.
import {fixture as outageFixture} from './outage-fixture.mjs';
import {hash} from './evaluation-fixture.mjs';
export function fixture({incomplete=false}={}) {
  const old=outageFixture({incomplete}),source='b'.repeat(40);
  const cohorts=[{id:'regression',seeds:[0,1,2],profiles:['sample-hold','hold-dropout-500ms','hold-dropout-1000ms','hold-dropout-2000ms'],baseline_source:'a'.repeat(40),candidate_source:source},{id:'unseen',seeds:[101,202,303],profiles:['sample-hold','hold-dropout-2000ms'],baseline_source:source,candidate_source:source}];
  const index={...old.index,schema_version:2,kind:'landing_demo',cohorts,cases:[],outcomes:[]},documents={'study.json':'{}'};
  for(const [c,cohort] of cohorts.entries())for(const [p,profile] of cohort.profiles.entries()) {
    index.outcomes.push({...structuredClone(old.index.outcomes.find(r=>r.profile===profile)),cohort:cohort.id});
    for(const [j,seed] of cohort.seeds.entries()) {
      const entry=old.index.cases.find(r=>r.profile===profile&&r.seed===j),original=JSON.parse(old.documents[entry.file]);
      const pair={...original,schema_version:2,kind:'landing_demo_pair',cohort:cohort.id,seed,baseline:structuredClone(original.candidate)};
      for(const s of pair.candidate.samples) {
        const active=profile.includes('1000')||profile.includes('2000');
        const activated=active&&s.time_s>=41,resumed=activated&&s.time_s>=48;
        s.landing_guard={mode:resumed?'descending':activated?'holding':'inactive',activated_at_s:activated?41:null,resumed_at_s:resumed?48:null,stable_for_s:0,target_m:activated?[0,0,.3]:s.target_m,target_velocity_m_s:[0,0,0],target_acceleration_m_s2:[0,0,0]};
      }
      const file=`c${c}-p${p}-s${j}.json`;documents[file]=JSON.stringify(pair);
      index.cases.push({...entry,cohort:cohort.id,seed,file,sha256:hash(documents[file])});
    }
  }return {index,documents};
}
export async function routeFixture(page,options={}) {
  const data=fixture(options),bytes=JSON.stringify(data.index);
  await page.route('**/landing-config.json',r=>r.fulfill({json:{baseUrl:'/test-landing/',indexSha256:hash(bytes)}}));
  await page.route('**/test-landing/**',async r=>{
    const file=new URL(r.request().url()).pathname.split('/test-landing/')[1];
    if(options.delay&&file==='c0-p3-s0.json')await new Promise(resolve=>setTimeout(resolve,350));
    const body=file==='index.json'?bytes:data.documents[file];
    await r.fulfill({status:body?200:404,contentType:'application/json',body:options.corrupt&&file.startsWith('c')?'{}':body??'{}'}).catch(()=>{});
  });return data;
}
