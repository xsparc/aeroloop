import {lazy,Suspense,useCallback,useEffect,useRef,useState} from "react";
import {sampleAt,recordedSampleAt} from "./contracts.js";
import {evidenceBase,readVerified} from "./load.js";
import {outageActive,outageWindows} from "./observation-contract.js";
import {LABELS,OUTAGE_PROFILES,validateDemoIndex,validatePair,type DemoIndex,type Pair,type DemoSample} from "./outage-contract.js";
import "./outage.css";
const Scene=lazy(()=>import("./scene.js"));
const distance=(a:number[],b:number[])=>Math.hypot(...a.map((v,i)=>v-b[i]));
export function OutageDemo({baseUrl,indexSha256}:{baseUrl:string;indexSha256:string}) {
  const [index,setIndex]=useState<DemoIndex|null>(null),[pair,setPair]=useState<Pair|null>(null);
  const [selection,setSelection]=useState(12),[error,setError]=useState("");
  const [time,setTime]=useState(0),[playing,setPlaying]=useState(false),[speed,setSpeed]=useState(1);
  const [show3d,setShow3d]=useState(false),[failed3d,setFailed3d]=useState(false);
  const [visible,setVisible]=useState(!document.hidden),[onscreen,setOnscreen]=useState(true),[reduced,setReduced]=useState(false);
  const [reportUrl,setReportUrl]=useState("");
  const host=useRef<HTMLDivElement>(null),fail=useCallback(()=>setFailed3d(true),[]);
  useEffect(()=>{
    const controller=new AbortController();setIndex(null);setError("");setReportUrl("");let blob="";
    void (async()=>{
      const base=evidenceBase(baseUrl,location.origin);
      const next=validateDemoIndex(await readVerified(new URL("index.json",base),indexSha256,controller.signal,16384));
      const report=await readVerified(new URL("study.json",base),next.study_sha256,controller.signal,1024*1024);
      if(controller.signal.aborted)return;
      blob=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:"application/json"}));setReportUrl(blob);setIndex(next);
    })().catch(()=>{if(!controller.signal.aborted)setError("Demo evidence unavailable or invalid. Prepare a verified export and retry.");});
    return()=>{controller.abort();if(blob)URL.revokeObjectURL(blob);};
  },[baseUrl,indexSha256]);
  useEffect(()=>{
    setPair(null);setPlaying(false);setTime(0);setError("");if(!index)return;
    const controller=new AbortController(),entry=index.cases[selection];
    void readVerified(new URL(entry.file,evidenceBase(baseUrl,location.origin)),entry.sha256,controller.signal,4*1024*1024)
      .then(value=>{const next=validatePair(value,entry);if(!controller.signal.aborted)setPair(next);})
      .catch(()=>{if(!controller.signal.aborted)setError("Comparison failed its integrity checks. No unverified flight is displayed.");});
    return()=>controller.abort();
  },[index,selection,baseUrl]);
  useEffect(()=>{
    const media=matchMedia("(prefers-reduced-motion: reduce)");setReduced(media.matches);
    const motion=()=>{setReduced(media.matches);setPlaying(false);};
    const visibility=()=>{setVisible(!document.hidden);if(document.hidden)setPlaying(false);};
    const observer=new IntersectionObserver(entries=>{const shown=entries.some(e=>e.isIntersecting);setOnscreen(shown);if(!shown)setPlaying(false);});
    if(host.current)observer.observe(host.current);
    media.addEventListener("change",motion);document.addEventListener("visibilitychange",visibility);
    return()=>{observer.disconnect();media.removeEventListener("change",motion);document.removeEventListener("visibilitychange",visibility);};
  },[!!pair]);
  const end=pair?Math.max(pair.baseline.samples.at(-1)!.time_s,pair.candidate.samples.at(-1)!.time_s):50;
  useEffect(()=>{
    if(!playing||!visible||!onscreen||!pair)return;let id=0,previous=performance.now();
    const tick=(now:number)=>{const dt=Math.min(.1,(now-previous)/1000);previous=now;setTime(t=>Math.min(end,t+dt*speed));id=requestAnimationFrame(tick);};
    id=requestAnimationFrame(tick);return()=>cancelAnimationFrame(id);
  },[playing,visible,onscreen,pair,speed,end]);
  useEffect(()=>{if(time>=end)setPlaying(false);},[time,end]);
  const seek=(t:number)=>{setPlaying(false);setTime(Math.min(end,t));};
  const profile=OUTAGE_PROFILES[Math.floor(selection/3)],seed=selection%3,windows=outageWindows(profile);
  return <main className="outage-demo">
    <header><p className="eyebrow">AEROLOOP / PHYSICS LAB</p><h1>Flying through missing feedback</h1>
      <p>Recorded Isaac PhysX flights · turbulent waypoints and landing · 200 Hz control</p>
      <p>The left controller holds its last capture. The right predicts motion from captured state, known rotor thrust and ideal attitude. All acceptance thresholds stay unchanged.</p>
    </header>
    <section className="controls" aria-label="Demo controls">
      <label>Capture outage <select value={Math.floor(selection/3)} onChange={e=>setSelection(Number(e.target.value)*3+seed)}>{LABELS.map((label,i)=><option key={label} value={i}>{label}</option>)}</select></label>
      <label>Seed <select value={seed} onChange={e=>setSelection(Math.floor(selection/3)*3+Number(e.target.value))}>{[0,1,2].map(s=><option key={s}>{s}</option>)}</select></label>
      <button disabled={!pair} onClick={()=>{if(time>=end)setTime(0);setPlaying(v=>!v);}}>{playing?"Pause":"Play"}</button>
      <label>Speed <select value={speed} onChange={e=>setSpeed(Number(e.target.value))}>{[.25,.5,1,2].map(s=><option key={s} value={s}>{s}×</option>)}</select></label>
      <button disabled={!pair} onClick={()=>setShow3d(v=>!v)}>{show3d?"Hide 3D":"Enable paired 3D"}</button>
      <label className="timeline">Simulation time <output>{time.toFixed(3)} s</output><input aria-label="Simulation time" type="range" min={0} max={end} step={.005} value={time} disabled={!pair} onChange={e=>seek(Number(e.target.value))}/></label>
      <div className="chapters">{[[0,"Start"],[18,"First outage"],[windows[0]?.[1]??20,"Capture resumes"],[40,"Landing outage"],[48,"Settled support"]].map(([t,label])=><button key={label} disabled={!pair} onClick={()=>seek(Number(t))}>{label}</button>)}</div>
      <p>{windows.length?`Missing captures: ${windows.map(([a,b])=>`${a}–${b} s`).join(" and ")}.`:"Uninterrupted 50 Hz captures."} {outageActive(time,profile)?"OUTAGE ACTIVE":"Captures available"}</p>
      {reduced&&<p>Reduced motion: playback starts only when you press Play. Scrub or use chapters to inspect still frames.</p>}
    </section>
    {error?<p role="alert">{error}</p>:!pair?<p role="status">Loading verified comparison…</p>:<>
      {index&&<section className="controls" aria-label="Full-rate study outcomes"><h2>{LABELS[Math.floor(selection/3)]} · all three seeds</h2>
        <table><thead><tr><th>Controller</th><th>Missions</th><th>Pairs against no outage</th><th>Recovery windows</th><th>All stress gates</th></tr></thead><tbody>{(["baseline","candidate"] as const).map((name,i)=>{
          const row=index.outcomes[Math.floor(selection/3)][name];return <tr key={name}><th>{i?"Predicted feedback":"Held feedback"}</th><td>{row.mission_passes}/3</td><td>{row.pair_count?`${row.pair_passes}/${row.pair_count}`:"Reference"}</td><td>{row.recovery_count?`${row.recovery_passes}/${row.recovery_count}`:"No outage"}</td><td>{row.accepted?"Accepted":"Not accepted"}</td></tr>;
        })}</tbody></table><p>Recovery requires a final uninterrupted interval within 50 mm of the same controller's no-outage flight, lasting at least one second and starting within five seconds of capture resumption. Mission success alone does not pass these checks.</p>
      </section>}
      <div className="paired" ref={host}>{(["baseline","candidate"] as const).map((name,i)=>{
        const side=pair[name],held=recordedSampleAt(side.samples,time) as DemoSample,pose=sampleAt(side.samples,time);
        const points=side.samples.map(s=>`${150+s.position_m[0]*70},${220-s.position_m[1]*70}`).join(" ");
        return <section key={name} className="flight-card" aria-label={i?"Predicted feedback flight":"Held feedback flight"}>
          <h2>{i?"Predicted feedback":"Held feedback"}</h2><p className={`outcome ${side.status}`}>Full-rate mission: <strong>{side.status.toUpperCase()}</strong> · {side.gates.filter(g=>g.status==="passed").length}/{side.gates.length} gates</p>
          {side.samples.at(-1)!.time_s<50&&<p role="alert">Incomplete recording ends at {side.samples.at(-1)!.time_s} s. The last pose is held.</p>}
          {show3d&&!failed3d?<Suspense fallback={<p>Loading 3D…</p>}><Scene sample={pose} samples={side.samples} rotorFlight visible={visible&&onscreen} onFailure={fail}/></Suspense>:<svg viewBox="0 0 400 280" role="img" aria-label={`${name} recorded horizontal trajectory`}><polyline points={points} fill="none" stroke={i?"#007e80":"#ad592e"} strokeWidth="2"/><circle cx={150+pose.position_m[0]*70} cy={220-pose.position_m[1]*70} r="6" fill="#101e30"/></svg>}
          {failed3d&&<p>3D is unavailable. The recorded trajectory and numeric evidence remain available.</p>}
          <dl><div><dt>Flight phase</dt><dd>{held.mission_phase?.replaceAll("_"," ")}</dd></div>
            <div><dt>Raw capture age</dt><dd>{(held.observation.age_s*1000).toFixed(0)} ms</dd></div>
            <div><dt>Feedback mode</dt><dd>{held.feedback.mode}</dd></div>
            <div><dt>Feedback position error</dt><dd>{distance(held.position_m,held.feedback.position_m).toFixed(3)} m</dd></div>
            <div><dt>Tracking error</dt><dd>{distance(held.position_m,held.target_m).toFixed(3)} m</dd></div>
            <div><dt>Recorded state time</dt><dd>{held.time_s.toFixed(3)} s</dd></div></dl>
          <details><summary>Inspect all acceptance gates</summary><table><thead><tr><th>Gate</th><th>Value / limit</th><th>Result</th></tr></thead><tbody>{side.gates.map(g=><tr key={g.id}><th>{g.label}</th><td>{g.value===null?"—":g.value.toFixed(3)} / {g.operator} {g.limit.toFixed(3)} {g.unit}</td><td>{g.status.replaceAll("_"," ")}</td></tr>)}</tbody></table></details>
        </section>;
      })}</div>
      <p>Display poses interpolate between recorded frames. Capture age, feedback and numeric errors use the preceding recorded timestamp. Full-rate gates use every physics/control sample.</p>
    </>}
    <footer><p>Research comparison on three regression seeds. Synthetic outages, ideal attitude and simplified wind/contact; predictor expires after 2.1 s. No hardware-flight claim. The independent yaw-refinement finding remains open.</p>
      {index&&<><p>{index.display}</p><p>Baseline source <code>{index.baseline_source.slice(0,12)}</code> · candidate source <code>{index.candidate_source.slice(0,12)}</code></p></>}
      {reportUrl&&<a href={reportUrl} download="predictive-feedback-study.json">Download verified full-rate study</a>}
    </footer>
  </main>;
}
