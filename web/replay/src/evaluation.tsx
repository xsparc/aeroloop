import {Component, lazy, Suspense, useCallback, useEffect, useRef, useState, type ReactNode} from "react";
import {sampleAt, tiltDegrees, type Recording, type Sample} from "./contracts.js";
import {evidenceBase} from "./load.js";
import {loadEvaluation, loadEvaluationRecording, type Case, type Evaluation, type Gate} from "./evaluation-contract.js";
import "./evaluation.css";

const Scene=lazy(()=>import("./scene.js"));
const fmt=(n:number|null|undefined,d=3)=>n==null?"Not measured":n.toFixed(d);
const frequency=(c:Case)=>Math.round(1/c.physics_dt_s);
class RenderBoundary extends Component<{children:ReactNode; onFailure:()=>void},{failed:boolean}> {
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  componentDidCatch(){this.props.onFailure();}
  render(){return this.state.failed?<p>3D unavailable. Use the recorded trajectory and timeline.</p>:this.props.children;}
}

function PathView({samples,current}:{samples:Sample[];current:Sample}) {
  const point=(v:number[])=>`${70+v[0]*95},${210-v[1]*95}`;
  return <svg viewBox="0 0 320 270" role="img" aria-label="Recorded trajectory, top view, east right and north up">
    <path d="M20 210 H290 M70 250 V20" stroke="#486477" fill="none"/>
    <polyline points={samples.map(s=>point(s.position_m)).join(" ")} fill="none" stroke="#62dcd1" strokeWidth="2"/>
    <circle cx={70+current.position_m[0]*95} cy={210-current.position_m[1]*95} r="6" fill="#62dcd1"/>
    <circle cx={70+current.target_m[0]*95} cy={210-current.target_m[1]*95} r="8" fill="none" stroke="#f4cd78" strokeWidth="2"/>
    <text x="276" y="228" fill="#a9c1cf">E</text><text x="50" y="25" fill="#a9c1cf">N</text>
  </svg>;
}
function ErrorPlot({recordings,time}:{recordings:Recording[];time:number}) {
  const end=Math.max(...recordings.map(r=>r.samples.at(-1)!.time_s));
  const errors=recordings.map(r=>r.samples.map(s=>({t:s.time_s,e:Math.hypot(...s.position_m.map((v,i)=>v-s.target_m[i]))})));
  const top=Math.max(.5,...errors.flatMap(a=>a.map(s=>s.e)));
  return <figure className="ev-plot"><figcaption>Position error · display samples (m) <span>200 Hz / candidate</span></figcaption>
    <svg viewBox="0 0 900 130" role="img" aria-label="Paired position error over recorded simulation time">
      <path d="M42 8 V102 H880" stroke="#486477" fill="none"/>
      {[0,.5,1].map(f=><g key={f}><text x="0" y={103-f*88} fill="#a9c1cf" fontSize="12">{(f*top).toFixed(2)}</text>
        <path d={`M42 ${102-f*88} H880`} stroke="#21394b"/></g>)}
      {errors.map((series,i)=><polyline key={i} points={series.map(s=>`${42+838*s.t/end},${102-88*s.e/top}`).join(" ")}
        fill="none" stroke={i?"#f4cd78":"#62dcd1"} strokeDasharray={i?"5 3":undefined} strokeWidth="2"/>)}
      <path d={`M${42+838*time/end} 8 V102`} stroke="#fff"/>
      {[0,10,20,30,40,50].filter(t=>t<=end).map(t=><text key={t} x={42+838*t/end} y="122" fill="#a9c1cf" fontSize="12">{t}s</text>)}
    </svg>
  </figure>;
}
const operator:Record<Gate["operator"],string>={eq:"=",le:"≤",lt:"<",ge:"≥",abs_le:"|value| ≤"};
function Pair({base,data,left,right}:{base:URL;data:Evaluation;left:Case;right:Case}) {
  const [recordings,setRecordings]=useState<Recording[]|null>(null), [error,setError]=useState(false);
  const [time,setTime]=useState(0),[playing,setPlaying]=useState(false),[speed,setSpeed]=useState(1);
  const [three,setThree]=useState(false),[lost,setLost]=useState(false),[visible,setVisible]=useState(true);
  const [reduced,setReduced]=useState(()=>matchMedia("(prefers-reduced-motion: reduce)").matches);
  const stage=useRef<HTMLDivElement>(null);
  const onFailure=useCallback(()=>{setLost(true);setThree(false);},[]);
  useEffect(()=>{
    const request=new AbortController();
    Promise.all([left,right].map(c=>loadEvaluationRecording(base,data,c,request.signal)))
      .then(r=>{if(!request.signal.aborted)setRecordings(r);})
      .catch(()=>{if(!request.signal.aborted)setError(true);});
    return ()=>request.abort();
  },[base,data,left,right]);
  useEffect(()=>{
    const media=matchMedia("(prefers-reduced-motion: reduce)");
    const motion=()=>{setReduced(media.matches);if(media.matches)setPlaying(false);};
    const visibility=()=>{if(document.hidden)setPlaying(false);};
    media.addEventListener("change",motion);document.addEventListener("visibilitychange",visibility);
    return ()=>{media.removeEventListener("change",motion);document.removeEventListener("visibilitychange",visibility);};
  },[]);
  useEffect(()=>{
    if(!stage.current)return;
    const observer=new IntersectionObserver(([entry])=>{setVisible(entry.isIntersecting);if(!entry.isIntersecting)setPlaying(false);});
    observer.observe(stage.current);return ()=>observer.disconnect();
  },[recordings]);
  const end=recordings?Math.min(...recordings.map(r=>r.samples.at(-1)!.time_s)):0;
  useEffect(()=>{
    if(!playing||!visible||reduced||document.hidden)return;
    let id=0,previous=performance.now();
    const tick=(now:number)=>{
      const delta=(now-previous)/1000*speed;previous=now;
      setTime(t=>Math.min(end,t+delta));id=requestAnimationFrame(tick);
    };
    id=requestAnimationFrame(tick);return ()=>cancelAnimationFrame(id);
  },[playing,visible,reduced,speed,end]);
  useEffect(()=>{if(playing&&time>=end)setPlaying(false);},[time,end,playing]);
  if(error)return <p role="alert">The selected recordings could not be verified. Playback is unavailable.</p>;
  if(!recordings)return <p role="status">Verifying selected recordings…</p>;
  const current=recordings.map(r=>sampleAt(r.samples,time));
  const pair=data.study.comparisons.find(c=>c.seed===right.seed&&c.physics_dt_s===right.physics_dt_s)!;
  const seek=(t:number)=>{setPlaying(false);setTime(Math.max(0,Math.min(end,t)));};
  const chapters:[string,number|null|undefined][]=[ ["Ground support",0],["Takeoff",2],["North waypoint",15],
    ["East waypoint",23],["Home waypoint",31],["Landing gust",40],
    ["Baseline touchdown",left.metrics.mission?.touchdown_time_s],
    ["Candidate touchdown",right.metrics.mission?.touchdown_time_s],["Settled support",48]];
  return <>
    <div className="ev-pair" ref={stage}>
      {recordings.map((r,i)=><section key={r.entry.run_id} aria-label={i?"Candidate recording":"Baseline recording"}>
        <div className="ev-panel-title"><h3>{i?frequency(right):200} Hz <small>{i?"candidate":"baseline"}</small></h3>
          <span className={`ev-status ${r.entry.status}`}>{r.entry.status}</span></div>
        <div className="ev-stage">
          {three&&!lost?<RenderBoundary onFailure={onFailure}><Suspense fallback={<p>Loading 3D…</p>}>
            <Scene sample={current[i]} samples={r.samples} rotorFlight visible={visible} onFailure={onFailure}/>
          </Suspense></RenderBoundary>:<PathView samples={r.samples} current={current[i]}/>}
        </div>
        <div className="ev-readouts"><span>Phase <strong>{current[i].mission_phase}</strong></span>
          <span>Height <strong>{fmt(current[i].position_m[2])} m</strong></span>
          <span>Tilt <strong>{fmt(tiltDegrees(current[i].quaternion_wxyz),1)}°</strong></span>
          <span>Wind <strong>{fmt(Math.hypot(...current[i].wind_velocity_m_s!),1)} m/s</strong></span>
          <span>Support <strong>{fmt(current[i].contact_normal_force_n![2],2)} N</strong></span></div>
      </section>)}
    </div>
    <div className="ev-transport">
      <button disabled={reduced} onClick={()=>{if(time>=end)setTime(0);setPlaying(p=>!p);}}>{playing?"Pause":"Play"}</button>
      <label className="ev-timeline">Shared simulation time <output>{time.toFixed(3)} s</output>
        <input type="range" min="0" max={end} step="0.005" value={time} onChange={e=>seek(+e.target.value)}/></label>
      <label>Speed <select value={speed} onChange={e=>setSpeed(+e.target.value)}>{[.5,1,2].map(n=><option key={n} value={n}>{n}×</option>)}</select></label>
      <button disabled={lost} onClick={()=>setThree(v=>!v)}>{three?"Hide 3D":"Enable paired 3D"}</button>
    </div>
    <p className="ev-note">{reduced?"Reduced motion: use the timeline or chapter buttons. ":""}{lost?"3D unavailable; recorded trajectory remains available. ":""}
      Gold: target / candidate curve. Teal: recorded route / baseline curve. 3D arrows show wind, force and support; drag to orbit, scroll to zoom.</p>
    <nav className="ev-chapters" aria-label="Mission chapters">{chapters.map(([label,t])=><button key={label} disabled={t==null||t>end}
      onClick={()=>t!=null&&seek(t)}>{label}<small>{t==null?"not measured":`${t.toFixed(3)} s`}</small></button>)}</nav>
    {end<50&&<p role="alert">Incomplete recording: synchronized playback ends at {end.toFixed(3)} s. Full mission comparison is unavailable.</p>}
    <ErrorPlot recordings={recordings} time={time}/>
    <section><h2>Full-rate pair evaluation <span className={`ev-status ${pair.passed?"passed":"failed"}`}>{pair.passed?"passed":"failed"}</span></h2>
      {pair.reason?<p>Incomplete pair; no sensitivity metrics are claimed.</p>:<div className="ev-table-scroll"><table><thead><tr><th>Comparison metric</th><th>Measured</th><th>Acceptance limit</th></tr></thead>
        <tbody>{[
          ["Peak position difference",`${fmt((pair.peak_position_difference_m??0)*1000)} mm`,"≤ 150 mm"],
          ["Difference RMSE",`${fmt((pair.position_difference_rmse_m??0)*1000)} mm`,"Diagnostic"],
          ["Peak attitude difference",`${fmt((pair.peak_attitude_difference_rad??0)*1000)} mrad`,"Diagnostic"],
          ["Position RMSE change",`${fmt((pair.position_rmse_change_m??0)*1000)} mm`,"≤ 50 mm"],
          ["Landed-time change",`${fmt(pair.landed_time_change_s)} s`,"≤ 0.500 s"],
        ].map(([label,value,limit])=><tr key={label}><th>{label}</th><td>{value}</td><td>{limit}</td></tr>)}</tbody></table></div>}
    </section>
    <section><h2>Mission acceptance gates</h2><p>Measured at 200 Hz control cadence, independently of the display. Every gate must pass.</p>
      <div className="ev-table-scroll"><table><thead><tr><th>Gate</th><th>Limit</th><th>200 Hz · value / result</th><th>{frequency(right)} Hz · value / result</th></tr></thead>
        <tbody>{left.gates.map(g=><tr key={g.id}><th>{g.label}</th><td>{operator[g.operator]} {g.limit} {g.unit}</td>
          {[g,right.gates.find(r=>r.id===g.id)!].map((v,i)=><td key={i}>{fmt(v.value,v.unit==="count"?0:6)} {v.value==null?"":v.unit}
            <span className={`ev-status ${v.status}`}>{v.status.replace("_"," ")}</span></td>)}</tr>)}</tbody></table></div>
      {[left,right].filter(c=>c.failure_reason).map(c=><p key={c.run_id} className="ev-warning">{frequency(c)} Hz failure: {c.failure_reason}</p>)}
    </section>
    <details><summary>Selected recording provenance</summary>{[left,right].map(c=><div key={c.run_id}><h3>{frequency(c)} Hz · seed {c.seed}</h3>
      <p>Run <code>{c.run_id}</code></p><p>Full samples SHA-256 <code>{c.samples_sha256}</code></p><p>Configuration SHA-256 <code>{c.config_sha256}</code></p>
      <p>{c.metrics.samples.toLocaleString()} control samples; {fmt(c.timing.real_time_factor,2)}× measured wall speed; {fmt(c.timing.max_lag_s,2)} s maximum lag.</p>
    </div>)}</details>
  </>;
}

