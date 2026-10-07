import {COLUMNS,COHORTS,SEEDS,type Approach,type Side,type ApproachCase} from './approach-contract.js';
import {HASH} from './contracts.js';

export const CELLS = ['fixed-intact','fixed-outage','scheduled-intact','scheduled-outage'] as const;
export const LABELS = ['Fixed · intact','Fixed · outages','Scheduled · intact','Scheduled · outages'];
export const COLORS = ['#70baff','#eeac67','#68e2bc','#c19bff'];
export type Window = {start:number;end:number};
export type Selection = Window & {id:string;time:number};
export type Quartet = {id:string;cohort:string;seed:number;flights:Side[];entries:ApproachCase[]};
export const METHOD = {
  version:1,mass_kg:1,dt_s:.005,radial_epsilon_m:1e-9,
  integration:'Preceding force dot observed displacement; preceding control over each [start,end) interval.',
  interaction:'(scheduled outage - scheduled intact) - (fixed outage - fixed intact)',
  limits:'Descriptive horizontal translation only. Residual is not measured friction; demand is not energy. No causal or population inference. Original gates are unchanged.',
};
const check=(v:unknown)=>{if(!v)throw Error('Invalid landing response analysis');};
const finite=(n:unknown):n is number=>typeof n==='number'&&Number.isFinite(n);
const eq=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
const tick=(t:number)=>Math.round((t-34)/.005);
const grid=(t:number)=>finite(t)&&t>=34&&t<=50&&Math.abs(t-(34+tick(t)*.005))<1e-8;
export const GROUPS=COHORTS.flatMap((cohort,i)=>SEEDS[i].map(seed=>({id:`${cohort}-s${seed}`,cohort,seed})));
export function validateWindow(w:Window){check(grid(w.start)&&grid(w.end)&&w.end>w.start);return w;}

