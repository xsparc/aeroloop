import {HASH} from './contracts.js';
import {validateDescentIndex,validateDescent,type DescentCase,type Descent,type DescentSide,COLUMNS as DESCENT_COLUMNS} from './descent-contract.js';

export const COLUMNS=['time_s','x_m','y_m','vx_m_s','vy_m_s','feedback_x_m','feedback_y_m','feedback_vx_m_s','feedback_vy_m_s','target_x_m','target_y_m','target_vx_m_s','target_vy_m_s','integral_x_m_s2','integral_y_m_s2','feedforward_x_m_s2','feedforward_y_m_s2','qw','qx','qy','qz','rotor_0_n','rotor_1_n','rotor_2_n','rotor_3_n','wind_x_n','wind_y_n','previous_vx_m_s','previous_vy_m_s','previous_thrust_x_n','previous_thrust_y_n','previous_wind_x_n','previous_wind_y_n','p_x_m_s2','p_y_m_s2','d_x_m_s2','d_y_m_s2','clipped_x_m_s2','clipped_y_m_s2','thrust_x_n','thrust_y_n','tilt_deg','yaw_deg','home_distance_m','horizontal_speed_m_s','feedback_position_error_m','feedback_velocity_error_m_s','horizontal_energy_j','residual_impulse_x_n_s','residual_impulse_y_n_s'];
export const MODES=['baseline','candidate'] as const;
export type Mode=typeof MODES[number];
export type ContactCase=DescentCase&{baseline_support_error_m:number|null;candidate_support_error_m:number|null};
export type Contact={descent:Descent;baseline:number[][];candidate:number[][]};
export type Bounds={position:number;speed:number;tilt:number;dwell:number};
export const DEFAULT_BOUNDS:Bounds={position:.35,speed:.2,tilt:3,dwell:.05};
export type Selection={id:string;time:number;bounds:Bounds};
function check(v:unknown):asserts v{if(!v)throw Error('Invalid landing contact evidence');}
function obj(v:unknown):Record<string,any>{check(v&&typeof v==='object'&&!Array.isArray(v));return v as Record<string,any>;}
function keys(v:Record<string,any>,expected:string[]){check(Object.keys(v).sort().join()===expected.slice().sort().join());}
const finite=(v:unknown):v is number=>typeof v==='number'&&Number.isFinite(v);
const close=(a:number,b:number)=>Math.abs(a-b)<1e-9;
const clip=(n:number)=>Math.max(-4,Math.min(4,n));

export function validateContactIndex(value:unknown):ContactCase[]{
  const d=obj(value);keys(d,['schema_version','kind','cases']);check(d.schema_version===1&&d.kind==='landing_contact_index'&&Array.isArray(d.cases));
  const base=d.cases.map((raw:unknown)=>{const c=obj(raw);keys(c,['id','file','sha256','cohort','profile','seed','baseline_status','candidate_status','baseline_support_error_m','candidate_support_error_m']);
    for(const mode of MODES)check(c[mode+'_support_error_m']===null||finite(c[mode+'_support_error_m'])&&c[mode+'_support_error_m']>=0);
    const {baseline_support_error_m:_,candidate_support_error_m:__,...rest}=c;return rest;});
  validateDescentIndex({...d,kind:'descent_comparison_index',cases:base});return d.cases;
}

/** Deterministic formulas; raw values occupy columns 0..32. */
export function derived(r:number[],armed:boolean):number[]{
  const [w,x,y,z]=r.slice(17,21),total=r.slice(21,25).reduce((a,b)=>a+b,0);
  const p=[0,1].map(a=>armed?2.5*(r[9+a]-r[5+a]):0),d=[0,1].map(a=>armed?2.8*(r[11+a]-r[7+a]):0);
  return [...p,...d,...[0,1].map(a=>clip(p[a]+d[a]+r[13+a]+r[15+a])),
    2*(x*z+w*y)*total,2*(y*z-w*x)*total,Math.acos(Math.max(-1,Math.min(1,1-2*(x*x+y*y))))*180/Math.PI,
    Math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))*180/Math.PI,Math.hypot(r[1],r[2]),Math.hypot(r[3],r[4]),
    Math.hypot(r[5]-r[1],r[6]-r[2]),Math.hypot(r[7]-r[3],r[8]-r[4]),.5*(r[3]**2+r[4]**2),
    r[3]-r[27]-.005*(r[29]+r[31]),r[4]-r[28]-.005*(r[30]+r[32])];
}

