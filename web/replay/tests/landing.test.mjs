import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fixture} from './landing-fixture.mjs';
import {validateDemoIndex,validatePair} from '../dist/outage-contract.js';
import {validateGuard} from '../dist/landing-contract.js';
import {validateLive} from '../dist/live-contract.js';
import {liveFixture} from './live-fixture.mjs';
test('landing demo binds cohort identity, unseen seeds and distinct commands',()=>{
  const {index,documents}=fixture();validateDemoIndex(index);
  for(const entry of index.cases)validatePair(JSON.parse(documents[entry.file]),entry);
  for(const mutate of [d=>d.cohorts[1].seeds[0]=0,d=>d.cohorts[1].baseline_source='c'.repeat(40),d=>d.cases[12].cohort='regression',d=>d.cases[12].seed=0,d=>d.cases[0].file='../private',d=>d.outcomes[5].candidate.mission_passes=3,d=>d.cases.pop()]) {
    const bad=structuredClone(index);mutate(bad);assert.throws(()=>validateDemoIndex(bad));
  }
  const entry=index.cases[9],pair=JSON.parse(documents[entry.file]);
  for(const mutate of [p=>p.cohort='unseen',p=>p.candidate.samples.at(-1).landing_guard.resumed_at_s=51,p=>p.candidate.samples[0].landing_guard.private_path='private',p=>p.candidate.gates[0].limit=1,p=>delete p.candidate.samples[0].landing_guard]) {
    const bad=structuredClone(pair);mutate(bad);assert.throws(()=>validatePair(bad,entry));
  }
  const short=fixture({incomplete:true});validateDemoIndex(short.index);validatePair(JSON.parse(short.documents[short.index.cases[9].file]),short.index.cases[9]);
});
test('live landing state rejects malformed transitions and preserves original targets',()=>{
  const {index,documents}=fixture(),sample=JSON.parse(documents[index.cases[9].file]).candidate.samples.find(s=>s.time_s===41);
  const live=liveFixture(8200);Object.assign(live,{schema_version:5,physics_dt_s:.005,observation_profile:sample.observation.profile});
  Object.assign(live.sample,{observation:sample.observation,feedback:sample.feedback,landing_guard:sample.landing_guard});
  validateLive(live);assert.equal(live.sample.target_m[2],1.5);assert.equal(live.sample.landing_guard.target_m[2],.3);
  for(const mutate of [g=>g.mode='inactive',g=>g.resumed_at_s=40,g=>g.target_m=[NaN,0,0],g=>g.stable_for_s=.301]) {
    const bad=structuredClone(sample.landing_guard);mutate(bad);assert.throws(()=>validateGuard(bad,41));
  }
  live.schema_version=4;assert.throws(()=>validateLive(live));
});