// Inputs must first pass validateApproach against their hash-bound index entries.
export function quartet(intact:Approach,outage:Approach,entries:ApproachCase[]):Quartet{
  check(intact.cohort===outage.cohort&&intact.seed===outage.seed&&intact.profile==='sample-hold'&&outage.profile==='hold-dropout-2000ms');
  check(entries.length===2&&entries[0].id===intact.id&&entries[1].id===outage.id);
  const flights=[intact.baseline,outage.baseline,intact.candidate,outage.candidate];
  for(const flight of flights)for(const key of ['controller_binary_sha256','lock_sha256','versions'])check(eq(flight.provenance[key],flights[0].provenance[key]));
  for(const [a,b] of [[0,1],[2,3]])for(const key of ['source_commit','source_tree_sha256'])check(eq(flights[a].provenance[key],flights[b].provenance[key]));
  return {id:`${intact.cohort}-s${intact.seed}`,cohort:intact.cohort,seed:intact.seed,flights,entries};
}
export function commonEnd(q:Quartet){return Math.min(...q.flights.map(f=>f.rows.at(-1)?.[0]??34));}
export function preset(q:Quartet,kind:'full'|'airborne'|'armed'|'disarmed'|'gust'):Window|null{
  const end=commonEnd(q);let start=34,stop=end;
  if(kind==='gust'){start=40;stop=42;}
  if(kind==='airborne'||kind==='armed'){
    const times=q.flights.map(f=>kind==='airborne'?f.touchdown_s:f.landed_s);
    if(times.some(t=>t===null))return null;
    stop=Math.min(end,Number((Math.min(...times as number[])-.005).toFixed(3)));
  }
  if(kind==='disarmed'){
    if(q.flights.some(f=>f.landed_s===null))return null;
    start=Math.max(...q.flights.map(f=>f.landed_s!));
  }
  return start<stop&&stop<=end?{start,end:stop}:null;
}
export function radial(r:number[]){
  const x=r[1]-r[9],y=r[2]-r[10],distance=Math.hypot(x,y);
  if(distance<METHOD.radial_epsilon_m)return {distance,closing:null,radial_error:null,tangential_error:null};
  const nx=x/distance,ny=y/distance,ex=r[5]-r[1],ey=r[6]-r[2];
  return {distance,closing:-((r[3]-r[11])*nx+(r[4]-r[12])*ny),radial_error:ex*nx+ey*ny,tangential_error:-ex*ny+ey*nx};
}
export function interval(a:number[],b:number[]){
  const dt=b[0]-a[0];check(Math.abs(dt-.005)<1e-8);
  const dx=b[1]-a[1],dy=b[2]-a[2],ax=(b[3]-a[3])/dt,ay=(b[4]-a[4])/dt;
  const wind=a[23]*dx+a[24]*dy,thrust=a[25]*dx+a[26]*dy;
  const kinetic=.5*(b[3]**2+b[4]**2-a[3]**2-a[4]**2);
  const phase:'disarmed'|'contact'|'airborne'=a[30]?'disarmed':a[27]>.1||b[27]>.1?'contact':'airborne';
  return {dt,wind,thrust,kinetic,residual:kinetic-wind-thrust,ax,ay,
    demand_error:Math.hypot(ax-a[20],ay-a[21]),
    force_residual:Math.hypot(ax-a[23]-a[25],ay-a[24]-a[26]),phase};
}
export type Summary = {
  complete:boolean;states:number;intervals:number;duration_s:number|null;
  rmse_m:number|null;demand_rms_m_s2:number|null;peak_error_m:number|null;
  wind_work_j:number|null;thrust_work_j:number|null;kinetic_change_j:number|null;residual_j:number|null;
  demand_error_rms_m_s2:number|null;force_residual_rms_m_s2:number|null;
  airborne_s:number|null;contact_s:number|null;disarmed_s:number|null;
};
export function summarize(side:Side,w:Window):Summary{
  validateWindow(w);const a=tick(w.start),b=tick(w.end),rows=side.rows.slice(a,b+1);
  const complete=rows.length===b-a+1;
  const missing:Summary={complete:false,states:rows.length,intervals:Math.max(0,rows.length-1),duration_s:null,rmse_m:null,demand_rms_m_s2:null,peak_error_m:null,wind_work_j:null,thrust_work_j:null,kinetic_change_j:null,residual_j:null,demand_error_rms_m_s2:null,force_residual_rms_m_s2:null,airborne_s:null,contact_s:null,disarmed_s:null};
  if(!complete)return missing;
  let squaredError=0,squaredDemand=0,wind=0,thrust=0,de=0,fr=0;
  const phase={airborne:0,contact:0,disarmed:0};
  for(let i=0;i<rows.length-1;i++){
    const r=rows[i],n=interval(r,rows[i+1]);
    squaredError+=r[31]**2*n.dt;squaredDemand+=(r[20]**2+r[21]**2)*n.dt;
    wind+=n.wind;thrust+=n.thrust;de+=n.demand_error**2*n.dt;fr+=n.force_residual**2*n.dt;phase[n.phase]+=n.dt;
  }
  const first=rows[0],last=rows.at(-1)!,duration=w.end-w.start;
  const kinetic=.5*(last[3]**2+last[4]**2-first[3]**2-first[4]**2);
  return {complete:true,states:rows.length,intervals:rows.length-1,duration_s:duration,
    rmse_m:Math.sqrt(squaredError/duration),demand_rms_m_s2:Math.sqrt(squaredDemand/duration),peak_error_m:Math.max(...rows.map(r=>r[31])),
    wind_work_j:wind,thrust_work_j:thrust,kinetic_change_j:kinetic,residual_j:kinetic-wind-thrust,
    demand_error_rms_m_s2:Math.sqrt(de/duration),force_residual_rms_m_s2:Math.sqrt(fr/duration),airborne_s:phase.airborne,contact_s:phase.contact,disarmed_s:phase.disarmed};
}
export function contrasts(values:(number|null)[]){
  check(values.length===4&&values.every(v=>v===null||finite(v)));
  if(values.some(v=>v===null))return {fixed:null,scheduled:null,interaction:null};
  const v=values as number[],fixed=v[1]-v[0],scheduled=v[3]-v[2];
  return {fixed,scheduled,interaction:scheduled-fixed};
}
export function analyze(q:Quartet,w:Window){
  const cells=q.flights.map(s=>summarize(s,w));
  return {window:{start:w.start,end:w.end},cells,rmse:contrasts(cells.map(s=>s.rmse_m)),demand:contrasts(cells.map(s=>s.demand_rms_m_s2))};
}
export function responseCurves(q:Quartet,w:Window){
  validateWindow(w);if(q.flights.some(f=>!summarize(f,w).complete))return [];
  return q.flights[0].rows.slice(tick(w.start),tick(w.end)+1).map((r,i)=>{
    const v=q.flights.map(f=>f.rows[tick(w.start)+i][31]),c=contrasts(v);
    return [r[0],c.fixed!,c.scheduled!,c.interaction!];
  });
}
export function energyCurve(side:Side,w:Window){
  if(!summarize(side,w).complete)return [];
  const rows=side.rows.slice(tick(w.start),tick(w.end)+1);let wind=0,thrust=0;
  const initial=.5*(rows[0][3]**2+rows[0][4]**2);
  return rows.map((r,i)=>{if(i){const x=interval(rows[i-1],r);wind+=x.wind;thrust+=x.thrust;}
    const k=.5*(r[3]**2+r[4]**2)-initial;return [r[0],wind,thrust,k,k-wind-thrust];});
}
export function accelerationCurve(side:Side,w:Window){
  if(!summarize(side,w).complete)return [];
  const rows=side.rows.slice(tick(w.start),tick(w.end)+1);
  return rows.slice(0,-1).map((r,i)=>{const x=interval(r,rows[i+1]);return [r[0],x.ax,x.ay,r[20],r[21],x.demand_error,x.force_residual];});
}
export function parseSelection(hash:string,digest:string):Selection|null{
  if(!HASH.test(digest)||hash.length>240)return null;const p=new URLSearchParams(hash.replace(/^#/,''));
  if([...p.keys()].sort().join()!=='end,index,seed,start,t'||p.get('index')!==digest||!GROUPS.some(g=>g.id===p.get('seed')))return null;
  const start=Number(p.get('start')),end=Number(p.get('end')),time=Number(p.get('t'));
  if(!grid(start)||!grid(end)||end<=start||!grid(time)||time<start||time>end)return null;
  return {id:p.get('seed')!,start,end,time};
}
export function selectionHash(s:Selection,digest:string){
  check(HASH.test(digest)&&GROUPS.some(g=>g.id===s.id));validateWindow(s);check(grid(s.time)&&s.time>=s.start&&s.time<=s.end);
  return '#'+new URLSearchParams({seed:s.id,index:digest,start:s.start.toFixed(3),end:s.end.toFixed(3),t:s.time.toFixed(3)});
}
export function review(q:Quartet,s:Selection,digest:string){
  check(q.id===s.id);selectionHash(s,digest);
  return {schema_version:1,kind:'landing_response_review',index_sha256:digest,selection:s,method:METHOD,
    entries:q.entries,analysis:analyze(q,s),columns:COLUMNS,
    flights:q.flights.map((f,i)=>({cell:CELLS[i],status:f.status,failure_reason:f.failure_reason,gates:f.gates,outage:f.outage,provenance:f.provenance,
      rows:f.rows.slice(tick(s.start),tick(s.end)+1)}))};
}
export function windowCsv(q:Quartet,w:Window,digest:string){
  validateWindow(w);check(HASH.test(digest));
  const lines=[['index_sha256','seed_group','cell','window_start_s','window_end_s','window_complete',...COLUMNS,'closing_m_s','radial_feedback_error_m','tangential_feedback_error_m','next_time_s','wind_interval_work_j','thrust_interval_work_j','kinetic_interval_change_j','residual_interval_j','measured_ax_m_s2','measured_ay_m_s2','demand_error_m_s2','force_residual_m_s2'].join(',')];
  q.flights.forEach((f,cell)=>{
    const rows=f.rows.slice(tick(w.start),tick(w.end)+1);
    rows.forEach((r,i)=>{const p=radial(r),n=i<rows.length-1?interval(r,rows[i+1]):null;
      lines.push([digest,q.id,CELLS[cell],w.start,w.end,Number(rows.length===tick(w.end)-tick(w.start)+1),...r,p.closing??'',p.radial_error??'',p.tangential_error??'',...(n?[rows[i+1][0],n.wind,n.thrust,n.kinetic,n.residual,n.ax,n.ay,n.demand_error,n.force_residual]:Array(9).fill(''))].join(','));});
  });return lines.join('\n')+'\n';
}