export function validateContact(value:unknown,entry:ContactCase):Contact{
  const d=obj(value);keys(d,['schema_version','kind','columns','descent','baseline','candidate']);
  check(d.schema_version===1&&d.kind==='landing_contact'&&JSON.stringify(d.columns)===JSON.stringify(COLUMNS));
  const descent=validateDescent(d.descent,entry);
  for(const mode of MODES){const rows=d[mode] as number[][],side=descent[mode];
    check(Array.isArray(rows)&&rows.length===Math.max(0,side.rows.length-6800));
    rows.forEach((r,i)=>{
      check(Array.isArray(r)&&r.length===50&&r.every(finite)&&close(r[0],34+i*.005));
      const old=side.rows[i+6800],armed=!old[19];
      check(Math.abs(Math.hypot(...r.slice(17,21))-1)<1e-6&&r.slice(21,25).every(v=>v>=0&&v<=5));
      check(close(r.slice(21,25).reduce((a,b)=>a+b,0),old[12]));
      check(close((1-2*(r[18]**2+r[19]**2))*old[12],old[13]));
      check(r.slice(13,15).every(v=>Math.abs(v)<=1.5)&& (armed||r.slice(11,17).every(v=>v===0)));
      derived(r,armed).forEach((v,j)=>check(close(v,r[33+j])));
      if(i){const prev=rows[i-1];for(const [a,b] of [[27,3],[28,4],[29,39],[30,40],[31,25],[32,26]])check(close(r[a],prev[b]));}
    });
    for(const p of side.poses){if(p.time_s<34)continue;const r=rows[Math.round((p.time_s-34)/.005)];
      for(let a=0;a<2;a++)check(close(p.position_m[a],r[1+a])&&close(p.target_m[a],r[9+a]));
      for(let a=0;a<4;a++)check(close(p.quaternion_wxyz[a],r[17+a]));}
    const g=side.gates.find(g=>g.id==='final_support_peak_xy_error_m')!;
    check(g.value===entry[mode+'_support_error_m' as 'baseline_support_error_m']);
    const support=rows.filter(r=>r[0]>=48);
    if(support.length)check(g.value!==null&&close(g.value,Math.max(...support.map(r=>r[43]))));else check(g.value===null);
  }
  if(descent.profile==='sample-hold')check(JSON.stringify(d.baseline)===JSON.stringify(d.candidate));
  return d as Contact;
}

export type Episode={start_s:number;end_s:number;duration_s:number;samples:number;right_censored:boolean;eligible_samples:number;max_dwell_s:number;disarmed_samples:number};
export function episodes(side:DescentSide):Episode[]{
  const result:Episode[]=[];let active:Episode|null=null;
  for(const r of side.rows){if(r[0]<34)continue;
    if(r[15]>.1){if(!active){active={start_s:r[0],end_s:r[0],duration_s:0,samples:0,right_censored:false,eligible_samples:0,max_dwell_s:0,disarmed_samples:0};result.push(active);}
      active.end_s=r[0];active.duration_s=r[0]-active.start_s;active.samples++;active.eligible_samples+=r[17];active.max_dwell_s=Math.max(active.max_dwell_s,r[18]);active.disarmed_samples+=r[19];
    }else active=null;
  }
  if(active)active.right_censored=true;return result;
}

export function phaseMetrics(rows:number[][],start:number|null,end:number|null,complete:boolean){
  if(start===null||end===null||end<start)return null;
  const chosen=rows.filter(r=>r[0]>=start-1e-9&&r[0]<=end+1e-9);if(!chosen.length)return null;
  const a=chosen[0],b=chosen.at(-1)!,intervals=chosen.slice(1),sum=(c:number,dt=1)=>intervals.reduce((n,r)=>n+r[c]*dt,0);
  return {start_s:start,end_s:end,state_samples:chosen.length,complete:complete&&close(a[0],start)&&close(b[0],end),
    displacement_xy_m:[b[1]-a[1],b[2]-a[2]],distance_change_m:b[43]-a[43],peak_speed_m_s:Math.max(...chosen.map(r=>r[44])),
    energy_change_j:b[47]-a[47],momentum_change_n_s:[b[3]-a[3],b[4]-a[4]],thrust_impulse_n_s:[sum(29,.005),sum(30,.005)],
    wind_impulse_n_s:[sum(31,.005),sum(32,.005)],residual_impulse_n_s:[sum(48),sum(49)]};
}
export function phases(rows:number[][],side:DescentSide){const last=rows.at(-1)?.[0]??null;
  return {approach:phaseMetrics(rows,34,side.touchdown_s??last,side.touchdown_s!==null),
    contact_to_disarm:phaseMetrics(rows,side.touchdown_s,side.landed_s??last,side.landed_s!==null),
    disarmed:phaseMetrics(rows,side.landed_s,last,last===50)};
}

