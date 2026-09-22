import { MISSION_PHASES, type Sample, type Vec3 } from "./contracts.js";

export type LiveSample = Sample & {
  sequence: number; velocity_m_s: Vec3; rates_rad_s: Vec3;
  rate_setpoint_rad_s: Vec3; effort_normalized: Vec3; allocation_scale: number;
};
export type LiveFrame = {
  state: "starting" | "running" | "verifying" | "completed" | "failed";
  seed: number; physics_dt_s: number; paced: boolean; elapsed_s: number;
  lag_s: number; max_lag_s: number; late_steps: number; age_s: number; stale: boolean;
  sample: LiveSample | null;
};
const finite = (n: unknown): n is number => typeof n === "number" && Number.isFinite(n);
function require(value: unknown): asserts value { if (!value) throw Error("Invalid live telemetry"); }
const vector = (v: unknown, size: number) => Array.isArray(v) && v.length === size && v.every(finite);
export function validateLive(value: unknown): LiveFrame | { state: "waiting" } {
  require(value && typeof value === "object" && !Array.isArray(value));
  const f = value as Record<string, unknown>;
  if (f.state === "waiting") { require(Object.keys(f).length === 1); return {state: "waiting"}; }
  require(Object.keys(f).sort().join() === ["schema_version", "state", "seed", "physics_dt_s", "paced", "elapsed_s", "lag_s", "max_lag_s", "late_steps", "age_s", "stale", "sample"].sort().join());
  require(f.schema_version === 1 && ["starting", "running", "verifying", "completed", "failed"].includes(String(f.state)));
  require(Number.isInteger(f.seed) && Number(f.seed) >= 0 && Number(f.seed) <= 2147483647);
  require([.005, .0025, .00125].includes(Number(f.physics_dt_s)) && finite(f.physics_dt_s));
  require(typeof f.paced === "boolean" && typeof f.stale === "boolean");
  for (const key of ["elapsed_s", "lag_s", "max_lag_s", "age_s"]) require(finite(f[key]) && Number(f[key]) >= 0);
  require(Number.isInteger(f.late_steps) && Number(f.late_steps) >= 0 && Number(f.late_steps) <= 10001);
  if (f.sample === null) require(["starting", "failed"].includes(String(f.state)));
  else {
    require(typeof f.sample === "object" && !Array.isArray(f.sample));
    const s = f.sample as Record<string, unknown>;
    require(Object.keys(s).sort().join() === ["time_s", "sequence", "position_m", "velocity_m_s", "quaternion_wxyz", "target_m", "rates_rad_s", "rate_setpoint_rad_s", "effort_normalized", "rotor_thrust_n", "allocation_scale", "wind_velocity_m_s", "external_force_n", "mission_phase", "contact_normal_force_n", "support_clearance_m"].sort().join());
    require(Number.isInteger(s.sequence) && Number(s.sequence) >= 0 && Number(s.sequence) <= 10000);
    require(finite(s.time_s) && Math.abs(s.time_s - Number(s.sequence)*.005) < 1e-8);
    require(MISSION_PHASES.includes(String(s.mission_phase)));
    for (const key of ["position_m", "velocity_m_s", "target_m", "rates_rad_s", "rate_setpoint_rad_s", "effort_normalized", "wind_velocity_m_s", "external_force_n", "contact_normal_force_n"]) require(vector(s[key], 3));
    require(vector(s.rotor_thrust_n, 4) && vector(s.quaternion_wxyz, 4));
    require(Math.abs(Math.hypot(...s.quaternion_wxyz as number[])-1) < 1e-6);
    require(finite(s.allocation_scale) && s.allocation_scale >= 0 && s.allocation_scale <= 1 && finite(s.support_clearance_m));
  }
  return f as unknown as LiveFrame;
}
export const positionError = (s: LiveSample) => Math.hypot(...s.position_m.map((v,i)=>v-s.target_m[i]));
export function historyAppend(history: LiveSample[], sample: LiveSample): LiveSample[] {
  const last = history.at(-1);
  if (last && sample.sequence < last.sequence) throw Error("Live sequence regressed");
  return last?.sequence === sample.sequence ? history : [...history.slice(-299), sample];
}
