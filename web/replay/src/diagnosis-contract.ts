import {HASH,MISSION_PHASES,type Sample} from './contracts.js';
import {expectedGates,gateStatus,type Gate} from './evaluation-contract.js';
export const QUALITY=['ideal','noise','delay','noise-delay'];
export const PROFILE=['sample-hold','hold-dropout-2000ms'];
export const PHASES=['other','airborne-descent','contact','motors-off'];
export const COLUMNS=['time_s','truth_z_m','raw_z_m','predictor_z_m','applied_z_m','applied_xy_error_m','applied_z_error_m','requested_thrust_n','contact_z_n','main_age_s','horizontal_age_s','reference_distance_m','phase_code'];
export type DiagnosisCase={id:string;file:string;sha256:string;quality:string;profile:string;seed:number;reference_id:string;status:string;samples:number;support_headroom_m:number|null};
export type PhaseGroup={phase:string;samples:number;horizontal_rmse_m:number|null;horizontal_peak_m:number|null;horizontal_peak_time_s:number|null;vertical_rmse_m:number|null;vertical_peak_m:number|null;vertical_peak_time_s:number|null};
export type PhaseErrors={start_s:number;end_s:number;sample_count:number;complete:boolean;groups:PhaseGroup[]};
export type Recovery={window_start_s:number;window_end_s:number;horizon_end_s:number;complete_horizon:boolean;recovery_time_s:number|null;passed:boolean;peak_position_difference_m:number|null};
export type Diagnosis={id:string;quality:string;profile:string;seed:number;reference_id:string;status:string;rows:number[][];poses:Sample[];
  events:{type:string;time_s:number}[];gates:(Gate&{headroom:number|null})[];phase_errors:PhaseErrors;metrics:any;
  comparison:null|{passed:boolean;recovery_passed:boolean;recovery_windows:Recovery[];landed_time_change_s?:number|null;reason?:string;[k:string]:any};
  provenance:{source_commit:string;source_tree_sha256:string;controller_binary_sha256:string;lock_sha256:string;config_sha256:string;samples_sha256:string;source_dirty:false;versions:Record<string,string>}};
