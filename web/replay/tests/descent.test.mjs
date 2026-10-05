import test from 'node:test';
import assert from 'node:assert/strict';
import {fixture} from './descent-fixture.mjs';
import {validateDescentIndex,validateDescent,comparisonExport,selectionHash,parseSelection} from '../dist/descent-contract.js';
test('descent binds full matrix, cadence, decay, contact dwell and original gates',()=>{
  const data=fixture(),entries=validateDescentIndex(data.index),entry=entries[3],raw=JSON.parse(data.documents[entry.file]);validateDescent(raw,entry);
  for(const mutate of [d=>d.candidate.rows[8000][20]=1,d=>d.baseline.rows[8250][19]=0,d=>d.candidate.rows[8241][18]=1,d=>d.candidate.rows[8000][8]=9,d=>d.candidate.gates[0].limit=1,d=>d.candidate.outage.passed=true,d=>d.candidate.provenance.host='private',d=>d.candidate.window.vertical_velocity_error_rmse_m_s=1,d=>d.candidate.poses[1].position_m[2]=9]){
    const bad=structuredClone(raw);mutate(bad);assert.throws(()=>validateDescent(bad,entry));
  }
  const bad=structuredClone(data.index);bad.cases[0].file='../secret.json';assert.throws(()=>validateDescentIndex(bad));
});
test('selection links are version-bound and exports use each touchdown clock',()=>{
  const data=fixture(),entry=data.index.cases[3],pair=validateDescent(JSON.parse(data.documents[entry.file]),entry),digest='a'.repeat(64),selection={id:entry.id,alignment:'touchdown',time:.05};
  const hash=selectionHash(selection,digest);assert.deepEqual(parseSelection(hash,digest),selection);assert.equal(parseSelection(hash,'b'.repeat(64)),null);assert.equal(parseSelection(hash+'&url=secret',digest),null);
  const report=comparisonExport(pair,-.05,.05,'touchdown',digest);assert.equal(report.baseline.window.samples,20);assert.ok(Math.abs(report.baseline.window.start_s-41.15)<1e-9);assert.equal(report.baseline.status,'failed');assert.ok(report.baseline.gates.some(g=>g.status==='failed'));
});
test('short failed recordings keep missing contact and incomplete windows',()=>{
  const data=fixture({incomplete:true}),entry=data.index.cases[3],pair=validateDescent(JSON.parse(data.documents[entry.file]),entry);
  assert.equal(pair.candidate.touchdown_s,null);assert.equal(pair.candidate.window.complete,false);assert.equal(pair.candidate.window.vertical_velocity_error_rmse_m_s,null);assert.throws(()=>comparisonExport(pair,-1,1,'touchdown','a'.repeat(64)));
});