export function validBounds(b:Bounds){return Object.keys(b).sort().join()==='dwell,position,speed,tilt'&&Object.values(b).every(finite)&&b.position>=.01&&b.position<=1&&b.speed>=0&&b.speed<=1&&b.tilt>=0&&b.tilt<=25&&b.dwell>=.005&&b.dwell<=1;}
export function readiness(rows:number[][],side:DescentSide,b:Bounds){
  check(validBounds(b));let since:number|null=null,first:number|null=null,maxDwell=0,lastDwell=0;
  const chosen=rows.filter(r=>side.landed_s===null||r[0]<=side.landed_s+1e-9);
  for(const r of chosen){const eligible=!!side.rows[Math.round(r[0]/.005)][17]&&r[43]<=b.position&&r[44]<=b.speed&&r[41]<=b.tilt;
    since=eligible?(since??r[0]):null;lastDwell=since===null?0:r[0]-since;maxDwell=Math.max(maxDwell,lastDwell);
    if(since!==null&&lastDwell>=b.dwell-1e-9&&first===null)first=r[0];
  }
  const last=chosen.at(-1),blockers:string[]=[];
  if(side.landed_s!==null&&last){
    if(!side.rows[Math.round(last[0]/.005)][17])blockers.push('contact eligibility');
    if(last[43]>b.position)blockers.push('position');if(last[44]>b.speed)blockers.push('speed');if(last[41]>b.tilt)blockers.push('tilt');if(lastDwell<b.dwell-1e-9)blockers.push('dwell');
  }
  return {first_qualifying_s:first,evaluated_through_s:last?.[0]??null,samples:chosen.length,max_dwell_s:maxDwell,
    actual_disarm_s:side.landed_s,blockers_at_disarm:side.landed_s===null?null:blockers,
    interpretation:'Observed predicate only, through actual disarm. No alternate trajectory or acceptance claim.'};
}

export function selectionHash(s:Selection,digest:string){check(validBounds(s.bounds)&&HASH.test(digest)&&finite(s.time)&&s.time>=34&&s.time<=50);
  return '#'+new URLSearchParams({case:s.id,index:digest,t:s.time.toFixed(3),position:String(s.bounds.position),speed:String(s.bounds.speed),tilt:String(s.bounds.tilt),dwell:String(s.bounds.dwell)});
}
export function parseSelection(hash:string,digest:string):Selection|null{
  if(hash.length>350)return null;const p=new URLSearchParams(hash.slice(1));
  if([...p.keys()].sort().join()!=='case,dwell,index,position,speed,t,tilt'||p.get('index')!==digest)return null;
  if([...p.values()].some(v=>v.trim()===''))return null;
  const id=p.get('case')!,time=Number(p.get('t')),bounds={position:Number(p.get('position')),speed:Number(p.get('speed')),tilt:Number(p.get('tilt')),dwell:Number(p.get('dwell'))};
  if(!/^(regression-p[01]-s[012]|additional-p[01]-s(401|503|607))$/.test(id)||!finite(time)||time<34||time>50||!validBounds(bounds))return null;
  return {id,time,bounds};
}
export function contactExport(data:Contact,bounds:Bounds,digest:string,time:number){
  check(validBounds(bounds)&&HASH.test(digest)&&finite(time)&&time>=34&&time<=50);
  return {schema_version:1,kind:'landing_contact_review',id:data.descent.id,index_sha256:digest,cursor_s:time,bounds,columns:COLUMNS,descent_columns:DESCENT_COLUMNS,
    ...Object.fromEntries(MODES.map(mode=>{const s=data.descent[mode];return [mode,{status:s.status,failure_reason:s.failure_reason,gates:s.gates,outage:s.outage,
      provenance:s.provenance,touchdown_s:s.touchdown_s,landed_s:s.landed_s,rows:data[mode],descent_rows:s.rows.filter(r=>r[0]>=34),
      phases:phases(data[mode],s),episodes:episodes(s),readiness:readiness(data[mode],s,bounds)}];})),
    interpretation:'Retained PhysX evidence. Readiness and residual impulse are diagnostic; original mission/pair/recovery gates are unchanged.'};
}
