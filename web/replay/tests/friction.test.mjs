import test from 'node:test';
import assert from 'node:assert/strict';
import {validateIndex,validateFlight,summary,csv} from '../dist/friction-contract.js';
import {fixture} from './friction-fixture.mjs';
test('verified contact contract retains failed gates and exact interval exports',()=>{const b=fixture();assert.equal(validateIndex(JSON.parse(b.index)).length,1);const f=validateFlight(b.f,b.entry);assert.equal(f.status,'failed');assert.equal(summary(f.rows,40,43).intervals,600);assert.equal(csv(f,40,43).trim().split('\n').length,601);assert.equal(summary(f.rows,40,43).mean_com_alignment,null);assert.throws(()=>summary(f.rows,40,40.001));});
test('contact contracts reject gaps, bad orientation, saturation, inconsistent metrics and paths',()=>{for(const mutate of [f=>f.rows.pop(),f=>f.rows[100][0]+=.001,f=>f.rows[2][4]=0,f=>f.rows[3][32]=64,f=>f.summary.peak_friction_n=99,f=>f.source.source_dirty=true,f=>f.columns[0]='=formula',f=>f.ground_kind='static']){const b=fixture();mutate(b.f);assert.throws(()=>validateFlight(b.f,b.entry));}const b=fixture();const i=JSON.parse(b.index);i.cases[0].file='../private.json';assert.throws(()=>validateIndex(i));});
