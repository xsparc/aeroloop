// Synthetic display-contract fixtures, never measured flight evidence.
import {fixture as axisFixture} from './axis-fixture.mjs';
import {hash} from './evaluation-fixture.mjs';
export function fixture(options={}) {
  const old=axisFixture(options),profile='hold-dropout-2000ms';
  const index={schema_version:4,kind:'quality_demo',cases:[],outcomes:[],study_sha256:hash('{}'),baseline_source:'b'.repeat(40),candidate_source:'b'.repeat(40),display:old.index.display},documents={'study.json':'{}'};
  for(const [q,quality] of ['noise','delay','noise-delay'].entries()) {
    const outcome=structuredClone(old.index.outcomes.find(o=>o.cohort==='regression'&&o.fresh_axis==='horizontal'));
    delete outcome.cohort;delete outcome.fresh_axis;outcome.baseline=structuredClone(outcome.candidate);
    index.outcomes.push({...outcome,quality});
    for(let seed=0;seed<3;seed++) {
      const entry=old.index.cases.find(c=>c.cohort==='regression'&&c.fresh_axis==='horizontal'&&c.seed===seed);
      const original=JSON.parse(old.documents[entry.file]);
      const pair={schema_version:4,kind:'quality_demo_pair',quality,profile,seed,baseline:structuredClone(original.candidate),candidate:structuredClone(original.candidate)};
      for(const side of ['baseline','candidate'])for(const s of pair[side].samples) {
        const mode=side==='baseline'?'ideal':quality,sequence=Math.round(s.time_s/.005),source=Math.floor(Math.max(0,sequence-(mode.includes('delay')?8:0))/4)*4;
        Object.assign(s.axis_observation,{quality:mode,source_sequence:source,source_time_s:source*.005,age_s:(sequence-source)*.005});
        s.axis_feedback.mode='horizontal-'+mode;
      }
      const file=`q${q}-s${seed}.json`;documents[file]=JSON.stringify(pair);
      index.cases.push({quality,profile,seed,file,sha256:hash(documents[file]),baseline_status:pair.baseline.status,candidate_status:pair.candidate.status});
    }
  }return {index,documents};
}
export async function routeFixture(page,options={}) {
  const data=fixture(options),bytes=JSON.stringify(data.index);
  await page.route('**/quality-config.json',r=>r.fulfill({json:{baseUrl:'/test-quality/',indexSha256:hash(bytes)}}));
  await page.route('**/test-quality/**',async r=>{
    const file=new URL(r.request().url()).pathname.split('/test-quality/')[1];
    if(options.delay&&file==='q2-s0.json')await new Promise(resolve=>setTimeout(resolve,350));
    const body=file==='index.json'?bytes:data.documents[file];
    await r.fulfill({status:body?200:404,contentType:'application/json',body:options.corrupt&&file.startsWith('q')?'{}':body??'{}'}).catch(()=>{});
  });return data;
}
