import test from 'node:test';
import assert from 'node:assert/strict';
import {validateEvaluation,loadEvaluationRecording} from '../dist/evaluation-contract.js';
import {fixture,hash} from './evaluation-fixture.mjs';

test('evaluation preserves full matrix, failed gates and incomplete comparisons',()=>{
  assert.equal(validateEvaluation(fixture().data).study.accepted,true);
  assert.equal(validateEvaluation(fixture({failed:true}).data).study.passed,8);
  assert.equal(validateEvaluation(fixture({incomplete:true}).data).study.accepted,false);
  for(const mutate of [
    d=>d.cases.pop(), d=>d.cases[0].gates.pop(), d=>d.cases[0].gates[0].value=null,
    d=>d.cases[0].gates[0].limit=NaN, d=>d.cases[0].run_id='../private',
    d=>d.cases[0].gates.find(g=>g.id==='rmse').limit=1,
    d=>d.cases[0].gates.find(g=>g.id==='rmse').value=0,
    d=>d.cases[0].run_id=d.cases[1].run_id, d=>d.study.passed=8,
    d=>d.study.comparisons[0].peak_position_difference_m=1,
    d=>d.study.comparisons[0]=d.study.comparisons[1], d=>d.study.accepted=false,
    d=>d.cases[0].timing.real_time_factor=10, d=>d.checksums={}
  ]) {const {data}=fixture();mutate(data);assert.throws(()=>validateEvaluation(data));}
});
test('selected recording checks hashes, source identity and full-rate metrics',async()=>{
  const {data,documents}=fixture();validateEvaluation(data);const entry=data.cases[0];
  const original=globalThis.fetch;
  globalThis.fetch=async url=>new Response(documents[new URL(url).pathname.slice(1)]);
  try {
    const run=await loadEvaluationRecording(new URL('https://local.test/'),data,entry,new AbortController().signal);
    assert.equal(run.entry.run_id,entry.run_id);
    const path=`${entry.run_id}/manifest.json`,manifest=JSON.parse(documents[path]);manifest.source_commit='f'.repeat(40);
    documents[path]=JSON.stringify(manifest);
    await assert.rejects(loadEvaluationRecording(new URL('https://local.test/'),data,entry,new AbortController().signal),/checksum/);
    data.checksums[path]=hash(documents[path]);
    await assert.rejects(loadEvaluationRecording(new URL('https://local.test/'),data,entry,new AbortController().signal),/Invalid flight/);
  }finally{globalThis.fetch=original;}
});
