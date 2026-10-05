import {HASH,MISSION_PHASES,type Sample} from './contracts.js';
import {expectedGates,gateStatus,type Gate} from './evaluation-contract.js';
import {headroom} from './diagnosis-contract.js';
export const COHORTS=['regression','additional'],PROFILES=['sample-hold','hold-dropout-2000ms'];
export const COLUMNS=['time_s','truth_z_m','feedback_z_m','truth_vz_m_s','feedback_vz_m_s','target_z_m','target_vz_m_s','position_term_m_s2','velocity_term_m_s2','feedforward_m_s2','clipped_vertical_m_s2','requested_thrust_n','realized_thrust_n','world_vertical_thrust_n','wind_vertical_force_n','contact_normal_n','clearance_m','contact_eligible','contact_dwell_s','landed','decay_scale','anchor_z_m_s2','effective_z_m_s2','capture_age_s'];
export type DescentCase={id:string;file:string;sha256:string;cohort:string;profile:string;seed:number;baseline_status:string;candidate_status:string};
export type WindowMetrics={start_s:number;end_s:number;samples:number;complete:boolean;vertical_velocity_error_rmse_m_s:number|null;peak_vertical_velocity_error_m_s:number|null;requested_thrust_impulse_n_s:number;realized_thrust_impulse_n_s:number};
type Outage={passed:boolean;recovery_passed:boolean;peak_distance_m:number|null;rmse_change_m:number|null;landed_change_s:number|null;recovery:{time_s:number|null;passed:boolean;complete:boolean}[]};
export type DescentSide={status:string;failure_reason:string|null;gates:(Gate&{headroom:number|null})[];rows:number[][];poses:Sample[];touchdown_s:number|null;landed_s:number|null;window:WindowMetrics;outage:Outage|null;provenance:Record<string,any>};
export type Descent={id:string;cohort:string;profile:string;seed:number;baseline:DescentSide;candidate:DescentSide};
function check(v:unknown):asserts v {if(!v)throw Error('Invalid descent comparison');}
function obj(v:unknown):Record<string,any>{check(v&&typeof v==='object'&&!Array.isArray(v));return v as Record<string,any>;}
function keys(v:Record<string,any>,names:string[]){check(Object.keys(v).sort().join()===names.slice().sort().join());}
const finite=(v:unknown):v is number=>typeof v==='number'&&Number.isFinite(v);
const close=(a:any,b:any)=>a===null||b===null?a===b:finite(a)&&finite(b)&&Math.abs(a-b)<1e-9;
export function validateDescentIndex(value:unknown):DescentCase[]{
  const d=obj(value);keys(d,['schema_version','kind','cases']);check(d.schema_version===1&&d.kind==='descent_comparison_index'&&Array.isArray(d.cases)&&d.cases.length===12);
  d.cases.forEach((raw:unknown,i:number)=>{const c=obj(raw),cohort=COHORTS[Math.floor(i/6)],p=Math.floor(i%6/3),seed=(i<6?[0,1,2]:[401,503,607])[i%3];
    keys(c,['id','file','sha256','cohort','profile','seed','baseline_status','candidate_status']);
    check(c.id===`${cohort}-p${p}-s${seed}`&&c.file===c.id+'.json'&&HASH.test(c.sha256)&&c.cohort===cohort&&c.profile===PROFILES[p]&&c.seed===seed&&['passed','failed'].includes(c.baseline_status)&&['passed','failed'].includes(c.candidate_status));
  });return d.cases;
}
export function windowMetrics(rows:number[][],start=40,end=42):WindowMetrics{
  const selected=rows.filter(r=>r[0]>=start-1e-9&&r[0]<end-1e-9),errors=selected.map(r=>Math.abs(r[4]-r[3]));
  return {start_s:start,end_s:end,samples:selected.length,complete:selected.length===Math.round((end-start)/.005),
    vertical_velocity_error_rmse_m_s:errors.length?Math.sqrt(errors.reduce((a,b)=>a+b*b,0)/errors.length):null,
    peak_vertical_velocity_error_m_s:errors.length?Math.max(...errors):null,
    requested_thrust_impulse_n_s:selected.reduce((a,r)=>a+r[11]*.005,0),realized_thrust_impulse_n_s:selected.reduce((a,r)=>a+r[12]*.005,0)};
}
export function validateDescent(value:unknown,entry:DescentCase):Descent{
  const d=obj(value);keys(d,['schema_version','kind','id','cohort','profile','seed','columns','baseline','candidate']);
  check(d.schema_version===1&&d.kind==='descent_comparison'&&JSON.stringify(d.columns)===JSON.stringify(COLUMNS));
  for(const k of ['id','cohort','profile','seed'] as const)check(d[k]===entry[k]);
  for(const mode of ['baseline','candidate'] as const){const s=obj(d[mode]);
    keys(s,['status','failure_reason','gates','rows','poses','touchdown_s','landed_s','window','outage','provenance']);
    check(s.status===entry[mode+'_status' as 'baseline_status']&&[null,'model_bounds_exceeded','wind_mission_threshold','wind_mission_support_threshold'].includes(s.failure_reason)&&(s.status==='passed')===(s.failure_reason===null));
    check(Array.isArray(s.rows)&&s.rows.length>=2&&s.rows.length<=10001);let since:number|null=null,landed=false;
    const rows=s.rows as number[][];
    rows.forEach((r,i)=>{
      check(Array.isArray(r)&&r.length===24&&r.every(finite)&&close(r[0],i*.005));
      const age=d.profile===PROFILES[1]&&((r[0]>=18&&r[0]<20)||(r[0]>=40&&r[0]<42))?r[0]-(r[0]<20?17.98:39.98):(i%4)*.005;
      check(close(r[23],age));
      check(close(r[20],mode==='baseline'?1:Math.exp(-Math.max(0,age-.015)/.2))&&Math.abs(r[21])<=4&&close(r[22],r[20]*r[21]));
      const eligible=r[0]>=34&&r[15]>.1&&r[16]<=.015&&Math.abs(r[3])<=.2;
      since=eligible?(since??r[0]):null;check(r[17]===Number(eligible)&&close(r[18],since===null?0:r[0]-since));
      if(r[18]>=.05-1e-9)landed=true;check(r[19]===Number(landed));
      const armed=r[0]>=2&&!landed;
      check(close(r[7],armed?2.5*(r[5]-r[2]):0)&&close(r[8],armed?2.8*(r[6]-r[4]):0)&&close(r[10],Math.max(-4,Math.min(4,r[9]+r[7]+r[8]))));
      check(r[11]>=0&&r[11]<=20&&r[12]>=0&&r[12]<=20&&Math.abs(r[13])<=r[12]+1e-9&&(!landed||r[11]===0));
      if(!armed)check(r[6]===0&&r[9]===0);
    });
    check(close(s.touchdown_s,rows.find(r=>r[0]>=34&&r[15]>.1)?.[0]??null)&&close(s.landed_s,rows.find(r=>r[19])?.[0]??null));
    const expected=windowMetrics(rows);keys(obj(s.window),Object.keys(expected));for(const [k,v] of Object.entries(expected))check(typeof v==='boolean'?s.window[k]===v:close(s.window[k],v));
    check(Array.isArray(s.poses)&&s.poses.length>=2&&s.poses.length<=1200);let last=-1;
    for(const raw of s.poses){const p=obj(raw);keys(p,['time_s','position_m','target_m','quaternion_wxyz','mission_phase']);
      const i=Math.round(p.time_s/.005);check(finite(p.time_s)&&p.time_s>last&&i<rows.length&&close(p.time_s,i*.005));last=p.time_s;
      for(const [k,n] of [['position_m',3],['target_m',3],['quaternion_wxyz',4]] as const)check(Array.isArray(p[k])&&p[k].length===n&&p[k].every(finite));
      check(MISSION_PHASES.includes(p.mission_phase)&&Math.abs(Math.hypot(...p.quaternion_wxyz)-1)<1e-6&&close(p.position_m[2],rows[i][1])&&close(p.target_m[2],rows[i][5])&&(p.mission_phase==='landed')===!!rows[i][19]);
    }check(s.poses[0].time_s===0&&last===rows.at(-1)![0]);
    // Fixed gate definitions; source metrics were independently reconstructed before export.
    const definitions=expectedGates({metrics:{mission:{waypoint_reached_s:[null,null,null,null],initial_support:null,final_support:null}}});
    check(Array.isArray(s.gates)&&s.gates.length===24);const seen=new Set();
    for(const raw of s.gates){const g=obj(raw) as Gate&{headroom:number|null};keys(g,['id','label','group','value','unit','operator','limit','status','headroom']);
      check(g.id in definitions&&!seen.has(g.id)&&typeof g.label==='string'&&g.label.length<=100&&g.group===(g.id.includes('_support_')?'support':'mission')&&(g.value===null||finite(g.value)));
      check(JSON.stringify([g.unit,g.operator,g.limit])===JSON.stringify(definitions[g.id].slice(1))&&g.status===gateStatus(g)&&close(g.headroom,headroom(g)));seen.add(g.id);
    }
    const gate=(id:string)=>s.gates.find((g:Gate)=>g.id===id).value;
    check(gate('samples')===rows.length&&close(gate('touchdown'),s.touchdown_s)&&close(gate('landed'),s.landed_s)&&gate('model_bounds')===Number(s.failure_reason==='model_bounds_exceeded'));
    check((s.status==='passed')===s.gates.every((g:Gate)=>g.status==='passed'));
    if(d.profile===PROFILES[0])check(s.outage===null);
    else{const o=obj(s.outage);keys(o,['passed','recovery_passed','peak_distance_m','rmse_change_m','landed_change_s','recovery']);
      for(const k of ['passed','recovery_passed'])check(typeof o[k]==='boolean');
      for(const k of ['peak_distance_m','rmse_change_m','landed_change_s'])check(o[k]===null||finite(o[k]));
      check(o.passed===(o.peak_distance_m!==null&&o.peak_distance_m<=.15&&o.rmse_change_m!==null&&Math.abs(o.rmse_change_m)<=.05&&o.landed_change_s!==null&&Math.abs(o.landed_change_s)<=.5));
      check(Array.isArray(o.recovery)&&o.recovery.length===2);for(const r of o.recovery){keys(obj(r),['time_s','passed','complete']);check(typeof r.complete==='boolean'&&(r.time_s===null||finite(r.time_s)&&r.time_s>=0)&&r.passed===(r.complete&&r.time_s!==null&&r.time_s<=5));}
      check(o.recovery_passed===o.recovery.every((r:any)=>r.passed));
    }
    const p=obj(s.provenance);keys(p,['source_commit','source_tree_sha256','controller_binary_sha256','lock_sha256','config_sha256','samples_sha256','versions','source_dirty']);
    check(/^[a-f0-9]{40}$/.test(p.source_commit)&&p.source_dirty===false);for(const k of ['source_tree_sha256','controller_binary_sha256','lock_sha256','config_sha256','samples_sha256'])check(typeof p[k]==='string'&&HASH.test(p[k]));
    keys(obj(p.versions),['isaacsim','isaaclab','torch']);check(Object.values(p.versions).every(v=>typeof v==='string'&&/^[0-9][a-zA-Z0-9.+-]{0,31}$/.test(v)));
  }
  for(const k of ['controller_binary_sha256','lock_sha256','versions'])check(JSON.stringify(d.baseline.provenance[k])===JSON.stringify(d.candidate.provenance[k]));
  if(d.cohort==='additional')for(const k of ['source_commit','source_tree_sha256'])check(d.baseline.provenance[k]===d.candidate.provenance[k]);
  const cutoff=d.profile===PROFILES[0]?d.baseline.rows.length:Math.min(3600,d.baseline.rows.length);
  check(JSON.stringify(d.baseline.rows.slice(0,cutoff))===JSON.stringify(d.candidate.rows.slice(0,cutoff)));
  return d as Descent;
}
export type Selection={id:string;alignment:'time'|'touchdown';time:number};
export function parseSelection(hash:string,digest:string):Selection|null{
  if(hash.length>220)return null;const p=new URLSearchParams(hash.slice(1));
  if([...p.keys()].sort().join()!=='case,index,mode,t'||p.get('index')!==digest)return null;
  const id=p.get('case')!,alignment=p.get('mode'),time=Number(p.get('t'));
  if(!/^(regression-p[01]-s[012]|additional-p[01]-s(401|503|607))$/.test(id)||!['time','touchdown'].includes(alignment!)||!finite(time)||time< (alignment==='time'?0:-50)||time>50)return null;
  return {id,alignment:alignment as Selection['alignment'],time};
}
export function selectionHash(s:Selection,digest:string){return '#'+new URLSearchParams({case:s.id,index:digest,mode:s.alignment,t:s.time.toFixed(3)});}
export function comparisonExport(d:Descent,start:number,end:number,alignment:Selection['alignment'],digest:string){
  check(finite(start)&&finite(end)&&start<end&&start>=-50&&end<=50&&HASH.test(digest));
  return {schema_version:1,kind:'descent_window_comparison',id:d.id,cohort:d.cohort,profile:d.profile,seed:d.seed,index_sha256:digest,alignment,
    ...Object.fromEntries((['baseline','candidate'] as const).map(mode=>{const s=d[mode],offset=alignment==='time'?0:s.touchdown_s;check(offset!==null);
      return [mode,{status:s.status,failure_reason:s.failure_reason,gates:s.gates,outage:s.outage,touchdown_s:s.touchdown_s,landed_s:s.landed_s,provenance:s.provenance,window:windowMetrics(s.rows,start+offset,end+offset)}];})),
    interpretation:'Window measurements are descriptive; original mission, same-mode pair and recovery gates remain authoritative.'};
}
