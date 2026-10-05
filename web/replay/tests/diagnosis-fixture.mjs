// Synthetic contract fixtures; never measured flight evidence.
import {fixture as qualityFixture} from './quality-fixture.mjs';
import {hash} from './evaluation-fixture.mjs';
import {COLUMNS,phaseErrors,headroom} from '../dist/diagnosis-contract.js';
import {expectedGates,gateStatus} from '../dist/evaluation-contract.js';
export function fixture({incomplete=false}={}){
  const old=qualityFixture(),source=JSON.parse(old.documents['q0-s0.json']).candidate;
  const index={schema_version:1,kind:'flight_diagnosis_index',cases:[]},documents={};
  for(const [q,quality] of ['ideal','noise','delay','noise-delay'].entries())for(const [p,profile] of ['sample-hold','hold-dropout-2000ms'].entries())for(let seed=0;seed<3;seed++){
    const id=`q${q}-p${p}-s${seed}`,reference_id=`q${q}-p0-s${seed}`,count=incomplete&&p?100:10001;
    const rows=Array.from({length:count},(_,i)=>[i*.005,1,1,1,1,0,0,9,0,0,0,0,0]);
    const metrics=structuredClone(source.metrics);metrics.samples=count;metrics.peak_error_m=.1;metrics.position_rmse_m=.05;metrics.mission.touchdown_horizontal_speed_m_s=.1;
    const failed=q===3&&p===1&&seed===0;metrics.mission.final_support.peak_xy_error_m=failed?.351:0;
    const failure_reason=count!==10001?'wind_mission_threshold':failed?'wind_mission_support_threshold':null;
    const expected=expectedGates({metrics,failure_reason}),gates=source.gates.map(g=>{const [value,unit,operator,limit]=expected[g.id];const next={...g,value,unit,operator,limit};next.status=gateStatus(next);return {...next,headroom:headroom(next)};});
    const status=gates.every(g=>g.status==='passed')?'passed':'failed';
    const comparison=p?{profile,seed,reference_profile:'sample-hold',passed:count===10001,...(count===10001?{peak_position_difference_m:0,position_difference_rmse_m:0,peak_attitude_difference_rad:0,position_rmse_change_m:0,landed_time_change_s:0}:{reason:'incomplete_pair'}),recovery_passed:count===10001,recovery_windows:[18,40].map((start,j)=>({window_start_s:start,window_end_s:start+2,horizon_end_s:j?50:39.995,complete_horizon:count===10001,peak_position_difference_m:count===10001?0:null,samples_above_band:0,post_outage_samples_above_band:0,excursion_observed:false,first_resumed_capture_s:count===10001?start+2:null,difference_at_resumed_capture_m:count===10001?0:null,recovery_time_s:count===10001?0:null,passed:count===10001}))}:null;
    const body={schema_version:1,kind:'flight_diagnosis',id,quality,profile,seed,reference_id,status,metrics,failure_reason,columns:COLUMNS,rows,
      poses:[0,rows.at(-1)[0]].map(time_s=>({time_s,position_m:[0,0,1],target_m:[0,0,1],quaternion_wxyz:[1,0,0,0],mission_phase:'hover'})),
      events:[{time_s:0,type:'grounded'},...(count===10001?[{time_s:41.225,type:'touchdown'},{time_s:41.285,type:'landed'}]:[])],gates,phase_errors:phaseErrors(rows),comparison,
      provenance:{source_commit:'b'.repeat(40),source_tree_sha256:'c'.repeat(64),controller_binary_sha256:'d'.repeat(64),lock_sha256:'e'.repeat(64),config_sha256:'f'.repeat(64),samples_sha256:'a'.repeat(64),source_dirty:false,versions:{isaaclab:'17.0.2',isaacsim:'6.1.0.0',torch:'2.11.0+cu128'}}};
    const file=id+'.json';documents[file]=JSON.stringify(body);
    index.cases.push({id,file,sha256:hash(documents[file]),quality,profile,seed,reference_id,status,samples:count,support_headroom_m:gates.find(g=>g.id==='final_support_peak_xy_error_m').headroom});
  }return {index,documents};
}
export async function routeFixture(page,options={}){
  const data=fixture(options),bytes=JSON.stringify(data.index);
  await page.route('**/diagnosis-config.json',r=>r.fulfill({json:{baseUrl:'/test-diagnosis/',indexSha256:hash(bytes)}}));
  await page.route('**/test-diagnosis/**',async r=>{const file=new URL(r.request().url()).pathname.split('/test-diagnosis/')[1];
    if(options.delay&&file==='q3-p1-s0.json')await new Promise(resolve=>setTimeout(resolve,500));
    const body=file==='index.json'?bytes:data.documents[file];
    await r.fulfill({status:body?200:404,contentType:'application/json',body:options.corrupt&&file.startsWith('q')?'{}':body??'{}'}).catch(()=>{});
  });return data;
}
