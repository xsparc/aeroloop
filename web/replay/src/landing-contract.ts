import {type Vec3} from "./contracts.js";
export type LandingGuard={mode:"inactive"|"holding"|"settling"|"descending"|"complete";activated_at_s:number|null;resumed_at_s:number|null;stable_for_s:number;target_m:Vec3;target_velocity_m_s:Vec3;target_acceleration_m_s2:Vec3};
export function validateGuard(value:unknown,time:number):LandingGuard {
  const check=(v:unknown)=>{if(!v)throw Error("Invalid landing guard");};
  check(value&&typeof value==="object"&&!Array.isArray(value));
  const g=value as LandingGuard;
  check(Object.keys(g).sort().join()===["mode","activated_at_s","resumed_at_s","stable_for_s","target_m","target_velocity_m_s","target_acceleration_m_s2"].sort().join());
  check(["inactive","holding","settling","descending","complete"].includes(g.mode));
  for(const t of [g.activated_at_s,g.resumed_at_s])check(t===null||(Number.isFinite(t)&&t>=34&&t<=time));
  check((g.mode==="inactive")===(g.activated_at_s===null));
  check(g.resumed_at_s===null||(g.activated_at_s!==null&&g.resumed_at_s>=g.activated_at_s));
  if(g.mode==="descending")check(g.resumed_at_s!==null);
  if(["holding","settling"].includes(g.mode))check(g.resumed_at_s===null);
  check(Number.isFinite(g.stable_for_s)&&g.stable_for_s>=0&&g.stable_for_s<=.3);
  for(const v of [g.target_m,g.target_velocity_m_s,g.target_acceleration_m_s2])check(Array.isArray(v)&&v.length===3&&v.every(n=>Number.isFinite(n)&&Math.abs(n)<=1000));
  return g;
}