function Explorer({base,data}:{base:URL;data:Evaluation}) {
  const [seed,setSeed]=useState(0),[dt,setDt]=useState(.0025);
  const left=data.cases.find(c=>c.seed===seed&&c.physics_dt_s===.005)!;
  const right=data.cases.find(c=>c.seed===seed&&c.physics_dt_s===dt)!;
  const download=()=>{
    const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+"\n"],{type:"application/json"}));
    const a=document.createElement("a");a.href=url;a.download="flight-evaluation.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),0);
  };
  return <>
    <div className="ev-summary"><div><span>Mission acceptance</span><strong>{data.study.passed} / 9 passed</strong></div>
      <div><span>Timestep pairs</span><strong>{data.study.comparisons.filter(c=>c.passed).length} / 6 passed</strong></div>
      <div><span>Control samples</span><strong>{data.cases.reduce((n,c)=>n+c.metrics.samples,0).toLocaleString()}</strong></div>
      <div><span>Study result</span><strong className={data.study.accepted?"passed":"failed"}>{data.study.accepted?"Accepted":"Not accepted"}</strong></div></div>
    <p className="ev-warning">Independent yaw refinement remains unresolved. Mission acceptance and bounded timestep sensitivity do not establish numerical convergence.</p>
    <section aria-label="Study matrix"><h2>Seed × physics frequency</h2><p>Select a cell to inspect that seed. The 200 Hz column is the comparison baseline.</p>
      <div className="ev-table-scroll"><table className="ev-matrix"><thead><tr><th>Wind seed</th>{[200,400,800].map(hz=><th key={hz}>{hz} Hz</th>)}</tr></thead><tbody>
        {[0,1,2].map(s=><tr key={s}><th>{s}</th>{[.005,.0025,.00125].map(d=>{const c=data.cases.find(c=>c.seed===s&&c.physics_dt_s===d)!;
          return <td key={d}><button aria-label={`Seed ${s}, ${frequency(c)} Hz`} aria-pressed={s===seed&&(d===dt||d===.005)} onClick={()=>{setSeed(s);if(d!==.005)setDt(d);}}>
            <span className={`ev-status ${c.status}`}>{c.status}</span><span>{fmt(c.metrics.position_rmse_m)} m RMSE</span><small>{fmt(c.timing.real_time_factor,2)}× wall speed</small>
          </button></td>;})}</tr>)}
      </tbody></table></div>
    </section>
    <section className="ev-demo"><div className="ev-section-title"><h2>Guided flight comparison</h2><div className="ev-selectors">
      <label>Wind seed <select value={seed} onChange={e=>setSeed(+e.target.value)}>{[0,1,2].map(s=><option key={s}>{s}</option>)}</select></label>
      <label>Candidate physics <select value={dt} onChange={e=>setDt(+e.target.value)}><option value="0.0025">400 Hz</option><option value="0.00125">800 Hz</option></select></label>
    </div></div><Pair key={`${seed}/${dt}`} base={base} data={data} left={left} right={right}/></section>
    <section><h2>Evidence and limitations</h2><p>{data.display}. Recorded playback; the browser does not run the flight controller or simulator.</p>
      <p>Measured source <code>{data.study.source_commit}</code>. Re-evaluation preserves this historical source identity.</p>
      <ul>{data.study.limitations.map(v=><li key={v}>{v}</li>)}</ul>
      <button onClick={download}>Download evaluation JSON</button><p className="ev-note">Includes full-rate metrics, gates, comparisons and hashes; raw control samples remain in the original recordings.</p>
    </section>
  </>;
}
export function FlightEvaluation({baseUrl,indexSha256}:{baseUrl:string;indexSha256:string}) {
  const [state,setState]=useState<{base:URL;data:Evaluation}|null>(null),[error,setError]=useState(false);
  useEffect(()=>{
    const request=new AbortController();setState(null);setError(false);
    try {
      const base=evidenceBase(baseUrl,location.origin);
      loadEvaluation(base,indexSha256,request.signal).then(data=>{if(!request.signal.aborted)setState({base,data});})
        .catch(()=>{if(!request.signal.aborted)setError(true);});
    }catch{setError(true);}
    return ()=>request.abort();
  },[baseUrl,indexSha256]);
  return <main className="ev-app"><header><p className="ev-eyebrow">AEROLOOP / PHYSICS LAB</p><h1>Flight evaluation</h1>
    <p>Explore measured turbulent flight, acceptance gates and paired 3D recordings.</p><span className="ev-tag">Recorded PhysX study · research preview</span></header>
    {error?<p role="alert">Evaluation could not be verified. No results are shown.</p>:state?<Explorer {...state}/>:<p role="status">Verifying evaluation…</p>}
  </main>;
}
