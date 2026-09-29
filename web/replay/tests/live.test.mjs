import test from 'node:test';
import assert from 'node:assert/strict';
import {validateLive, historyAppend} from '../dist/live-contract.js';
import {outageActive, outageWindows} from '../dist/observation-contract.js';

export function liveFixture(sequence=0) {
  return {schema_version:1,state:'running',seed:0,physics_dt_s:.0025,paced:true,elapsed_s:sequence*.005,
    lag_s:0,max_lag_s:0,late_steps:0,age_s:0,stale:false,
    sample:{time_s:sequence*.005,sequence,position_m:[0,0,1.5],velocity_m_s:[0,0,0],quaternion_wxyz:[1,0,0,0],
      target_m:[0,0,1.5],rates_rad_s:[0,0,0],rate_setpoint_rad_s:[0,0,0],effort_normalized:[0,0,0],
      rotor_thrust_n:[2.45,2.45,2.45,2.45],allocation_scale:1,wind_velocity_m_s:[1,0,0],external_force_n:[.1,0,0],
      mission_phase:'hover',contact_normal_force_n:[0,0,0],support_clearance_m:1.45}};
}

test('long outage profiles hold until their own end and reject a shorter-profile alias',()=>{
  for(const [profile,duration] of [['hold-dropout-500ms',.5],['hold-dropout-1000ms',1],['hold-dropout-2000ms',2]]) {
    assert.deepEqual(outageWindows(profile),[[18,18+duration],[40,40+duration]]);
    for(const start of [18,40])for(const t of [start,start+duration-.005,start+duration]) {
      const sequence=Math.round(t/.005), source=t<start+duration?Math.round((start-.02)/.005):sequence;
      const good=liveFixture(sequence);good.schema_version=3;good.physics_dt_s=.005;good.observation_profile=profile;
      good.sample.observation={profile,source_sequence:source,source_time_s:source*.005,age_s:(sequence-source)*.005,position_m:[0,0,1.5],velocity_m_s:[0,0,0]};
      assert.equal(validateLive(good).sample.observation.source_sequence,source);
      assert.equal(outageActive(t,profile),t<start+duration);
      const bad=structuredClone(good);bad.sample.observation.source_sequence++;
      assert.throws(()=>validateLive(bad));
      if(t>start&&t<start+duration) {
        const alias=structuredClone(good);alias.observation_profile='hold-dropout';alias.sample.observation.profile='hold-dropout';
        assert.throws(()=>validateLive(alias));
      }
    }
  }
});
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


test('predictive live packets preserve raw capture age and reject feedback aliases',()=>{
  const packet=liveFixture(3800);packet.schema_version=4;packet.physics_dt_s=.005;packet.observation_profile='hold-dropout-2000ms';
  packet.sample.observation={profile:packet.observation_profile,source_sequence:3596,source_time_s:17.98,age_s:1.02,position_m:[0,0,1],velocity_m_s:[0,0,0]};
  packet.sample.feedback={mode:'predicting',position_m:[1,0,1],velocity_m_s:[1,0,0],disturbance_acceleration_m_s2:[0,0,0]};
  validateLive(packet);
  for(const mutate of [p=>p.schema_version=3,p=>p.sample.feedback.mode='capture',p=>p.sample.feedback.position_m=[NaN,0,0],p=>p.sample.feedback.private_path='private']) {
    const bad=structuredClone(packet);mutate(bad);assert.throws(()=>validateLive(bad));
  }
});