function check(ok:unknown):asserts ok {if(!ok)throw Error('Invalid flight diagnosis');}
function object(v:unknown):Record<string,any>{check(v&&typeof v==='object'&&!Array.isArray(v));return v as Record<string,any>;}
function keys(v:Record<string,any>,names:string[]){check(Object.keys(v).sort().join()===names.slice().sort().join());}
const finite=(v:unknown):v is number=>typeof v==='number'&&Number.isFinite(v);
const close=(a:any,b:any)=>a===null||b===null?a===b:finite(a)&&finite(b)&&Math.abs(a-b)<1e-9;
const count=(v:any,min:number,max:number)=>Number.isInteger(v)&&v>=min&&v<=max;
export function headroom(g:Gate):number|null {
  if(g.value===null)return null;
  return {eq:-Math.abs(g.value-g.limit),le:g.limit-g.value,lt:g.limit-g.value,ge:g.value-g.limit,abs_le:g.limit-Math.abs(g.value)}[g.operator];
}
export function validateDiagnosisIndex(v:unknown):DiagnosisCase[]{
  const d=object(v);keys(d,['schema_version','kind','cases']);check(d.schema_version===1&&d.kind==='flight_diagnosis_index'&&Array.isArray(d.cases)&&d.cases.length===24);
  d.cases.forEach((raw:unknown,i:number)=>{
    const c=object(raw),q=Math.floor(i/6),p=Math.floor(i%6/3),s=i%3;
    keys(c,['id','file','sha256','quality','profile','seed','reference_id','status','samples','support_headroom_m']);
    check(c.id===`q${q}-p${p}-s${s}`&&c.file===c.id+'.json'&&HASH.test(c.sha256)&&c.quality===QUALITY[q]&&c.profile===PROFILE[p]&&c.seed===s&&c.reference_id===`q${q}-p0-s${s}`);
    check(['passed','failed'].includes(c.status)&&count(c.samples,2,10001)&&(c.status!=='passed'||c.samples===10001)&&(c.support_headroom_m===null||finite(c.support_headroom_m)));
  });return d.cases;
}
export function phaseErrors(rows:number[][]):PhaseErrors {
  const window=rows.filter(r=>r[0]>=40&&r[0]<42);
  return {start_s:40,end_s:42,sample_count:window.length,complete:window.length===400,groups:PHASES.map((phase,code)=>{
    const group=window.filter(r=>r[12]===code),item:any={phase,samples:group.length};
    for(const [axis,col] of [['horizontal',5],['vertical',6]] as const){
      const peak=group.reduce<number[]|null>((best,r)=>!best||r[col]>best[col]?r:best,null);
      item[axis+'_rmse_m']=group.length?Math.sqrt(group.reduce((s,r)=>s+r[col]**2,0)/group.length):null;
      item[axis+'_peak_m']=peak?.[col]??null;item[axis+'_peak_time_s']=peak?.[0]??null;
    }return item as PhaseGroup;
  })};
}
export function validateDiagnosis(v:unknown,entry:DiagnosisCase):Diagnosis{
  const d=object(v);keys(d,['schema_version','kind','id','quality','profile','seed','reference_id','status','metrics','failure_reason','columns','rows','poses','events','gates','phase_errors','comparison','provenance']);
  check(d.schema_version===1&&d.kind==='flight_diagnosis');
  for(const k of ['id','quality','profile','seed','reference_id','status'] as const)check(d[k]===entry[k]);
  check(JSON.stringify(d.columns)===JSON.stringify(COLUMNS)&&Array.isArray(d.rows)&&d.rows.length===entry.samples);
  const rows=d.rows as number[][];
  rows.forEach((r,i)=>{
    check(Array.isArray(r)&&r.length===13&&r.every(finite)&&close(r[0],i*.005)&&[5,6,7,9,10,11].every(j=>r[j]>=0)&&count(r[12],0,3));
    check(close(r[6],Math.abs(r[1]-r[4]))&&close(r[3],r[4])&&r[9]<=2.015+1e-9&&r[10]<=(entry.quality.includes('delay')?.055:.015)+1e-9);
    if(r[12]===3)check(r[7]===0);else if(r[12]===2)check(r[8]>.1);else check(r[8]<=.1);
  });
  check(Array.isArray(d.poses)&&d.poses.length>=2&&d.poses.length<=1200);
  let last=-1;
  for(const raw of d.poses){const p=object(raw);keys(p,['time_s','position_m','target_m','quaternion_wxyz','mission_phase']);
    const i=Math.round(p.time_s/.005);check(finite(p.time_s)&&p.time_s>last&&i<rows.length&&close(p.time_s,i*.005));last=p.time_s;
    for(const [name,n] of [['position_m',3],['target_m',3],['quaternion_wxyz',4]] as const)check(Array.isArray(p[name])&&p[name].length===n&&p[name].every(finite));
    check(Math.abs(Math.hypot(...p.quaternion_wxyz)-1)<1e-4&&close(p.position_m[2],rows[i][1])&&MISSION_PHASES.includes(p.mission_phase));
  }
  check(d.poses[0].time_s===0&&close(last,rows.at(-1)![0]));
  check(Array.isArray(d.events)&&d.events.length<=64);last=-1;
  for(const raw of d.events){const e=object(raw);keys(e,['type','time_s']);check([...MISSION_PHASES,'wind_start','liftoff','touchdown','gust_start','gust_end','outage-start','outage-end'].includes(e.type)&&finite(e.time_s)&&e.time_s>=last&&e.time_s<=rows.at(-1)![0]&&close(e.time_s,Math.round(e.time_s/.005)*.005));last=e.time_s;}
  check([null,'model_bounds_exceeded','wind_mission_threshold','wind_mission_support_threshold'].includes(d.failure_reason)&&(d.status==='passed')===(d.failure_reason===null)&&d.metrics.samples===rows.length);
  const expected=expectedGates(d);check(Array.isArray(d.gates)&&d.gates.length===24);
  const seen=new Set();for(const raw of d.gates){const g=object(raw) as Gate&{headroom:number|null};keys(g,['id','label','group','value','unit','operator','limit','status','headroom']);
    check(!seen.has(g.id)&&g.id in expected&&typeof g.label==='string'&&g.label.length<=100&&g.group===(g.id.includes('_support_')?'support':'mission')&&(g.value===null||finite(g.value)));
    check(JSON.stringify([g.value,g.unit,g.operator,g.limit])===JSON.stringify(expected[g.id])&&g.status===gateStatus(g)&&close(g.headroom,headroom(g)));seen.add(g.id);
  }
  check((d.status==='passed')===d.gates.every((g:Gate)=>g.status==='passed')&&close(entry.support_headroom_m,d.gates.find((g:Gate)=>g.id==='final_support_peak_xy_error_m').headroom));
  const expectedPhases=phaseErrors(rows),ph=object(d.phase_errors);keys(ph,['start_s','end_s','sample_count','complete','groups']);
  for(const k of ['start_s','end_s','sample_count','complete'] as const)check(ph[k]===expectedPhases[k]);
  check(Array.isArray(ph.groups)&&ph.groups.length===4);
  ph.groups.forEach((raw:any,i:number)=>{const g=object(raw),expected=expectedPhases.groups[i];keys(g,Object.keys(expected));
    for(const [k,value] of Object.entries(expected))check(typeof value==='string'?g[k]===value:close(g[k],value));});
  const p=object(d.provenance);keys(p,['source_commit','source_tree_sha256','controller_binary_sha256','lock_sha256','config_sha256','samples_sha256','source_dirty','versions']);
  check(/^[a-f0-9]{40}$/.test(p.source_commit)&&p.source_dirty===false);
  for(const k of ['source_tree_sha256','controller_binary_sha256','lock_sha256','config_sha256','samples_sha256'])check(typeof p[k]==='string'&&HASH.test(p[k]));
  keys(object(p.versions),['isaaclab','isaacsim','torch']);check(Object.values(p.versions).every(v=>typeof v==='string'&&/^[0-9A-Za-z.+-]{1,32}$/.test(v)));
  check(entry.profile===PROFILE[0]?d.comparison===null:d.comparison!==null);
  return d as Diagnosis;
}
export function validateDiagnosisPair(reference:Diagnosis,flight:Diagnosis){
  check(reference.id===flight.reference_id&&reference.profile===PROFILE[0]&&reference.quality===flight.quality&&reference.seed===flight.seed&&reference.rows.length>=flight.rows.length);
  for(const k of ['source_commit','source_tree_sha256','controller_binary_sha256','lock_sha256','versions'] as const)check(JSON.stringify(reference.provenance[k])===JSON.stringify(flight.provenance[k]));
  if(!flight.comparison){check(reference.id===flight.id&&flight.rows.every(r=>r[11]===0));return;}
  const c=object(flight.comparison),complete=reference.rows.length===10001&&flight.rows.length===10001;
  const base=['profile','seed','reference_profile','passed','recovery_windows','recovery_passed'];
  keys(c,[...base,...(complete?['peak_position_difference_m','position_difference_rmse_m','peak_attitude_difference_rad','position_rmse_change_m','landed_time_change_s']:['reason'])]);
  check(c.profile===flight.profile&&c.seed===flight.seed&&c.reference_profile===PROFILE[0]);
  if(!complete)check(c.reason==='incomplete_pair'&&c.passed===false);
  else {
    const distances=flight.rows.map(r=>r[11]),a=reference.metrics,b=flight.metrics;
    const landed=a.mission.landed_time_s===null||b.mission.landed_time_s===null?null:Math.abs(a.mission.landed_time_s-b.mission.landed_time_s);
    check(close(c.peak_position_difference_m,Math.max(...distances))&&close(c.position_difference_rmse_m,Math.sqrt(distances.reduce((s,x)=>s+x*x,0)/distances.length))&&close(c.position_rmse_change_m,Math.abs(a.position_rmse_m-b.position_rmse_m))&&close(c.landed_time_change_s,landed)&&finite(c.peak_attitude_difference_rad)&&c.peak_attitude_difference_rad>=0);
    check(c.passed===(c.peak_position_difference_m<=.15&&c.position_rmse_change_m<=.05&&landed!==null&&landed<=.5));
  }
  check(Array.isArray(c.recovery_windows)&&c.recovery_windows.length===2);
  c.recovery_windows.forEach((raw:unknown,j:number)=>{
    const w=object(raw),start=j?40:18,end=start+2,limit=j?10001:8000,stop=Math.min(flight.rows.length,limit),begin=Math.round(end/.005);
    const above=flight.rows.slice(Math.round(start/.005),stop).filter(r=>r[11]>.05),post=above.filter(r=>r[0]>=end);
    const settled=Math.max(begin,post.length?Math.round(post.at(-1)![0]/.005)+1:begin),full=stop===limit;
    const recovery=full&&stop-settled>=201?(settled-begin)*.005:null;
    keys(w,['window_start_s','window_end_s','horizon_end_s','complete_horizon','peak_position_difference_m','samples_above_band','post_outage_samples_above_band','excursion_observed','first_resumed_capture_s','difference_at_resumed_capture_m','recovery_time_s','passed']);
    const segment=flight.rows.slice(Math.round(start/.005),stop),resumed=flight.rows.slice(begin,stop).find(r=>r[9]===0);
    check(w.window_start_s===start&&w.window_end_s===end&&close(w.horizon_end_s,(limit-1)*.005)&&w.complete_horizon===full&&w.samples_above_band===above.length&&w.post_outage_samples_above_band===post.length&&w.excursion_observed===!!above.length&&close(w.peak_position_difference_m,segment.length?Math.max(...segment.map(r=>r[11])):null)&&close(w.first_resumed_capture_s,resumed?.[0]??null)&&close(w.difference_at_resumed_capture_m,resumed?.[11]??null)&&close(w.recovery_time_s,recovery)&&w.passed===(recovery!==null&&recovery<=5));
  });check(c.recovery_passed===c.recovery_windows.every((w:Recovery)=>w.passed));
}
export function windowCsv(flight:Diagnosis,start:number,end:number):string{
  check(finite(start)&&finite(end)&&start>=0&&end<=50&&start<=end);
  return [COLUMNS.join(','),...flight.rows.filter(r=>r[0]>=start&&r[0]<=end).map(r=>r.join(','))].join('\r\n')+'\r\n';
}
