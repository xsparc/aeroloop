import {HASH, validateRecording, type Entry, type Recording} from "./contracts.js";
import {readVerified} from "./load.js";

export type Gate = {id:string; label:string; group:string; value:number|null; unit:string;
  operator:"eq"|"le"|"lt"|"ge"|"abs_le"; limit:number; status:"passed"|"failed"|"not_measured"};
export type Case = Entry & {physics_dt_s:number; failure_reason:string|null; gates:Gate[];
  config_sha256:string; samples_sha256:string; metrics:Recording["metrics"];
  timing:{real_time_factor:number; elapsed_s:number; max_lag_s:number}};
export type Comparison = {seed:number; physics_dt_s:number; reference_dt_s:number; passed:boolean;
  reason?:"incomplete_pair"; peak_position_difference_m?:number; position_difference_rmse_m?:number;
  peak_attitude_difference_rad?:number; position_rmse_change_m?:number; landed_time_change_s?:number|null};
export type Evaluation = {cases:Case[]; checksums:Record<string,string>; display:string; study:{
  accepted:boolean; trials:number; passed:number; source_commit:string; source_tree_sha256:string;
  controller_binary_sha256:string; lock_sha256:string; comparisons:Comparison[]; limitations:string[]}};
const gateIds = ["model_bounds", "samples", "liftoff_start", "liftoff_end", "waypoints", "peak_error", "rmse",
  "tilt", "penetration", "contact", "touchdown", "descent", "horizontal", "landed",
  ...["initial_support", "final_support"].flatMap(s=>["samples", "mean_vertical_balance_error_n", "peak_rotor_thrust_n"].map(v=>`${s}_${v}`)),
  ...["peak_height_error_m", "peak_speed_m_s", "peak_tilt_deg", "peak_xy_error_m"].map(v=>`final_support_${v}`)];
