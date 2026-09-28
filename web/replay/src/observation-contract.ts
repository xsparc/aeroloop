import type {Vec3} from "./contracts.js";
export const PROFILES = ["ideal", "noise", "delay", "noise-delay"] as const;
export const TIMING_PROFILES = ["timing-ideal", "sample-hold", "dropout", "hold-dropout"] as const;
export const OUTAGE_WINDOWS = [[18,18.25],[40,40.25]] as const;
export type Profile = typeof PROFILES[number];
export type TimingProfile = typeof TIMING_PROFILES[number];
export const isTimingProfile = (profile:unknown):profile is TimingProfile => TIMING_PROFILES.includes(profile as TimingProfile);
export const capturePeriod = (profile:string) => ["sample-hold","hold-dropout"].includes(profile)?4:1;
export const outageActive = (time:number,profile:string) => profile.includes("dropout")&&OUTAGE_WINDOWS.some(([start,end])=>time>=start&&time<end);
export type Observation = {profile:Profile|TimingProfile; source_sequence:number; source_time_s:number; age_s:number; position_m:Vec3; velocity_m_s:Vec3};
const finite=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v);
function check(v:unknown):asserts v {if(!v)throw Error("Invalid observation contract");}
export function profileConfiguration(profile:Profile) {
  return {profile,position_sigma_m:profile.includes("noise")?.01:0,velocity_sigma_m_s:profile.includes("noise")?.02:0,
    clip_sigma:3,delay_steps:profile.includes("delay")?8:0,capture_dt_s:.005,startup:"hold-first",
    random_stream:"python-mt19937-gauss-xor-0x4f4253",channels:"position-velocity",
    ideal_channels:"attitude-rates-acceleration-supervisor-contact"};
}
export function validateProfiles(value:unknown) {
  check(Array.isArray(value)&&value.length===4);
  value.forEach((v,i)=>{
    const expected=profileConfiguration(PROFILES[i]);
    check(v&&typeof v==="object"&&Object.keys(v).length===Object.keys(expected).length);
    for(const [key,field] of Object.entries(expected))check(v[key]===field);
  });
}
export function validateObservation(value:unknown,time:number,profile:unknown):Observation {
  check(typeof profile==="string"&&(PROFILES.includes(profile as Profile)||isTimingProfile(profile)));
  check(value&&typeof value==="object"&&!Array.isArray(value));
  const o=value as Record<string,unknown>;
  check(Object.keys(o).sort().join()===["profile","source_sequence","source_time_s","age_s","position_m","velocity_m_s"].sort().join());
  check(o.profile===profile&&finite(time)&&time>=0&&time<=50);
  const sequence=Math.round(time/.005);
  let source=Math.max(0,sequence-(profile.includes("delay")?8:0));
  if(isTimingProfile(profile)) {
    const period=capturePeriod(profile);source=Math.floor(sequence/period)*period;
    if(profile.includes("dropout"))for(const [start,end] of OUTAGE_WINDOWS)
      if(source>=Math.round(start/.005)&&source<Math.round(end/.005))source=Math.floor((Math.round(start/.005)-1)/period)*period;
  }
  check(Math.abs(time-sequence*.005)<1e-9&&o.source_sequence===source);
  check(finite(o.source_time_s)&&Math.abs(o.source_time_s-source*.005)<1e-9
    &&finite(o.age_s)&&Math.abs(o.age_s-(sequence-source)*.005)<1e-9);
  for(const key of ["position_m","velocity_m_s"])check(Array.isArray(o[key])&&(o[key] as unknown[]).length===3
    &&(o[key] as unknown[]).every(v=>finite(v)&&Math.abs(v)<=1000));
  return o as Observation;
}
