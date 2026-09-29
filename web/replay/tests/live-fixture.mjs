// Synthetic live protocol fixture.
export function liveFixture(sequence=0) {
  return {schema_version:1,state:'running',seed:0,physics_dt_s:.0025,paced:true,elapsed_s:sequence*.005,
    lag_s:0,max_lag_s:0,late_steps:0,age_s:0,stale:false,
    sample:{time_s:sequence*.005,sequence,position_m:[0,0,1.5],velocity_m_s:[0,0,0],quaternion_wxyz:[1,0,0,0],
      target_m:[0,0,1.5],rates_rad_s:[0,0,0],rate_setpoint_rad_s:[0,0,0],effort_normalized:[0,0,0],
      rotor_thrust_n:[2.45,2.45,2.45,2.45],allocation_scale:1,wind_velocity_m_s:[1,0,0],external_force_n:[.1,0,0],
      mission_phase:'hover',contact_normal_force_n:[0,0,0],support_clearance_m:1.45}};
}
