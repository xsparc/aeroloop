import test from "node:test";
import assert from "node:assert/strict";
import {sampleAt,validateReplay} from "./viewer.js";
const samples=[{time_s:0,position_m:[0,0,1],target_m:[0,0,1],quaternion_wxyz:[1,0,0,0]},{time_s:1,position_m:[1,0,1],target_m:[1,0,1],quaternion_wxyz:[1,0,0,0]}];
const replay=()=>({schema_version:1,kind:"recorded_simulation",run_id:"cpu-hover-0-123456abcdef",samples:structuredClone(samples)});
test("interpolates position without anticipating a target step",()=>{assert.deepEqual(sampleAt(samples,.5).position,[.5,0,1]);assert.deepEqual(sampleAt(samples,.5).target,[0,0,1]);assert.deepEqual(sampleAt(samples,1).target,[1,0,1]);});
test("bounds endpoints",()=>{assert.deepEqual(sampleAt(samples,-1).position,[0,0,1]);assert.deepEqual(sampleAt(samples,10).position,[1,0,1]);});
test("validates timestamps, finite vectors and unit quaternion",()=>{validateReplay(replay());for(const change of [r=>r.samples[1].time_s=0,r=>r.samples[0].position_m[0]=NaN,r=>r.samples[0].quaternion_wxyz=[0,0,0,0],r=>r.run_id="../../private"]){const r=replay();change(r);assert.throws(()=>validateReplay(r));}});
