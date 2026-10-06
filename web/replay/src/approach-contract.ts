import {HASH,MISSION_PHASES,type Sample} from './contracts.js';
import {expectedGates,gateStatus,type Gate} from './evaluation-contract.js';
import {headroom} from './diagnosis-contract.js';
import {gainParameters} from './approach-gains.js';
export const COLUMNS=["time_s", "truth_x_m", "truth_y_m", "truth_vx_m_s", "truth_vy_m_s", "feedback_x_m", "feedback_y_m", "feedback_vx_m_s", "feedback_vy_m_s", "target_x_m", "target_y_m", "target_vx_m_s", "target_vy_m_s", "integral_x_m_s2", "integral_y_m_s2", "feedforward_x_m_s2", "feedforward_y_m_s2", "gain_blend", "horizontal_kp_s2", "horizontal_kd_s", "clipped_ax_m_s2", "clipped_ay_m_s2", "allocation_scale", "wind_fx_n", "wind_fy_n", "thrust_fx_n", "thrust_fy_n", "normal_n", "clearance_m", "truth_vz_m_s", "landed", "horizontal_error_m", "horizontal_speed_m_s", "squared_error_integral_m2_s", "squared_demand_integral_m2_s3", "axis_clipped", "horizontal_energy_j", "tilt_deg", "truth_z_m", "requested_thrust_n", "realized_thrust_n", "target_z_m"];
export const CONFIGURATION={"kind": "approach-gains-v1", "position_kp": 2.5, "velocity_kd": 2.8, "integral_ki": [0.6, 0.6, 0.0], "integral_limit_m_s2": [1.5, 1.5, 0.0], "acceleration_limit_m_s2": 4.0, "feedforward": true, "reset_when_disarmed": true, "freeze_on_allocation_saturation": true, "horizontal_position_kp": 4.0, "horizontal_velocity_kd": 3.6, "ramp_start_s": 34.0, "ramp_duration_s": 1.0, "ramp": "quintic"};
export const COHORTS=['regression','stress','additional'],PROFILES=['sample-hold','hold-dropout-2000ms'];
export const SEEDS=[[0,1,2],[401,503,607],[709,811,907]];
export type ApproachCase={id:string;file:string;sha256:string;cohort:string;profile:string;seed:number;baseline_status:string;candidate_status:string;regressed_gates:number;improved_gates:number};
type ScoredGate=Gate&{headroom:number|null};
type Outage={passed:boolean;recovery_passed:boolean;peak_distance_m:number|null;rmse_change_m:number|null;landed_change_s:number|null;recovery:{time_s:number|null;passed:boolean;complete:boolean}[]};
export type Diagnostics={samples:number;complete:boolean;squared_error_integral_m2_s:number|null;squared_demand_integral_m2_s3:number|null;axis_clipped_fraction:number|null;minimum_allocation_scale:number|null;peak_horizontal_error_m:number|null};
export type Side={status:string;failure_reason:string|null;gates:ScoredGate[];rows:number[][];poses:Sample[];touchdown_s:number|null;landed_s:number|null;diagnostics:Diagnostics;outage:Outage|null;provenance:Record<string,any>};
export type Approach={id:string;cohort:string;profile:string;seed:number;baseline:Side;candidate:Side;gate_changes:ReturnType<typeof gateChanges>};
function check(v:unknown):asserts v {if(!v)throw Error('Invalid approach comparison');}
function obj(v:unknown):Record<string,any>{check(v&&typeof v==='object'&&!Array.isArray(v));return v as Record<string,any>;}
function keys(v:Record<string,any>,names:string[]){check(Object.keys(v).sort().join()===names.slice().sort().join());}
const finite=(v:unknown):v is number=>typeof v==='number'&&Number.isFinite(v);
const close=(a:any,b:any)=>a===null||b===null?a===b:finite(a)&&finite(b)&&Math.abs(a-b)<1e-8;
const clip=(v:number)=>Math.max(-4,Math.min(4,v));
export function validateApproachIndex(value:unknown):ApproachCase[]{
  const d=obj(value);keys(d,['schema_version','kind','cases']);check(d.schema_version===1&&d.kind==='approach_comparison_index'&&Array.isArray(d.cases)&&d.cases.length===18);
  d.cases.forEach((raw:unknown,i:number)=>{const c=obj(raw),ci=Math.floor(i/6),cohort=COHORTS[ci],p=Math.floor(i%6/3),seed=SEEDS[ci][i%3];
    keys(c,['id','file','sha256','cohort','profile','seed','baseline_status','candidate_status','regressed_gates','improved_gates']);
    check(c.id===`${cohort}-p${p}-s${seed}`&&c.file===c.id+'.json'&&HASH.test(c.sha256)&&c.cohort===cohort&&c.profile===PROFILES[p]&&c.seed===seed&&['passed','failed'].includes(c.baseline_status)&&['passed','failed'].includes(c.candidate_status));
    for(const k of ['regressed_gates','improved_gates'])check(Number.isInteger(c[k])&&c[k]>=0&&c[k]<=24);
    check(c.regressed_gates+c.improved_gates<=24);
  });return d.cases;
}
export function diagnostics(rows:number[][]):Diagnostics{
  return {samples:rows.length,complete:rows.length===3201,
    squared_error_integral_m2_s:rows.at(-1)?.[33]??null,squared_demand_integral_m2_s3:rows.at(-1)?.[34]??null,
    axis_clipped_fraction:rows.length>1?rows.slice(0,-1).reduce((a,r)=>a+r[35],0)/(rows.length-1):null,
    minimum_allocation_scale:rows.length?Math.min(...rows.map(r=>r[22])):null,
    peak_horizontal_error_m:rows.length?Math.max(...rows.map(r=>r[31])):null};
}
export function gateChanges(a:ScoredGate[],b:ScoredGate[]){
  return a.map((x,i)=>{const y=b[i];check(x.id===y.id);return {id:x.id,
    change:x.status===y.status?'unchanged':y.status==='passed'?'improved':x.status==='passed'?'regressed':'changed',
    headroom_delta:x.headroom!==null&&y.headroom!==null?y.headroom-x.headroom:null};});
}
export function validateApproach(value:unknown,entry:ApproachCase):Approach{
  const d=obj(value);keys(d,['schema_version','kind','id','cohort','profile','seed','columns','configuration','gate_changes','baseline','candidate']);
  check(d.schema_version===1&&d.kind==='approach_comparison'&&JSON.stringify(d.columns)===JSON.stringify(COLUMNS));
  keys(obj(d.configuration),Object.keys(CONFIGURATION));for(const [k,v] of Object.entries(CONFIGURATION))check(JSON.stringify(d.configuration[k])===JSON.stringify(v));
  for(const k of ['id','cohort','profile','seed'] as const)check(d[k]===entry[k]);
  for(const mode of ['baseline','candidate'] as const){const s=obj(d[mode]);
    keys(s,['status','failure_reason','gates','rows','poses','touchdown_s','landed_s','diagnostics','outage','provenance']);
    check(s.status===entry[mode+'_status' as 'baseline_status']&&[null,'model_bounds_exceeded','wind_mission_threshold','wind_mission_support_threshold'].includes(s.failure_reason)&&(s.status==='passed')===(s.failure_reason===null));
    check(Array.isArray(s.rows)&&s.rows.length<=3201);let since:number|null=null,landed=false;
    const rows=s.rows as number[][];
    rows.forEach((r,i)=>{
      check(Array.isArray(r)&&r.length===42&&r.every(finite)&&close(r[0],34+i*.005));
      const eligible=r[27]>.1&&r[28]<=.015&&Math.abs(r[29])<=.2;
      since=eligible?(since??r[0]):null;if(since!==null&&r[0]-since>=.05-1e-9)landed=true;check(r[30]===Number(landed));
      const gains=mode==='candidate'?gainParameters(r[0],!landed):[0,2.5,2.8];
      check(gains.every((v,a)=>close(v,r[17+a])));
      const demand=[0,1].map(a=>landed?0:r[15+a]+r[18]*(r[9+a]-r[5+a])+r[19]*(r[11+a]-r[7+a])+r[13+a]);
      check(close(r[20],clip(demand[0]))&&close(r[21],clip(demand[1]))&&r[35]===Number(demand.some(v=>Math.abs(v)>4)));
      check(r[22]>=0&&r[22]<=1&&r[37]>=0&&r[37]<=180&&Math.abs(r[13])<=1.5&&Math.abs(r[14])<=1.5);
      check(close(r[31],Math.hypot(r[1]-r[9],r[2]-r[10]))&&close(r[32],Math.hypot(r[3],r[4]))&&close(r[36],.5*r[32]**2));
      const prev=rows[i-1],dt=i?r[0]-prev[0]:0;
      check(close(r[33],i?prev[33]+prev[31]**2*dt:0)&&close(r[34],i?prev[34]+(prev[20]**2+prev[21]**2)*dt:0));
      check(r[39]>=0&&r[39]<=20&&r[40]>=0&&r[40]<=20&&Math.hypot(r[25],r[26])<=r[40]+1e-8);
      if(landed)check(r[39]===0&&r.slice(11,17).every(v=>v===0));
    });
    check(close(s.touchdown_s,rows.find(r=>r[27]>.1)?.[0]??null)&&close(s.landed_s,rows.find(r=>r[30])?.[0]??null));
    const expected=diagnostics(rows);keys(obj(s.diagnostics),Object.keys(expected));for(const [k,v] of Object.entries(expected))check(typeof v==='boolean'?s.diagnostics[k]===v:close(s.diagnostics[k],v));
    check(Array.isArray(s.poses)&&s.poses.length>=2&&s.poses.length<=1200);let last=-1;
    for(const raw of s.poses){const p=obj(raw);keys(p,['time_s','position_m','target_m','quaternion_wxyz','mission_phase']);
      check(finite(p.time_s)&&p.time_s>last&&p.time_s<=50&&close(p.time_s,Math.round(p.time_s/.005)*.005));last=p.time_s;
      for(const [k,n] of [['position_m',3],['target_m',3],['quaternion_wxyz',4]] as const)check(Array.isArray(p[k])&&p[k].length===n&&p[k].every(finite));
      check(MISSION_PHASES.includes(p.mission_phase)&&Math.abs(Math.hypot(...p.quaternion_wxyz)-1)<1e-6);
      if(p.time_s>=34){const r=rows[Math.round((p.time_s-34)/.005)];check(r);
        check(p.position_m.every((v:number,a:number)=>close(v,r[[1,2,38][a]]))&&p.target_m.every((v:number,a:number)=>close(v,r[[9,10,41][a]]))&&(p.mission_phase==='landed')===!!r[30]);
        check(close(r[37],Math.acos(Math.max(-1,Math.min(1,1-2*(p.quaternion_wxyz[1]**2+p.quaternion_wxyz[2]**2))))*180/Math.PI));
      }
    }check(s.poses[0].time_s===0&&(rows.length?close(last,rows.at(-1)![0]):last<34));
    const definitions=expectedGates({metrics:{mission:{waypoint_reached_s:[null,null,null,null],initial_support:null,final_support:null}}});
    check(Array.isArray(s.gates)&&s.gates.length===24);const seen=new Set();
    for(const raw of s.gates){const g=obj(raw) as ScoredGate;keys(g,['id','label','group','value','unit','operator','limit','status','headroom']);
      check(g.id in definitions&&!seen.has(g.id)&&typeof g.label==='string'&&g.label.length<=100&&g.group===(g.id.includes('_support_')?'support':'mission')&&(g.value===null||finite(g.value)));
      check(JSON.stringify([g.unit,g.operator,g.limit])===JSON.stringify(definitions[g.id].slice(1))&&g.status===gateStatus(g)&&close(g.headroom,headroom(g)));seen.add(g.id);
    }
    const gate=(id:string)=>s.gates.find((g:Gate)=>g.id===id).value;
    check(gate('samples')===Math.round(last/.005)+1&&close(gate('touchdown'),s.touchdown_s)&&close(gate('landed'),s.landed_s)&&gate('model_bounds')===Number(s.failure_reason==='model_bounds_exceeded'));
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
  const changes=gateChanges(d.baseline.gates,d.candidate.gates);check(Array.isArray(d.gate_changes)&&d.gate_changes.length===24);
  changes.forEach((c,i)=>{const g=obj(d.gate_changes[i]);keys(g,Object.keys(c));check(g.id===c.id&&g.change===c.change&&close(g.headroom_delta,c.headroom_delta));});
  check(entry.regressed_gates===changes.filter(c=>c.change==='regressed').length&&entry.improved_gates===changes.filter(c=>c.change==='improved').length);
  return d as Approach;
}
export type Selection={id:string;time:number;relative:boolean};
export function parseSelection(hash:string,digest:string):Selection|null{
  if(hash.length>220)return null;const p=new URLSearchParams(hash.slice(1));
  if([...p.keys()].sort().join()!=='case,index,relative,t'||p.get('index')!==digest)return null;
  const id=p.get('case')!,time=Number(p.get('t')),relative=p.get('relative');
  if(!COHORTS.some((c,i)=>SEEDS[i].some(s=>[0,1].some(n=>id===`${c}-p${n}-s${s}`)))||!finite(time)||time<34||time>50||!['0','1'].includes(relative!))return null;
  return {id,time,relative:relative==='1'};
}
export function selectionHash(s:Selection,digest:string){return '#'+new URLSearchParams({case:s.id,index:digest,relative:s.relative?'1':'0',t:s.time.toFixed(3)});}
export function reviewExport(d:Approach,s:Selection,digest:string){
  check(HASH.test(digest)&&d.id===s.id&&parseSelection(selectionHash(s,digest),digest));
  return {schema_version:1,kind:'approach_gain_review',index_sha256:digest,selection:s,columns:COLUMNS,configuration:CONFIGURATION,
    id:d.id,cohort:d.cohort,profile:d.profile,seed:d.seed,gate_changes:d.gate_changes,baseline:d.baseline,candidate:d.candidate,
    interpretation:'Descriptive landing metrics; original mission, same-mode outage pair and recovery gates remain authoritative. Demand is not physical energy.'};
}
