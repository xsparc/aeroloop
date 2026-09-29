import {HASH, MISSION_PHASES, type Sample} from "./contracts.js";
import {validateObservation, type Observation} from "./observation-contract.js";
import {validateFeedback, type Feedback} from "./feedback-contract.js";
import {expectedGates, gateStatus, type Gate} from "./evaluation-contract.js";
import {validateGuard, type LandingGuard} from "./landing-contract.js";
export const OUTAGE_PROFILES=["sample-hold","hold-dropout","hold-dropout-500ms","hold-dropout-1000ms","hold-dropout-2000ms"] as const;
export const LABELS=["No outage","250 ms","500 ms","1 second","2 seconds"];
export type DemoCase={cohort?:string;profile:string;seed:number;file:string;sha256:string;baseline_status:string;candidate_status:string};
type Outcome={mission_passes:number;pair_passes:number;pair_count:number;recovery_passes:number;recovery_count:number;accepted:boolean};
export type DemoIndex={cohorts?:{id:string;seeds:number[];profiles:string[];baseline_source:string;candidate_source:string}[];cases:DemoCase[];study_sha256:string;baseline_source:string;candidate_source:string;display:string;outcomes:{cohort?:string;profile:string;baseline:Outcome;candidate:Outcome}[]};
export type DemoSample=Sample&{observation:Observation;feedback:Feedback;landing_guard?:LandingGuard};
export type Side={status:string;gates:Gate[];samples:DemoSample[]};
export type Pair={profile:string;seed:number;baseline:Side;candidate:Side};
function check(v:unknown):asserts v {if(!v)throw Error("Invalid outage demo evidence");}
function obj(v:unknown):Record<string,any> {check(v&&typeof v==="object"&&!Array.isArray(v));return v as Record<string,any>;}
function keys(v:Record<string,any>,names:string[]) {check(Object.keys(v).sort().join()===names.sort().join());}
const finite=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v);
const vector=(v:unknown,n:number)=>Array.isArray(v)&&v.length===n&&v.every(x=>finite(x)&&Math.abs(x)<=1000);
const status=(s:unknown)=>s==="passed"||s==="failed";
export function validateDemoIndex(value:unknown):DemoIndex {
  if(obj(value).schema_version===2)return validateLandingIndex(value);
  const d=obj(value);keys(d,["schema_version","kind","cases","study_sha256","baseline_source","candidate_source","display","outcomes"]);
  check(d.schema_version===1&&d.kind==="outage_demo"&&HASH.test(d.study_sha256)&&[d.baseline_source,d.candidate_source].every(s=>typeof s==="string"&&/^[a-f0-9]{40}$/.test(s)));
  check(typeof d.display==="string"&&d.display.length<200&&Array.isArray(d.cases)&&d.cases.length===15);
  d.cases.forEach((raw:unknown,i:number)=>{
    const c=obj(raw);keys(c,["profile","seed","file","sha256","baseline_status","candidate_status"]);
    check(c.profile===OUTAGE_PROFILES[Math.floor(i/3)]&&c.seed===i%3&&c.file===`p${Math.floor(i/3)}-s${i%3}.json`&&HASH.test(c.sha256)&&status(c.baseline_status)&&status(c.candidate_status));
  });
  check(Array.isArray(d.outcomes)&&d.outcomes.length===5);
  d.outcomes.forEach((raw:unknown,i:number)=>{
    const r=obj(raw);keys(r,["profile","baseline","candidate"]);check(r.profile===OUTAGE_PROFILES[i]);
    for(const name of ["baseline","candidate"]) {
      const o=obj(r[name]);keys(o,["profile","duration_s","mission_passes","pair_passes","pair_count","recovery_passes","recovery_count","excursion_windows","accepted"]);
      check(o.profile===r.profile&&o.duration_s===[0,.25,.5,1,2][i]&&o.pair_count===(i?3:0)&&o.recovery_count===(i?6:0));
      for(const [k,max] of [["mission_passes",3],["pair_passes",o.pair_count],["recovery_passes",o.recovery_count],["excursion_windows",o.recovery_count]] as const)check(Number.isInteger(o[k])&&o[k]>=0&&o[k]<=max);
      check(o.mission_passes===d.cases.filter((c:any)=>c.profile===r.profile&&c[`${name}_status`]==="passed").length);
      check(o.accepted===(o.mission_passes===3&&o.pair_passes===o.pair_count&&o.recovery_passes===o.recovery_count));
    }
  });return d as DemoIndex;
}
export function validatePair(value:unknown,entry:DemoCase):Pair {
  const guarded=entry.cohort!==undefined;
  const p=obj(value);keys(p,["schema_version","kind","profile","seed","baseline","candidate",...(guarded?["cohort"]:[])]);
  check(p.schema_version===(guarded?2:1)&&p.kind===(guarded?"landing_demo_pair":"outage_demo_pair")&&p.profile===entry.profile&&p.seed===entry.seed&&p.cohort===entry.cohort);
  for(const name of ["baseline","candidate"] as const) {
    const side=obj(p[name]);keys(side,["status","failure_reason","metrics","gates","samples"]);
    check(side.status===entry[`${name}_status`]&&status(side.status));
    check([null,"model_bounds_exceeded","wind_mission_threshold","wind_mission_support_threshold"].includes(side.failure_reason));
    check((side.status==="passed")===(side.failure_reason===null));
    const expected=expectedGates(side),seen=new Set();
    check(Array.isArray(side.gates)&&side.gates.length===Object.keys(expected).length);
    for(const raw of side.gates) {
      const g=obj(raw) as Gate;keys(g,["id","label","group","value","unit","operator","limit","status"]);
      check(Object.hasOwn(expected,g.id)&&!seen.has(g.id)&&typeof g.label==="string"&&g.label.length<200);
      check((g.value===null||finite(g.value))&&finite(g.limit)&&g.status===gateStatus(g));
      check(JSON.stringify([g.value,g.unit,g.operator,g.limit])===JSON.stringify(expected[g.id])&&g.group===(g.id.includes("_support_")?"support":"mission"));seen.add(g.id);
    }
    check((side.status==="passed")===side.gates.every((g:Gate)=>g.status==="passed"));
    check(Number.isInteger(side.metrics.samples)&&side.metrics.samples>=2&&side.metrics.samples<=10001);
    check(Array.isArray(side.samples)&&side.samples.length>=2&&side.samples.length<=1200);
    let last=-1;
    for(const raw of side.samples) {
      const s=obj(raw);keys(s,["time_s","position_m","target_m","quaternion_wxyz","rotor_thrust_n","wind_velocity_m_s","external_force_n","external_moment_nm","mission_phase","contact_normal_force_n","support_clearance_m","observation","feedback",...(guarded&&name==="candidate"?["landing_guard"]:[])]);
      check(finite(s.time_s)&&s.time_s>last&&s.time_s<=50&&s.time_s>=0&&Math.abs(s.time_s/.005-Math.round(s.time_s/.005))<1e-8);last=s.time_s;
      for(const k of ["position_m","target_m","wind_velocity_m_s","external_force_n","external_moment_nm","contact_normal_force_n"])check(vector(s[k],3));
      check(vector(s.quaternion_wxyz,4)&&Math.abs(Math.hypot(...s.quaternion_wxyz)-1)<1e-6&&vector(s.rotor_thrust_n,4)&&s.rotor_thrust_n.every((n:number)=>n>=0&&n<=5));
      check(MISSION_PHASES.includes(s.mission_phase)&&finite(s.support_clearance_m));
      validateFeedback(s.feedback,validateObservation(s.observation,s.time_s,p.profile),!guarded&&name==="baseline");
      if(guarded&&name==="candidate")validateGuard(s.landing_guard,s.time_s);
    }
    check(side.samples[0].time_s===0&&Math.abs(last-(side.metrics.samples-1)*.005)<1e-9);
  }return p as Pair;
}

