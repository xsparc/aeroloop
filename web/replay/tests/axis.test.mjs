import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fixture} from './axis-fixture.mjs';
import {validateDemoIndex,validatePair} from '../dist/outage-contract.js';
import {validateLive} from '../dist/live-contract.js';
import {liveFixture} from './live-fixture.mjs';
test('axis demo binds cohorts, choices and unavailable capture components',()=>{
  const {index,documents}=fixture();validateDemoIndex(index);
  for(const entry of index.cases)validatePair(JSON.parse(documents[entry.file]),entry);
  for(const mutate of [d=>d.cohorts[1].id='unseen',d=>d.cases[0].fresh_axis='all',d=>d.cases[0].file='../private',d=>d.cases.pop(),d=>d.outcomes[0].candidate.mission_passes=3]) {
    const bad=structuredClone(index);mutate(bad);assert.throws(()=>validateDemoIndex(bad));
  }
  const entry=index.cases[0],pair=JSON.parse(documents[entry.file]);
  for(const mutate of [p=>p.fresh_axis='horizontal',p=>p.candidate.samples[0].axis_observation.position_m[0]=0,p=>p.candidate.samples[0].axis_observation.source_sequence=4,p=>p.candidate.samples[0].axis_feedback.position_m[0]=99,p=>p.candidate.samples[0].axis_observation.private_path='private',p=>delete p.candidate.samples[0].axis_feedback]) {
    const bad=structuredClone(pair);mutate(bad);assert.throws(()=>validatePair(bad,entry));
  }
  const short=fixture({incomplete:true});validateDemoIndex(short.index);validatePair(JSON.parse(short.documents[short.index.cases[0].file]),short.index.cases[0]);
});
test('live axis feedback retains raw predictor and validates actual composite',()=>{
  const {index,documents}=fixture(),s=JSON.parse(documents[index.cases[0].file]).candidate.samples.find(s=>s.time_s===41);
  const live=liveFixture(8200);Object.assign(live,{schema_version:6,physics_dt_s:.005,observation_profile:s.observation.profile});
  for(const k of ['observation','feedback','axis_observation','axis_feedback'])live.sample[k]=s[k];
  validateLive(live);assert.equal(live.sample.axis_feedback.mode,'vertical-fresh');
  for(const mutate of [v=>v.sample.axis_observation.age_s=.02,v=>v.sample.axis_feedback.mode='capture',v=>v.sample.axis_feedback.velocity_m_s[0]=99,v=>v.schema_version=4]) {
    const bad=structuredClone(live);mutate(bad);assert.throws(()=>validateLive(bad));
  }
});
