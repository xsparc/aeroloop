import test from 'node:test';
import assert from 'node:assert/strict';
import {validateLive, historyAppend} from '../dist/live-contract.js';

export function liveFixture(sequence=0) {
  return {schema_version:1,state:'running',seed:0,physics_dt_s:.0025,paced:true,elapsed_s:sequence*.005,
    lag_s:0,max_lag_s:0,late_steps:0,age_s:0,stale:false,
    sample:{time_s:sequence*.005,sequence,position_m:[0,0,1.5],velocity_m_s:[0,0,0],quaternion_wxyz:[1,0,0,0],
      target_m:[0,0,1.5],rates_rad_s:[0,0,0],rate_setpoint_rad_s:[0,0,0],effort_normalized:[0,0,0],
      rotor_thrust_n:[2.45,2.45,2.45,2.45],allocation_scale:1,wind_velocity_m_s:[1,0,0],external_force_n:[.1,0,0],
      mission_phase:'hover',contact_normal_force_n:[0,0,0],support_clearance_m:1.45}};
}
test('live contracts reject host metadata and malformed/nonfinite states',()=>{
  assert.equal(validateLive(liveFixture()).state,'running');
  for (const mutate of [v=>v.host='private',v=>v.sample.position_m[0]=NaN,v=>v.sample.time_s=4,v=>v.physics_dt_s='.005',v=>v.sample.quaternion_wxyz=[0,0,0,0]]) {
    const v=liveFixture();mutate(v);assert.throws(()=>validateLive(v));
  }
});
test('live history stays bounded, deduplicates polls and rejects regressions',()=>{
  let h=[];
  for(let i=0;i<500;i++) h=historyAppend(h,liveFixture(i).sample);
  assert.equal(h.length,300);assert.equal(h[0].sequence,200);
  assert.equal(historyAppend(h,liveFixture(499).sample),h);
  assert.throws(()=>historyAppend(h,liveFixture(0).sample));
});


test('observation telemetry binds source age and profile without accepting private data',()=>{
  const good=liveFixture(1000);good.schema_version=2;good.physics_dt_s=.005;good.observation_profile='noise-delay';
  good.sample.observation={profile:'noise-delay',source_sequence:992,source_time_s:4.96,age_s:.04,position_m:[.01,0,1.5],velocity_m_s:[0,0,0]};
  assert.equal(validateLive(good).sample.observation.age_s,.04);
  for (const mutate of [v=>v.observation_profile='ideal',v=>v.sample.observation.source_sequence=1000,v=>v.sample.observation.age_s=0,v=>v.sample.observation.private_path='private',v=>v.schema_version=1]) {
    const bad=structuredClone(good);mutate(bad);assert.throws(()=>validateLive(bad));
  }
});


test('capture timing validates both outage edges and rejects legacy-version aliases',()=>{
  for(const [sequence,source,age] of [[3599,3596,.015],[3600,3596,.02],[3651,3596,.275],[3652,3652,0],[8040,7996,.22],[8052,8052,0]]) {
    const good=liveFixture(sequence);good.schema_version=3;good.physics_dt_s=.005;good.observation_profile='hold-dropout';
    good.sample.observation={profile:'hold-dropout',source_sequence:source,source_time_s:source*.005,age_s:age,position_m:[0,0,1.5],velocity_m_s:[0,0,0]};
    assert.equal(validateLive(good).sample.observation.age_s,age);
    for(const mutate of [v=>v.schema_version=2,v=>v.observation_profile='dropout',v=>v.sample.observation.source_sequence++,v=>v.sample.observation.age_s+=.005]) {
      const bad=structuredClone(good);mutate(bad);assert.throws(()=>validateLive(bad));
    }
  }
});