function check(condition:unknown):asserts condition {if(!condition) throw Error("Invalid flight evaluation");}
function obj(value:unknown):Record<string,any> {check(value && typeof value==="object" && !Array.isArray(value));return value as Record<string,any>;}
const finite=(n:unknown):n is number=>typeof n==="number" && Number.isFinite(n);
const nonnegative=(n:unknown)=>finite(n)&&n>=0;
const short=(s:unknown)=>typeof s==="string"&&s.length>0&&s.length<=200;
function expectedGates(c:Record<string,any>):Record<string,[unknown,string,string,number]> {
  const m=obj(c.metrics), mission=obj(m.mission);
  check(Array.isArray(mission.waypoint_reached_s)&&mission.waypoint_reached_s.length===4
    && mission.waypoint_reached_s.every((v:unknown)=>v===null||nonnegative(v)));
  const values:Record<string,[unknown,string,string,number]>={
    model_bounds:[Number(c.failure_reason==="model_bounds_exceeded"),"count","eq",0],
    samples:[m.samples,"count","eq",10001],liftoff_start:[mission.liftoff_time_s,"s","ge",2],
    liftoff_end:[mission.liftoff_time_s,"s","lt",7],waypoints:[mission.waypoint_reached_s.filter((v:unknown)=>v!==null).length,"count","eq",4],
    peak_error:[m.peak_error_m,"m","le",1],rmse:[m.position_rmse_m,"m","le",.5],
    tilt:[mission.peak_tilt_deg,"deg","le",25],penetration:[mission.max_penetration_m,"m","le",.003],
    contact:[mission.unexpected_contact_samples,"count","eq",0],touchdown:[mission.touchdown_time_s,"s","lt",48],
    descent:[mission.touchdown_descent_speed_m_s,"m/s","le",.35],horizontal:[mission.touchdown_horizontal_speed_m_s,"m/s","le",.5],
    landed:[mission.landed_time_s,"s","lt",48],
  };
  for(const [label,count] of [["initial_support",200],["final_support",401]] as const) {
    const support=mission[label]===null?null:obj(mission[label]);
    const fields:[string,string,string,number][]=[["samples","count","eq",count],
      ["mean_vertical_balance_error_n","N","abs_le",.05*9.80665],["peak_rotor_thrust_n","N","le",.01]];
    if(label==="final_support")fields.push(["peak_height_error_m","m","le",.003],["peak_speed_m_s","m/s","le",.05],
      ["peak_tilt_deg","deg","le",3],["peak_xy_error_m","m","le",.35]);
    for(const [key,unit,op,limit] of fields) values[`${label}_${key}`]=[support===null?null:support[key],unit,op,limit];
  }
  return values;
}
export function gateStatus(g:Gate):Gate["status"] {
  if(g.value===null) return "not_measured";
  const v=g.value, l=g.limit;
  const pass={eq:v===l,le:v<=l,lt:v<l,ge:v>=l,abs_le:Math.abs(v)<=l}[g.operator];
  return pass?"passed":"failed";
}
export function validateEvaluation(value:unknown):Evaluation {
  const d=obj(value), s=obj(d.study), hashes=obj(d.checksums);
  check(d.schema_version===1 && d.kind==="flight_evaluation" && short(d.display));
  check(s.kind==="isaac_flight_timestep_study" && s.backend==="isaacsim_physx" && s.source_dirty===false
    && /^[a-f0-9]{40}$/.test(s.source_commit) && [s.source_tree_sha256,s.controller_binary_sha256,s.lock_sha256].every(v=>typeof v==="string"&&HASH.test(v))
    && s.trials===9 && s.control_dt_s===.005 && JSON.stringify(s.seeds)==="[0,1,2]"
    && Array.isArray(s.limitations) && s.limitations.length>=4 && s.limitations.length<=10 && s.limitations.every(short));
  check(Array.isArray(d.cases)&&d.cases.length===9 && Array.isArray(s.results)&&s.results.length===9);
  const matrix=new Set(), ids=new Set();
  for(const raw of d.cases) {
    const c=obj(raw);
    check([.005,.0025,.00125].includes(c.physics_dt_s) && [0,1,2].includes(c.seed)
      && c.scenario==="ground-mission-wind" && typeof c.run_id==="string"
      && new RegExp(`^isaac-ground-mission-wind-${c.seed}-[a-f0-9]{12}$`).test(c.run_id)
      && ["passed","failed"].includes(c.status) && (c.status==="passed")===(c.failure_reason===null)
      && [null,"model_bounds_exceeded","wind_mission_threshold","wind_mission_support_threshold"].includes(c.failure_reason)
      && [c.config_sha256,c.samples_sha256].every(v=>typeof v==="string"&&HASH.test(v)));
    const key=`${c.physics_dt_s}/${c.seed}`;check(!matrix.has(key)&&!ids.has(c.run_id));matrix.add(key);ids.add(c.run_id);
    const result=s.results.find((r:any)=>r.physics_dt_s===c.physics_dt_s&&r.seed===c.seed);check(result);
    for(const k of ["status","failure_reason","config_sha256","samples_sha256","metrics","timing"])
      check(JSON.stringify(c[k])===JSON.stringify(result[k]));
    const t=obj(c.timing), m=obj(c.metrics);
    check(finite(t.elapsed_s)&&t.elapsed_s>0 && nonnegative(t.max_lag_s)&&finite(t.real_time_factor)&&t.real_time_factor>0
      && t.paced===true&&t.monitor_enabled===true && nonnegative(t.simulation_s)
      && Math.abs(t.real_time_factor-t.simulation_s/t.elapsed_s)<1e-12
      && Number.isInteger(m.samples)&&m.samples>=2&&m.samples<=10001
      && Math.abs(t.simulation_s-(m.samples-1)*.005)<1e-9
      && (m.position_rmse_m===null||nonnegative(m.position_rmse_m)));
    check(Array.isArray(c.gates)&&c.gates.length===gateIds.length);
    const seen=new Set(), expected=expectedGates(c);
    for(const rawGate of c.gates) {
      const g=obj(rawGate) as Gate;
      check(gateIds.includes(g.id)&&!seen.has(g.id)&&short(g.label)&&["mission","support"].includes(g.group)
        && ["count","s","m","m/s","deg","N"].includes(g.unit)&&["eq","le","lt","ge","abs_le"].includes(g.operator)
        && finite(g.limit)&&(g.value===null||finite(g.value))&&g.status===gateStatus(g));
      check(JSON.stringify([g.value,g.unit,g.operator,g.limit])===JSON.stringify(expected[g.id])
        && g.group===(g.id.includes("_support_")?"support":"mission"));seen.add(g.id);
    }
    check((c.status==="passed")===c.gates.every((g:Gate)=>g.status==="passed"));
    for(const name of ["replay","manifest","metrics","events"])check(typeof hashes[`${c.run_id}/${name}.json`]==="string"&&HASH.test(hashes[`${c.run_id}/${name}.json`]));
  }
  check(Object.keys(hashes).length===36 && Array.isArray(s.comparisons)&&s.comparisons.length===6);
  const pairs=new Set();
  for(const raw of s.comparisons) {
    const c=obj(raw);const key=`${c.physics_dt_s}/${c.seed}`;
    check([.0025,.00125].includes(c.physics_dt_s)&&c.reference_dt_s===.005&&[0,1,2].includes(c.seed)&&!pairs.has(key));pairs.add(key);
    const pair=d.cases.filter((r:Case)=>r.seed===c.seed&&[.005,c.physics_dt_s].includes(r.physics_dt_s));
    if(c.reason==="incomplete_pair")check(c.passed===false && pair.some((r:Case)=>r.metrics.samples!==10001)
      && Object.keys(c).length===5);
    else {
      check(c.reason===undefined && pair.every((r:Case)=>r.metrics.samples===10001)
        && [c.peak_position_difference_m,c.position_difference_rmse_m,c.peak_attitude_difference_rad,c.position_rmse_change_m].every(nonnegative)
        && (c.landed_time_change_s===null||nonnegative(c.landed_time_change_s)));
      check(c.passed===(c.peak_position_difference_m<=.15 && c.position_rmse_change_m<=.05
        && c.landed_time_change_s!==null && c.landed_time_change_s<=.5));
      const [a,b]=pair.map((r:Case)=>r.metrics);
      check(Math.abs(c.position_rmse_change_m-Math.abs(a.position_rmse_m!-b.position_rmse_m!))<1e-12);
      const landed=pair.map((r:Case)=>r.metrics.mission?.landed_time_s);
      check(landed.some((t:unknown)=>t==null)?c.landed_time_change_s===null:
        finite(c.landed_time_change_s)&&Math.abs(c.landed_time_change_s-Math.abs(landed[0]!-landed[1]!))<1e-12);
    }
  }
  check(s.passed===d.cases.filter((c:Case)=>c.status==="passed").length
    && s.accepted===(s.passed===9&&s.comparisons.every((c:Comparison)=>c.passed)));
  return d as unknown as Evaluation;
}
export async function loadEvaluation(base:URL,hash:string,signal:AbortSignal) {
  return validateEvaluation(await readVerified(new URL("evaluation.json",base),hash,signal,256*1024));
}
export async function loadEvaluationRecording(base:URL,data:Evaluation,entry:Case,signal:AbortSignal) {
  const docs=await Promise.all(["replay","manifest","metrics","events"].map(name=>{
    const path=`${entry.run_id}/${name}.json`;
    return readVerified(new URL(path,base),data.checksums[path],signal,name==="replay"?4*1024*1024:65536);
  }));
  const recording=validateRecording(entry,...(docs as [unknown,unknown,unknown,unknown]));
  const m=obj(docs[1]);
  for(const key of ["source_commit","source_tree_sha256","controller_binary_sha256","lock_sha256"] as const)
    check(m[key]===data.study[key]);
  check(m.source_dirty===false&&m.config_sha256===entry.config_sha256
    && JSON.stringify(recording.metrics)===JSON.stringify(entry.metrics)
    && Math.abs(recording.samples.at(-1)!.time_s-(entry.metrics.samples-1)*.005)<1e-9);
  return recording;
}
