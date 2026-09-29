import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fixture} from './outage-fixture.mjs';
import {validateDemoIndex,validatePair} from '../dist/outage-contract.js';
import {validateFeedback} from '../dist/feedback-contract.js';
test('outage demo validates all profiles, failed gates, raw capture identity and predictor modes',()=>{
  const {index,documents}=fixture();validateDemoIndex(index);
  for(const entry of index.cases)validatePair(JSON.parse(documents[entry.file]),entry);
  const entry=index.cases[12],pair=JSON.parse(documents[entry.file]);
  assert.equal(pair.candidate.status,'failed');
  for(const mutate of [p=>p.seed=2,p=>p.candidate.gates[0].limit=1,p=>p.candidate.status='passed',p=>p.candidate.samples[3].feedback.mode='capture',p=>p.candidate.samples[3].observation.age_s=0,p=>p.candidate.samples[0].feedback.private_path='private',p=>p.candidate.samples[0].quaternion_wxyz=[0,0,0,0],p=>p.candidate.samples.reverse()]){
    const bad=structuredClone(pair);mutate(bad);assert.throws(()=>validatePair(bad,entry));
  }
  for(const mutate of [d=>d.cases.pop(),d=>d.cases[0].file='../private',d=>d.cases[0].seed=2,d=>d.private_path='private']){
    const bad=structuredClone(index);mutate(bad);assert.throws(()=>validateDemoIndex(bad));
  }
  const short=fixture({incomplete:true});validatePair(JSON.parse(short.documents[short.index.cases[12].file]),short.index.cases[12]);
});
test('expired feedback requires the held raw capture',()=>{
  const observation={age_s:2.105,position_m:[0,0,1],velocity_m_s:[0,0,0]};
  const feedback={mode:'expired',position_m:[0,0,1],velocity_m_s:[0,0,0],disturbance_acceleration_m_s2:[4,0,0]};
  validateFeedback(feedback,observation);
  assert.throws(()=>validateFeedback({...feedback,mode:'predicting'},observation));
  assert.throws(()=>validateFeedback({...feedback,position_m:[1,0,1]},observation));
});
