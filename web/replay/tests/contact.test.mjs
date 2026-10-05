import test from 'node:test';
import assert from 'node:assert/strict';
import {fixture} from './contact-fixture.mjs';
import {validateContactIndex,validateContact,derived,episodes,phaseMetrics,phases,readiness,DEFAULT_BOUNDS,selectionHash,parseSelection,contactExport} from '../dist/contact-contract.js';

test('landing contracts bind gates, quaternion, rotor forces, timing and full-rate arithmetic',()=>{
  const data=fixture(),entry=validateContactIndex(data.index)[6],raw=JSON.parse(data.documents[entry.file]);validateContact(raw,entry);
  for(const mutate of [d=>d.candidate[0][48]=1,d=>d.candidate[1][27]=1,d=>d.candidate[1][29]=1,d=>d.candidate[0][17]=.9,d=>d.candidate[0][21]=6,d=>d.candidate[0][33]=7,d=>d.candidate.pop(),d=>d.candidate[0].push(0),d=>d.descent.candidate.gates[0].limit=1,d=>d.descent.candidate.poses.at(-1).position_m[0]=.7,d=>d.path='private']){
    const bad=structuredClone(raw);mutate(bad);assert.throws(()=>validateContact(bad,entry));
  }
  const bad=structuredClone(data.index);bad.cases[0].file='../secret';assert.throws(()=>validateContactIndex(bad));
  assert.throws(()=>validateContact(raw,{...entry,candidate_support_error_m:.2}));
});

test('analytic impulse distinguishes preceding force from current force and closes phase budget',()=>{
  const a=Array(33).fill(0);a[0]=34;a[3]=.21;a[17]=1;a[25]=100;a[27]=.2;a[31]=2;
  const r=[...a,...derived(a,true)];assert.ok(Math.abs(r[48])<1e-12);assert.equal(r[33],0);
  const b=[...a];b[0]=34.005;b[3]=.71;b[27]=.21;b[31]=100;const s=[...b,...derived(b,true)];
  const p=phaseMetrics([r,s],34,34.005,true);assert.equal(p.state_samples,2);assert.ok(Math.abs(p.wind_impulse_n_s[0]-.5)<1e-12);
  assert.ok(Math.abs(p.momentum_change_n_s[0]-p.wind_impulse_n_s[0]-p.residual_impulse_n_s[0])<1e-12);
  assert.equal(phaseMetrics([],34,50,true),null);assert.equal(phaseMetrics([r,s],34,50,true).complete,false);
});

test('contact episodes retain interruptions, singleton duration and terminal censoring',()=>{
  const make=(t,force,eligible,dwell,landed=0)=>{const r=Array(24).fill(0);r[0]=t;r[15]=force;r[17]=eligible;r[18]=dwell;r[19]=landed;return r;};
  const side={rows:[make(34,.2,1,0),make(34.005,.2,1,.005),make(34.01,0,0,0),make(34.015,.2,0,0)]};
  const e=episodes(side);assert.equal(e.length,2);assert.equal(e[0].samples,2);assert.equal(e[0].right_censored,false);assert.equal(e[1].duration_s,0);assert.equal(e[1].eligible_samples,0);assert.equal(e[1].right_censored,true);
});

test('readiness never includes post-disarm motion and settings cannot overwrite original gates',()=>{
  const data=fixture(),entry=data.index.cases[6],pair=validateContact(JSON.parse(data.documents[entry.file]),entry),side=pair.descent.baseline;
  const before=JSON.stringify(side.gates),audit=readiness(pair.baseline,side,DEFAULT_BOUNDS);
  assert.equal(audit.first_qualifying_s,null);assert.equal(audit.evaluated_through_s,41.25);assert.deepEqual(audit.blockers_at_disarm,['position','dwell']);
  const relaxed={...DEFAULT_BOUNDS,position:.5};assert.equal(readiness(pair.baseline,side,relaxed).first_qualifying_s,41.25);
  assert.equal(readiness(pair.baseline,side,{...relaxed,dwell:.1}).first_qualifying_s,null);
  assert.throws(()=>readiness(pair.baseline,side,{...relaxed,dwell:NaN}));
  assert.equal(JSON.stringify(side.gates),before);
  const incomplete=phases([], {touchdown_s:null,landed_s:null});assert.deepEqual(incomplete,{approach:null,contact_to_disarm:null,disarmed:null});
  // An interruption resets the exploratory dwell even when contact eligibility stays true.
  const rows=structuredClone(pair.baseline);rows[Math.round((41.225-34)/.005)][44]=.3;
  assert.equal(readiness(rows,side,relaxed).first_qualifying_s,null);
});

test('review links and exports bind settings, source version and unchanged failed outcomes',()=>{
  const data=fixture(),entry=data.index.cases[6],pair=validateContact(JSON.parse(data.documents[entry.file]),entry),digest='a'.repeat(64),s={id:entry.id,time:41.68,bounds:DEFAULT_BOUNDS};
  const hash=selectionHash(s,digest);assert.deepEqual(parseSelection(hash,digest),s);assert.equal(parseSelection(hash,'b'.repeat(64)),null);
  for(const suffix of ['&url=private','&t=34','&speed=NaN'])assert.equal(parseSelection(hash+suffix,digest),null);
  assert.equal(parseSelection(hash.replace('dwell=0.05','dwell='),digest),null);
  const report=contactExport(pair,DEFAULT_BOUNDS,digest,41.68);assert.equal(report.baseline.rows.length,3201);assert.equal(report.baseline.status,'failed');assert.equal(report.baseline.gates.find(g=>g.id==='final_support_peak_xy_error_m').limit,.35);assert.equal(report.baseline.readiness.first_qualifying_s,null);assert.ok(!JSON.stringify(report).includes('baseUrl'));
});

test('short failed evidence retains absent landing rows and incomplete diagnostics',()=>{
  const data=fixture({incomplete:true}),entry=data.index.cases[3],pair=validateContact(JSON.parse(data.documents[entry.file]),entry);
  assert.equal(pair.baseline.length,0);assert.equal(readiness(pair.baseline,pair.descent.baseline,DEFAULT_BOUNDS).samples,0);assert.equal(pair.descent.baseline.status,'failed');
});
