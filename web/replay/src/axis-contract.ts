import {type Feedback} from "./feedback-contract.js";
import {type Vec3} from "./contracts.js";
export type AxisObservation={available_axes:"vertical"|"horizontal";source_sequence:number;source_time_s:number;age_s:number;position_m:(number|null)[];velocity_m_s:(number|null)[]};
export type AxisFeedback={mode:"vertical-fresh"|"horizontal-fresh";position_m:Vec3;velocity_m_s:Vec3};
function check(v:unknown):asserts v {if(!v)throw Error("Invalid axis feedback");}
function object(v:unknown):Record<string,any> {check(v&&typeof v==="object"&&!Array.isArray(v));return v as Record<string,any>;}
function keys(v:Record<string,any>,ks:string[]) {check(Object.keys(v).sort().join()===ks.sort().join());}
const finite=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v);
export function validateAxis(capture:unknown,feedback:unknown,prediction:Feedback,time:number,axes?:string) {
  const c=object(capture),f=object(feedback);
  keys(c,["available_axes","source_sequence","source_time_s","age_s","position_m","velocity_m_s"]);
  keys(f,["mode","position_m","velocity_m_s"]);
  check(["vertical","horizontal"].includes(c.available_axes)&&(axes===undefined||axes===c.available_axes));
  const sequence=Math.round(time/.005),source=Math.floor(sequence/4)*4;
  check(c.source_sequence===source&&finite(c.source_time_s)&&Math.abs(c.source_time_s-source*.005)<1e-9&&finite(c.age_s)&&Math.abs(c.age_s-(sequence-source)*.005)<1e-9);
  check(f.mode===c.available_axes+"-fresh");
  for(const key of ["position_m","velocity_m_s"] as const) {
    check(Array.isArray(c[key])&&c[key].length===3&&Array.isArray(f[key])&&f[key].length===3);
    for(let i=0;i<3;i++) {
      const selected=c.available_axes==="vertical"?i===2:i<2;
      check(selected?finite(c[key][i]):c[key][i]===null);
      check(finite(f[key][i])&&Math.abs(f[key][i]-(selected?c[key][i]:prediction[key][i]))<1e-12);
    }
  }
}
