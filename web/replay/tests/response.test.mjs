import test from 'node:test';
import assert from 'node:assert/strict';
import {fixture} from './approach-fixture.mjs';
import {validateApproachIndex,validateApproach} from '../dist/approach-contract.js';
import {quartet,preset,radial,interval,summarize,contrasts,analyze,energyCurve,accelerationCurve,parseSelection,selectionHash,review,windowCsv} from '../dist/response-analysis.js';
const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-9,`${a} != ${b}`);
const f=fixture(),entries=validateApproachIndex(f.index);
const pair=[0,1].map(p=>entries.find(e=>e.id===`stress-p${p}-s401`));
const values=pair.map(e=>validateApproach(JSON.parse(f.documents[e.file]),e));
const q=quartet(values[0],values[1],pair),digest='a'.repeat(64);
function row(t,x=0,v=0){const r=Array(42).fill(0);r[0]=t;r[1]=x;r[3]=v;r[31]=Math.abs(x);return r;}
test('four-way provenance rejects wrong profile, seed, mode source and runtime',()=>{
  for(const mutate of [v=>v.profile='sample-hold',v=>v.seed=503,v=>v.baseline.provenance.source_commit='c'.repeat(40),v=>v.candidate.provenance.lock_sha256='d'.repeat(64)]){
    const changed=structuredClone(values[1]);mutate(changed);assert.throws(()=>quartet(values[0],changed,pair));
  }
  assert.throws(()=>quartet(values[0],values[1],pair.toReversed()));assert.equal(q.flights.length,4);
});
test('constant force work equals kinetic change and uses preceding force',()=>{
  const a=row(34),b=row(34.005,.000025,.01);a[23]=1;a[25]=1;b[23]=999;b[25]=999;a[20]=2;
  const n=interval(a,b);close(n.wind,.000025);close(n.thrust,.000025);close(n.kinetic,.00005);close(n.residual,0);close(n.ax,2);close(n.demand_error,0);close(n.force_residual,0);
  b[27]=1;assert.equal(interval(a,b).phase,'contact');a[30]=1;assert.equal(interval(a,b).phase,'disarmed');
  b[0]=34.02;assert.throws(()=>interval(a,b));
});
test('interval endpoints exclude terminal demand and preserve phase exposure',()=>{
  const rows=[row(34,1,0),row(34.005,1,0),row(34.01,1,0)];rows[0][20]=2;rows[1][20]=4;rows[2][20]=999;rows[1][27]=1;rows[1][30]=1;
  const s=summarize({rows},{start:34,end:34.01});close(s.rmse_m,1);close(s.demand_rms_m_s2,Math.sqrt(10));assert.equal(s.intervals,2);close(s.contact_s,.005);close(s.disarmed_s,.005);close(s.airborne_s,0);
  const bad=summarize({rows:rows.slice(0,2)},{start:34,end:34.01});assert.equal(bad.complete,false);assert.equal(bad.rmse_m,null);assert.equal(bad.duration_s,null);
  assert.equal(accelerationCurve({rows},{start:34,end:34.01}).length,2);assert.equal(energyCurve({rows},{start:34,end:34.01}).length,3);
});
test('phase presets require every event and exclude the contact/disarm endpoint',()=>{
  assert.deepEqual(preset(q,'airborne'),{start:34,end:41.195});assert.deepEqual(preset(q,'armed'),{start:34,end:41.245});assert.deepEqual(preset(q,'disarmed'),{start:41.25,end:50});
  const changed=structuredClone(q);changed.flights[3].landed_s=null;assert.equal(preset(changed,'disarmed'),null);assert.equal(preset(changed,'armed'),null);
  changed.flights[2].touchdown_s=null;assert.equal(preset(changed,'airborne'),null);changed.flights[0].rows=[];assert.equal(preset(changed,'full'),null);
  const missing=analyze(changed,{start:40,end:43});assert.equal(missing.rmse.interaction,null);
});
test('rotated radial frame preserves signed closing and error norm, target is undefined',()=>{
  const r=row(34,0,0);r[2]=2;r[4]=-3;r[5]=4;r[6]=3;const p=radial(r);close(p.distance,2);close(p.closing,3);close(p.radial_error,1);close(p.tangential_error,-4);close(p.radial_error**2+p.tangential_error**2,17);
  r[9]=r[1];r[10]=r[2];assert.equal(radial(r).closing,null);assert.equal(radial(r).radial_error,null);
});
test('difference of effects signs are explicit and incomplete cells remain unavailable',()=>{
  assert.deepEqual(contrasts([1,3,2,3]),{fixed:2,scheduled:1,interaction:-1});assert.deepEqual(contrasts([1,null,2,3]),{fixed:null,scheduled:null,interaction:null});assert.throws(()=>contrasts([1,2,3,NaN]));
});
test('links bind seed, grid, window and digest; exports preserve original gates and terminal blanks',()=>{
  const s={id:q.id,start:40,end:40.01,time:40.005},hash=selectionHash(s,digest);assert.deepEqual(parseSelection(hash,digest),s);assert.equal(parseSelection(hash,'b'.repeat(64)),null);
  for(const bad of [hash+'&t=40',hash.replace('end=40.010','end=39.000'),hash.replace('t=40.005','t=40.002')])assert.equal(parseSelection(bad,digest),null);
  const data=review(q,s,digest);assert.equal(data.flights.length,4);assert.equal(data.flights[0].rows.length,3);assert.deepEqual(data.flights[1].outage,q.flights[1].outage);assert.deepEqual(data.flights[0].gates,q.flights[0].gates);
  assert.deepEqual(data.analysis.window,{start:40,end:40.01});
  const csv=windowCsv(q,s,digest).trimEnd().split('\n').map(l=>l.split(','));assert.equal(csv.length,13);assert.ok(csv.every(r=>r.length===csv[0].length));assert.ok(csv[3].slice(-9).every(v=>v===''));assert.ok(csv[2].slice(-9).every(v=>v!==''));
});
