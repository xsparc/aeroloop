import type {Observation} from "./observation-contract.js";
import type {Vec3} from "./contracts.js";
export type Feedback = {mode:"held"|"capture"|"predicting"|"expired"; position_m:Vec3; velocity_m_s:Vec3; disturbance_acceleration_m_s2:Vec3};
export function validateFeedback(value:unknown, observation:Observation, held=false):Feedback {
  function check(v:unknown):asserts v {if(!v)throw Error("Invalid predictive feedback");}
  check(value&&typeof value==="object"&&!Array.isArray(value));
  const f=value as Feedback;
  check(Object.keys(f).sort().join()===["mode","position_m","velocity_m_s","disturbance_acceleration_m_s2"].sort().join());
  const mode=held?"held":observation.age_s<.02?"capture":observation.age_s<=2.1?"predicting":"expired";
  check(f.mode===mode);
  for(const key of ["position_m","velocity_m_s","disturbance_acceleration_m_s2"] as const) {
    check(Array.isArray(f[key])&&f[key].length===3&&f[key].every(n=>typeof n==="number"&&Number.isFinite(n)&&Math.abs(n)<=1000));
    if(key!=="disturbance_acceleration_m_s2"&&mode!=="predicting")check(f[key].every((n,i)=>n===observation[key][i]));
  }
  check(f.disturbance_acceleration_m_s2.every(n=>Math.abs(n)<=4&&(!held||n===0)));
  return f;
}
