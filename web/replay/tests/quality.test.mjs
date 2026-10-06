import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fixture} from './quality-fixture.mjs';
import {validateDemoIndex,validatePair} from '../dist/outage-contract.js';
import {validateLive} from '../dist/live-contract.js';
import {liveFixture} from './live-fixture.mjs';

test('quality demo binds all modes and both delivered horizontal channels',()=>{
  const {index,documents}=fixture();validateDemoIndex(index);
  for(const entry of index.cases)validatePair(JSON.parse(documents[entry.file]),entry);
  for(const mutate of [d=>d.cases[0].quality='ideal',d=>d.cases[0].file='../private',d=>d.cases.pop(),d=>d.outcomes[0].candidate.mission_passes=3,d=>d.baseline_source='a'.repeat(40),d=>d.cases[0].cohort='unseen']) {
    const bad=structuredClone(index);mutate(bad);assert.throws(()=>validateDemoIndex(bad));
  }
  const entry=index.cases[6],pair=JSON.parse(documents[entry.file]);
  for(const mutate of [p=>p.quality='noise',p=>p.candidate.samples[1].axis_observation.age_s=0,p=>p.candidate.samples[0].axis_observation.quality='ideal',p=>p.baseline.samples[0].axis_observation.quality='noise-delay',p=>p.candidate.samples[0].axis_observation.position_m[2]=0,p=>p.candidate.samples[0].axis_feedback.position_m[2]=99,p=>p.candidate.samples[0].axis_observation.private_path='private',p=>delete p.baseline.samples[0].axis_feedback]) {
    const bad=structuredClone(pair);mutate(bad);assert.throws(()=>validatePair(bad,entry));
  }
  const short=fixture({incomplete:true});validateDemoIndex(short.index);validatePair(JSON.parse(short.documents[short.index.cases[0].file]),short.index.cases[0]);
});
test('live v7 distinguishes noise and delay from ideal availability',()=>{
  const {index,documents}=fixture(),s=JSON.parse(documents[index.cases[6].file]).candidate.samples.find(s=>s.time_s===41);
  const live=liveFixture(8200);Object.assign(live,{schema_version:7,physics_dt_s:.005,observation_profile:s.observation.profile});
  for(const k of ['observation','feedback','axis_observation','axis_feedback'])live.sample[k]=s[k];
  validateLive(live);assert.equal(live.sample.axis_observation.age_s,.04);
  for(const mutate of [v=>v.sample.axis_observation.age_s=.02,v=>v.sample.axis_feedback.mode='horizontal-fresh',v=>v.sample.axis_observation.available_axes='vertical',v=>v.schema_version=6,v=>delete v.sample.axis_observation.quality]) {
    const bad=structuredClone(live);mutate(bad);assert.throws(()=>validateLive(bad));
  }
});

test('live v8 validates decay arithmetic and rejects older schema aliases',()=>{
  const {index,documents}=fixture(),s=JSON.parse(documents[index.cases[6].file]).candidate.samples.find(s=>s.time_s===41);
  const live=liveFixture(8200);Object.assign(live,{schema_version:8,physics_dt_s:.005,observation_profile:s.observation.profile});
  for(const k of ['observation','feedback','axis_observation','axis_feedback'])live.sample[k]=s[k];
  const scale=Math.exp(-Math.max(0,s.observation.age_s-.015)/.2);
  live.sample.vertical_decay={kind:'vertical-disturbance-decay-v1',scale,anchor_z_m_s2:0,effective_z_m_s2:0};
  live.sample.feedback.disturbance_acceleration_m_s2[2]=0;validateLive(live);
  for(const change of [v=>v.schema_version=7,v=>v.sample.vertical_decay.scale=1,v=>v.sample.vertical_decay.anchor_z_m_s2=1,v=>v.sample.vertical_decay.host='private']){
    const bad=structuredClone(live);change(bad);assert.throws(()=>validateLive(bad));
  }
});

test('live v9 binds the armed approach schedule without weakening v8',()=>{
  const {index,documents}=fixture(),s=JSON.parse(documents[index.cases[6].file]).candidate.samples.find(s=>s.time_s===41);
  const live=liveFixture(8200);Object.assign(live,{schema_version:9,physics_dt_s:.005,observation_profile:s.observation.profile});
  for(const k of ['observation','feedback','axis_observation','axis_feedback'])live.sample[k]=s[k];
  const scale=Math.exp(-Math.max(0,s.observation.age_s-.015)/.2);
  live.sample.vertical_decay={kind:'vertical-disturbance-decay-v1',scale,anchor_z_m_s2:0,effective_z_m_s2:0};
  live.sample.feedback.disturbance_acceleration_m_s2[2]=0;live.sample.approach_control=[1,4,3.6];validateLive(live);
  for(const change of [v=>v.schema_version=8,v=>v.sample.approach_control=[0,2.5,2.8],v=>v.sample.mission_phase='landed',v=>v.sample.approach_control=[1,4,NaN]]){
    const bad=structuredClone(live);change(bad);assert.throws(()=>validateLive(bad));
  }
  live.sample.mission_phase='landed';live.sample.approach_control=[0,2.5,2.8];validateLive(live);
});