const LANDING_COHORTS=[{id:"regression",seeds:[0,1,2],profiles:["sample-hold","hold-dropout-500ms","hold-dropout-1000ms","hold-dropout-2000ms"]},{id:"unseen",seeds:[101,202,303],profiles:["sample-hold","hold-dropout-2000ms"]}];
function validateLandingIndex(value:unknown):DemoIndex {
  const d=obj(value);keys(d,["schema_version","kind","cases","cohorts","study_sha256","baseline_source","candidate_source","display","outcomes"]);
  const source=(s:unknown)=>typeof s==="string"&&/^[a-f0-9]{40}$/.test(s);
  check(d.schema_version===2&&d.kind==="landing_demo"&&HASH.test(d.study_sha256)&&source(d.baseline_source)&&source(d.candidate_source));
  check(typeof d.display==="string"&&d.display.length<200&&Array.isArray(d.cases)&&d.cases.length===18&&Array.isArray(d.cohorts)&&d.cohorts.length===2&&Array.isArray(d.outcomes)&&d.outcomes.length===6);
  let row=0,outcome=0;
  LANDING_COHORTS.forEach((expected,c)=>{
    const meta=obj(d.cohorts[c]);keys(meta,["id","seeds","profiles","baseline_source","candidate_source"]);
    check(meta.id===expected.id&&JSON.stringify(meta.seeds)===JSON.stringify(expected.seeds)&&JSON.stringify(meta.profiles)===JSON.stringify(expected.profiles));
    check(meta.baseline_source===(c?d.candidate_source:d.baseline_source)&&meta.candidate_source===d.candidate_source);
    expected.profiles.forEach((profile,p)=>{
      for(const [j,seed] of expected.seeds.entries()) {
        const r=obj(d.cases[row++]);keys(r,["cohort","profile","seed","file","sha256","baseline_status","candidate_status"]);
        check(r.cohort===expected.id&&r.profile===profile&&r.seed===seed&&r.file===`c${c}-p${p}-s${j}.json`&&HASH.test(r.sha256)&&status(r.baseline_status)&&status(r.candidate_status));
      }
      const r=obj(d.outcomes[outcome++]);keys(r,["cohort","profile","baseline","candidate"]);check(r.cohort===expected.id&&r.profile===profile);
      for(const name of ["baseline","candidate"]) {
        const o=obj(r[name]);keys(o,["profile","duration_s","mission_passes","pair_passes","pair_count","recovery_passes","recovery_count","excursion_windows","accepted"]);
        check(o.profile===profile&&o.duration_s===[0,.25,.5,1,2][OUTAGE_PROFILES.indexOf(profile as typeof OUTAGE_PROFILES[number])]&&o.pair_count===(p?3:0)&&o.recovery_count===(p?6:0));
        for(const [key,max] of [["mission_passes",3],["pair_passes",o.pair_count],["recovery_passes",o.recovery_count],["excursion_windows",o.recovery_count]] as const)check(Number.isInteger(o[key])&&o[key]>=0&&o[key]<=max);
        check(o.mission_passes===d.cases.filter((e:any)=>e.cohort===expected.id&&e.profile===profile&&e[`${name}_status`]==="passed").length);
        check(o.accepted===(o.mission_passes===3&&o.pair_passes===o.pair_count&&o.recovery_passes===o.recovery_count));
      }
    });
  });return d as DemoIndex;
}
