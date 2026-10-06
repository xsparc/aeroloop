import test from 'node:test';
import assert from 'node:assert/strict';
import {validateApproachIndex,validateApproach,diagnostics,parseSelection,selectionHash,reviewExport} from '../dist/approach-contract.js';
import {gainParameters,validateGains} from '../dist/approach-gains.js';
import {fixture} from './approach-fixture.mjs';
const data=fixture(),index=validateApproachIndex(data.index),entry=index[6],pair=JSON.parse(data.documents[entry.file]);
test('all eighteen pairs retain failed gates, schedule and source identity',()=>{
  for(const c of index){const d=validateApproach(JSON.parse(data.documents[c.file]),c);assert.equal(d.candidate.status,'failed');}
  assert.equal(index.filter(c=>c.regressed_gates>0).length,6);
});
test('rehashed schedule, demand, cumulative metrics, gate and private metadata tampering fail closed',()=>{
  for(const mutate of [d=>d.candidate.rows[100][18]=2.5,d=>d.candidate.rows[200][20]+=.1,d=>d.candidate.rows.at(-1)[33]+=.1,d=>d.candidate.rows[1][35]=1,d=>d.candidate.provenance.host='private',d=>d.gate_changes[0].change='improved',d=>d.configuration.horizontal_position_kp=5,d=>d.candidate.gates[0].limit=1,d=>d.candidate.rows[1][0]=34.007,d=>d.candidate.poses.at(-1).position_m[0]+=1,d=>d.candidate.status='passed']){
    const d=structuredClone(pair);mutate(d);assert.throws(()=>validateApproach(d,entry));
  }
  for(const mutate of [v=>v.cases.pop(),v=>v.cases[0].file='../secret.json',v=>v.cases[0].seed=83]){const v=structuredClone(data.index);mutate(v);assert.throws(()=>validateApproachIndex(v));}
});
test('interval metrics exclude the last sample and missing coverage stays missing',()=>{
  const rows=[Array(42).fill(0),Array(42).fill(0),Array(42).fill(0)];rows[0][35]=1;rows[2][35]=1;rows[2][33]=.025;rows[2][34]=.11125;
  assert.equal(diagnostics(rows).axis_clipped_fraction,.5);assert.equal(diagnostics(rows).squared_error_integral_m2_s,.025);assert.equal(diagnostics([]).squared_error_integral_m2_s,null);
  const short=fixture({incomplete:true}),e=short.index.cases[3],v=validateApproach(JSON.parse(short.documents[e.file]),e);assert.equal(v.candidate.rows.length,0);assert.equal(v.candidate.diagnostics.complete,false);
});
test('schedule telemetry binds time and disarm',()=>{
  assert.deepEqual(gainParameters(34.5),[.5,3.25,3.1999999999999997]);validateGains([0,2.5,2.8],45,false);
  assert.throws(()=>validateGains([1,4,3.6],45,false));assert.throws(()=>validateGains([0,2.5,2.8],35,true));
});
test('review links and export bind the evidence digest and original outcomes',()=>{
  const digest='a'.repeat(64),s={id:entry.id,time:41.2,relative:true};assert.deepEqual(parseSelection(selectionHash(s,digest),digest),s);
  assert.equal(parseSelection(selectionHash(s,digest),'b'.repeat(64)),null);assert.equal(parseSelection(selectionHash({...s,time:51},digest),digest),null);
  assert.equal(parseSelection(selectionHash(s,digest)+'&case=private',digest),null);
  const v=reviewExport(validateApproach(pair,entry),s,digest);assert.equal(v.candidate.rows.length,3201);assert.equal(v.candidate.status,'failed');assert.equal(v.columns.length,42);
});
