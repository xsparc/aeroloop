import test from 'node:test';
import assert from 'node:assert/strict';
import {validateIndex,validateProbe,pointDistance,csv} from '../dist/probe-contract.js';
import {fixture} from './probe-fixture.mjs';
test('signed contact captures retain incidents and interval endpoints',()=>{const b=fixture(),i=validateIndex(b.index),entry=i.cases[0],p=validateProbe(JSON.parse(b.files[entry.id]),entry,i);assert.equal(p.summary.negative_intervals,1);assert.equal(p.summary.first_negative_s,2.32);assert.equal(csv(p,2.3,2.4).trim().split('\n').length,21);assert.equal(p.passed,undefined);});
test('probe contract rejects corruption, incomplete matrices and changed source',()=>{const b=fixture(),i=validateIndex(b.index),e=i.cases[0];for(const mutate of [p=>p.rows.pop(),p=>p.rows[0].contacts[0][6]=0,p=>p.configuration.seed=99,p=>p.rows[0].anchors=Array(64).fill([0,0,0,0,0,0]),p=>p.summary.negative_intervals=0,p=>p.source.source_dirty=true]){const p=JSON.parse(b.files[e.id]);mutate(p);assert.throws(()=>validateProbe(p,e,i));}for(const mutate of [i=>i.cases.pop(),i=>i.cases[1]=i.cases[0],i=>i.cases[0].id='../private',i=>i.repeatability[0].peak_velocity_difference_m_s=1]){const i=structuredClone(b.index);mutate(i);assert.throws(()=>validateIndex(i));}});

test("reported contact distance respects collider orientation",()=>{const row={position:[1,2,3],quaternion:[Math.SQRT1_2,Math.SQRT1_2,0,0]};assert.ok(Math.abs(pointDistance(row,[1,2.15,3])-.1)<1e-12);assert.equal(pointDistance(row,[1,2,3.1]),0);});
