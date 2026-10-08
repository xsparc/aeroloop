import type {Sample,Vec3,Wxyz} from './contracts.js';
export type Row=(number|null)[];
export type Metrics=Record<string,number|null>;
export type Case={id:string;seed:number;mode:string;profile:string;physics_dt_s:number;status:string;summary:Metrics;file:string;sha256:string};
export type Flight=Omit<Case,'file'|'sha256'>&{rows:Row[];source:Record<string,unknown>;capture_sha256:string;flight_checksums_sha256:string;controller_binary_sha256:string;versions:Record<string,string>;gates:{id:string;label:string;status:string;value:number|null;limit:number;unit:string}[];failure_reason:string|null;columns:string[]};
const hash=/^[a-f0-9]{64}$/;
const idPattern=/^(fixed|scheduled|ideal)-(intact|outage)-s\d+-dt(5000|2500|1250)$/;
function check(v:unknown):asserts v{if(!v)throw Error('Invalid contact evidence');}
function obj(v:unknown):Record<string,any>{check(v&&typeof v==='object'&&!Array.isArray(v));return v as Record<string,any>;}
const finite=(v:unknown):v is number=>typeof v==='number'&&Number.isFinite(v);
const same=(a:unknown,b:unknown):boolean=>JSON.stringify(a)===JSON.stringify(b);
export function summary(rows:Row[],start:number,end:number):Metrics{
  check(start>=0&&start<end&&end<=50&&[start,end].every(v=>Math.abs(v/.005-Math.round(v/.005))<1e-7));
  check(rows[0][0]!<=start&&rows.at(-1)![0]!>=end);
  const a=rows.filter(r=>r[0]!>start&&r[0]!<=end),count=Math.round((end-start)/.005);check(a.length===count);
  const rms=(col:number)=>Math.sqrt(a.reduce((s,r)=>s+r[col]!**2,0)/count),aligned=a.filter(r=>r[31]!==null),ratios=a.filter(r=>r[30]!==null);
  const result:Metrics={start_s:start,end_s:end,intervals:count,contact_intervals:a.reduce((s,r)=>s+r[33]!,0),
    momentum_without_friction_rms_ns:rms(23),momentum_with_friction_rms_ns:rms(24),
    peak_friction_n:Math.max(...a.map(r=>Math.hypot(...r.slice(14,17) as number[]))),
    peak_friction_ratio:ratios.length?Math.max(...ratios.map(r=>r[30]!)):null,
    mean_com_alignment:aligned.length?aligned.reduce((s,r)=>s+r[31]!,0)/aligned.length:null,alignment_intervals:aligned.length,
    peak_anchors:Math.max(...a.map(r=>r[32]!))};
  ['wind_work_j','thrust_work_j','friction_work_j','kinetic_change_j','work_residual_j'].forEach((k,i)=>result[k]=a.reduce((s,r)=>s+r[25+i]!,0));return result;
}
function descriptor(v:unknown):Case{
  const c=obj(v);check(typeof c.id==='string'&&idPattern.test(c.id)&&c.file===c.id+'.json'&&hash.test(c.sha256));
  check(Number.isInteger(c.seed)&&c.seed>=0&&c.seed<2**31&&['fixed','scheduled','ideal'].includes(c.mode)&&['sample-hold','hold-dropout-2000ms','ideal'].includes(c.profile)&&[.005,.0025,.00125].includes(c.physics_dt_s)&&['passed','failed'].includes(c.status));
  check(c.id===`${c.mode}-${c.profile==='hold-dropout-2000ms'?'outage':'intact'}-s${c.seed}-dt${Math.round(c.physics_dt_s*1e6)}`);
  const s=obj(c.summary);check(Object.values(s).every(v=>v===null||finite(v)));return c as Case;
}
export function validateIndex(v:unknown):Case[]{const x=obj(v);check(x.schema_version===1&&x.kind==='friction_index'&&Array.isArray(x.cases)&&x.cases.length>0&&x.cases.length<=24);const entries=x.cases.map(descriptor);check(new Set(entries.map(c=>c.id)).size===entries.length);return entries;}
export function validateFlight(v:unknown,c:Case):Flight{
  const x=obj(v);check(x.schema_version===1&&x.kind==='friction_case');
  for(const k of ['id','seed','mode','profile','physics_dt_s','status'] as const)check(x[k]===c[k]);
  check(Array.isArray(x.columns)&&x.columns.length===35&&x.columns.every((k:unknown)=>typeof k==='string'));
  check(Array.isArray(x.rows)&&x.rows.length===10001);
  x.rows.forEach((r:unknown,i:number)=>{check(Array.isArray(r)&&r.length===35);check(r.every((v,k)=>finite(v)||v===null&&(k===30||k===31)));check(Math.abs(r[0]-i*.005)<1e-8);check(Math.abs(Math.hypot(...r.slice(4,8))-1)<1e-5);check(Number.isInteger(r[32])&&r[32]>=0&&r[32]<64&&[0,1].includes(r[33])&&[0,1].includes(r[34]));check(r[31]===null||Math.abs(r[31])<=1);});
  const s=obj(x.source);check(s.source_dirty===false&&/^[a-f0-9]{40}$/.test(s.source_commit)&&hash.test(s.source_tree_sha256)&&hash.test(s.lock_sha256));
  for(const k of ['capture_sha256','flight_checksums_sha256','controller_binary_sha256'])check(hash.test(x[k]));
  check(Object.values(obj(x.versions)).every(v=>typeof v==='string'));
  check(Array.isArray(x.gates)&&x.gates.length>0&&x.gates.every((v:unknown)=>{const g=obj(v);return typeof g.id==='string'&&typeof g.label==='string'&&['passed','failed','missing'].includes(g.status)&&(g.value===null||finite(g.value))&&finite(g.limit)&&typeof g.unit==='string';}));
  check((x.status==='passed')===x.gates.every((g:any)=>g.status==='passed'));
  check(x.failure_reason===null||typeof x.failure_reason==='string');
  const metrics=summary(x.rows,0,50);for(const k of Object.keys(metrics)){const a=metrics[k];check(a===null?x.summary[k]===null:finite(x.summary[k])&&Math.abs(a-x.summary[k])<1e-8*Math.max(1,Math.abs(a)));}check(same(x.summary,c.summary));return x as Flight;
}
export function pose(r:Row):Sample{return {time_s:r[0]!,position_m:r.slice(1,4) as Vec3,quaternion_wxyz:r.slice(4,8) as Wxyz,target_m:[0,0,.05],mission_phase:r[34]?'landed':'landing',contact_normal_force_n:r.slice(11,14) as Vec3,contact_friction_force_n:r.slice(14,17) as Vec3};}
export function csv(f:Flight,start:number,end:number):string{summary(f.rows,start,end);return f.columns.join(',')+'\n'+f.rows.filter(r=>r[0]!>start&&r[0]!<=end).map(r=>r.map(v=>v??'').join(',')).join('\n')+'\n';}
