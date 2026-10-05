import type {Observation} from './observation-contract.js';
import type {Feedback} from './feedback-contract.js';
export type VerticalDecay={kind:'vertical-disturbance-decay-v1';scale:number;anchor_z_m_s2:number;effective_z_m_s2:number};
export function validateDecay(value:unknown,o:Observation,f:Feedback):VerticalDecay {
  const d=value as VerticalDecay;
  if(!d||Object.keys(d).sort().join()!==['kind','scale','anchor_z_m_s2','effective_z_m_s2'].sort().join()
    ||d.kind!=='vertical-disturbance-decay-v1'||![d.scale,d.anchor_z_m_s2,d.effective_z_m_s2].every(Number.isFinite)
    ||Math.abs(d.anchor_z_m_s2)>4||d.scale<=0||d.scale>1
    ||Math.abs(d.scale-Math.exp(-Math.max(0,o.age_s-.015)/.2))>1e-12
    ||Math.abs(d.effective_z_m_s2-d.anchor_z_m_s2*d.scale)>1e-12
    ||d.effective_z_m_s2!==f.disturbance_acceleration_m_s2[2])throw Error('Invalid vertical decay telemetry');
  return d;
}
