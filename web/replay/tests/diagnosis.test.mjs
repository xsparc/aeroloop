import test from 'node:test';
import assert from 'node:assert/strict';
import {fixture} from './diagnosis-fixture.mjs';
import {validateDiagnosisIndex,validateDiagnosis,validateDiagnosisPair,windowCsv} from '../dist/diagnosis-contract.js';
test('diagnosis enforces matrix, numeric payload, gates, phase arithmetic and recovery',()=>{
  const data=fixture(),cases=validateDiagnosisIndex(data.index),entry=cases[21],refEntry=cases[18];
  const raw=JSON.parse(data.documents[entry.file]),ref=validateDiagnosis(JSON.parse(data.documents[refEntry.file]),refEntry),flight=validateDiagnosis(raw,entry);validateDiagnosisPair(ref,flight);
  for(const change of [v=>v.rows[1][0]=0,v=>v.rows[1][1]=99,v=>v.phase_errors.groups[0].vertical_peak_m=1,v=>v.gates.at(-1).limit=9,v=>v.gates.at(-1).headroom=1,v=>v.provenance.private_path='secret',v=>v.poses[1].quaternion_wxyz=[2,0,0,0]]){
    const bad=structuredClone(raw);change(bad);assert.throws(()=>validateDiagnosis(bad,entry));
  }
  for(const change of [v=>v.comparison.recovery_windows[0].recovery_time_s=.1,v=>v.comparison.passed=false,v=>v.comparison.private_path='secret',v=>v.provenance.source_commit='c'.repeat(40)]){
    const bad=structuredClone(raw);change(bad);assert.throws(()=>validateDiagnosisPair(ref,validateDiagnosis(bad,entry)));
  }
  const bad=structuredClone(data.index);bad.cases[0].file='../private.json';assert.throws(()=>validateDiagnosisIndex(bad));
  assert.equal(flight.status,'failed');assert.ok(flight.gates.at(-1).headroom<0);
});
test('diagnosis preserves incomplete coverage and distinguishes reference to self',()=>{
  const data=fixture({incomplete:true}),cases=validateDiagnosisIndex(data.index),entry=cases[21],refEntry=cases[18];
  const ref=validateDiagnosis(JSON.parse(data.documents[refEntry.file]),refEntry),flight=validateDiagnosis(JSON.parse(data.documents[entry.file]),entry);
  validateDiagnosisPair(ref,flight);validateDiagnosisPair(ref,ref);assert.equal(flight.phase_errors.complete,false);assert.equal(flight.comparison.recovery_passed,false);assert.equal(ref.comparison,null);
  flight.comparison.recovery_windows[0].complete_horizon=true;assert.throws(()=>validateDiagnosisPair(ref,flight));
});
test('CSV includes every original sample in an inclusive bounded numeric window',()=>{
  const data=fixture(),entry=data.index.cases[21],flight=validateDiagnosis(JSON.parse(data.documents[entry.file]),entry);
  const csv=windowCsv(flight,40,42),lines=csv.trim().split('\r\n');assert.equal(lines.length,402);assert.equal(Number(lines[1].split(',')[0]),40);assert.equal(Number(lines.at(-1).split(',')[0]),42);
  assert.ok(lines.slice(1).every(l=>l.split(',').every(v=>Number.isFinite(Number(v)))));assert.throws(()=>windowCsv(flight,42,40));
});
