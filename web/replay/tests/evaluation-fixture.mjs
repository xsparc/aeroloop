// Synthetic display protocol only. Reuses published metric shapes; poses are not physics evidence.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
export const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const encode=value=>JSON.stringify(value);
function gates(m) {
  const route=m.mission;
  const rows=[['model_bounds','Model bounds exceeded',0,'count','eq',0],
    ['samples','Control samples',m.samples,'count','eq',10001],
    ['liftoff_start','Liftoff earliest',route.liftoff_time_s,'s','ge',2],
    ['liftoff_end','Liftoff deadline',route.liftoff_time_s,'s','lt',7],
    ['waypoints','Waypoint dwells reached',route.waypoint_reached_s.filter(v=>v!==null).length,'count','eq',4],
    ['peak_error','Peak position error',m.peak_error_m,'m','le',1],
    ['rmse','Position RMSE',m.position_rmse_m,'m','le',.5],
    ['tilt','Peak tilt',route.peak_tilt_deg,'deg','le',25],
    ['penetration','Peak penetration',route.max_penetration_m,'m','le',.003],
    ['contact','Unexpected contact samples',route.unexpected_contact_samples,'count','eq',0],
    ['touchdown','Touchdown deadline',route.touchdown_time_s,'s','lt',48],
    ['descent','Touchdown descent speed',route.touchdown_descent_speed_m_s,'m/s','le',.35],
    ['horizontal','Touchdown horizontal speed',route.touchdown_horizontal_speed_m_s,'m/s','le',.5],
    ['landed','Landed deadline',route.landed_time_s,'s','lt',48]];
  for(const [label,count] of [['initial_support',200],['final_support',401]]) {
    const fields=[['samples','count','eq',count],['mean_vertical_balance_error_n','N','abs_le',.05*9.80665],['peak_rotor_thrust_n','N','le',.01]];
    if(label==='final_support')fields.push(['peak_height_error_m','m','le',.003],['peak_speed_m_s','m/s','le',.05],['peak_tilt_deg','deg','le',3],['peak_xy_error_m','m','le',.35]);
    for(const [key,unit,op,limit] of fields)rows.push([`${label}_${key}`,`${label}: ${key}`,route[label]?.[key]??null,unit,op,limit,'support']);
  }
  return rows.map(([id,label,value,unit,operator,limit,group='mission'])=>({id,label,value,unit,operator,limit,group,
    status:value===null?'not_measured':({eq:value===limit,ge:value>=limit,lt:value<limit,le:value<=limit,abs_le:Math.abs(value)<=limit}[operator]?'passed':'failed')}));
}
export function fixture({failed=false,incomplete=false}={}) {
  const study=JSON.parse(readFileSync(new URL('../../../docs/evidence/isaac-flight-study-001.json',import.meta.url),'utf8'));
  study.source_commit='a'.repeat(40);study.source_tree_sha256='b'.repeat(64);
  const data={schema_version:1,kind:'flight_evaluation',study,cases:[],checksums:{},display:'Synthetic test display; not flight measurements'};
  if(failed||incomplete){
    const r=study.results.find(r=>r.seed===0&&r.physics_dt_s===.0025);
    r.status='failed';r.failure_reason='wind_mission_threshold';r.metrics.position_rmse_m=.6;
    if(incomplete){
      r.metrics.samples=2;r.timing.simulation_s=.005;r.timing.real_time_factor=.005/r.timing.elapsed_s;
      for(const f of ['liftoff_time_s','touchdown_time_s','landed_time_s','touchdown_descent_speed_m_s','touchdown_horizontal_speed_m_s'])r.metrics.mission[f]=null;
      r.metrics.mission.waypoint_reached_s=[null,null,null,null];r.metrics.mission.initial_support=null;r.metrics.mission.final_support=null;
      const c=study.comparisons.find(c=>c.seed===0&&c.physics_dt_s===.0025);
      Object.keys(c).forEach(k=>delete c[k]);Object.assign(c,{seed:0,physics_dt_s:.0025,reference_dt_s:.005,passed:false,reason:'incomplete_pair'});
    }else{
      const c=study.comparisons.find(c=>c.seed===0&&c.physics_dt_s===.0025);
      c.position_rmse_change_m=Math.abs(r.metrics.position_rmse_m-study.results.find(r=>r.seed===0&&r.physics_dt_s===.005).metrics.position_rmse_m);
      c.passed=false;
    }
    study.passed=8;study.accepted=false;
  }
  const documents={};
  for(const [i,row] of study.results.entries()) {
    const c={...row,run_id:`isaac-ground-mission-wind-${row.seed}-${i.toString(16).padStart(12,'0')}`,scenario:'ground-mission-wind',gates:gates(row.metrics)};
    data.cases.push(c);
    const manifest={schema_version:5,run_id:c.run_id,fixture:false,kind:'recorded_simulation',experiment:'isaac-quadrotor',model:'quadrotor-x-contact-wind-v1',controller:'rate-pid-v1',world_frame:'ENU',body_frame:'FLU',quaternion_order:'wxyz',units:'SI',scenario:c.scenario,seed:c.seed,status:c.status,failure_reason:c.failure_reason,source_dirty:false,config_sha256:c.config_sha256,
      ...Object.fromEntries(['source_commit','source_tree_sha256','controller_binary_sha256','lock_sha256'].map(k=>[k,study[k]]))};
    const times=row.metrics.samples===2?[0,.005]:[0,2,15,23,31,40,42,44,48,50];
    const replay={schema_version:5,kind:'recorded_simulation',run_id:c.run_id,samples:times.map(t=>({time_s:t,position_m:[t/100,0,.05+t/100],target_m:[0,0,1.5],quaternion_wxyz:[1,0,0,0],rotor_thrust_n:[2,2,2,2],wind_velocity_m_s:[1,0,0],external_force_n:[.1,0,0],external_moment_nm:[0,0,0],mission_phase:t<2?'grounded':t<40?'hover':'landing',contact_normal_force_n:[0,0,0],support_clearance_m:t/100}))};
    for(const [name,value] of Object.entries({manifest,replay,metrics:row.metrics,events:[]}))documents[`${c.run_id}/${name}.json`]=encode(value);
  }
  for(const [path,bytes] of Object.entries(documents))data.checksums[path]=hash(bytes);
  return {data,documents};
}
export async function routeFixture(page,options={}) {
  const result=fixture(options);
  const bytes=encode(result.data);
  await page.route('**/evaluation-config.json',r=>r.fulfill({json:{baseUrl:'/test-evaluation/',indexSha256:hash(bytes)}}));
  await page.route('**/test-evaluation/**',async route=>{
    const path=new URL(route.request().url()).pathname.split('/test-evaluation/')[1];
    const body=path==='evaluation.json'?bytes:result.documents[path];
    if(options.delay&&path.startsWith(options.delay))await new Promise(r=>setTimeout(r,350));
    await route.fulfill({status:body?200:404,contentType:'application/json',body:options.corrupt&&path.endsWith('/replay.json')?'{}':body??'{}'}).catch(()=>{});
  });
  return result;
}
