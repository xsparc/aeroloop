import {lazy,Suspense,useCallback,useEffect,useRef,useState} from "react";
import {sampleAt,recordedSampleAt} from "./contracts.js";
import {evidenceBase,readVerified} from "./load.js";
import {outageActive,outageWindows} from "./observation-contract.js";
import {LABELS,OUTAGE_PROFILES,validateDemoIndex,validatePair,type DemoIndex,type Pair,type DemoSample} from "./outage-contract.js";
import {QUALITIES, QUALITY_LABELS} from "./axis-contract.js";
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
      blob=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:"application/json"}));setReportUrl(blob);setSelection(next.cases[0].quality?6:next.cases[0].fresh_axis?0:next.cohorts?9:12);setIndex(next);
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
  const quality=!!index?.cases[0].quality,axis=!!index?.cases[0].fresh_axis,guarded=!!index?.cohorts&&!axis&&!quality,entry=index?.cases[selection];
  const cohort=index?.cohorts?.find(c=>c.id===entry?.cohort);
  const profiles:readonly string[]=cohort?.profiles??OUTAGE_PROFILES,seeds=cohort?.seeds??[0,1,2];
  const profile=entry?.profile??"hold-dropout-2000ms",seed=entry?.seed??0,windows=outageWindows(profile);
  const title=LABELS[OUTAGE_PROFILES.indexOf(profile as typeof OUTAGE_PROFILES[number])];
  const select=(p:string,s:number,c=entry?.cohort,a=entry?.fresh_axis,q=entry?.quality)=>{const i=index?.cases.findIndex(e=>e.profile===p&&e.seed===s&&e.cohort===c&&e.fresh_axis===a&&e.quality===q);if(i!==undefined&&i>=0)setSelection(i);};
  const labels=quality?[QUALITY_LABELS[0],QUALITY_LABELS[QUALITIES.indexOf(entry?.quality??"noise-delay")]]:axis?["All channels interrupted",entry?.fresh_axis==="vertical"?"Fresh altitude":"Fresh horizontal"]:guarded?["Prediction only","Prediction + landing guard"]:["Held feedback","Predicted feedback"];
  const transitions=pair?.candidate.samples.find(s=>s.landing_guard?.resumed_at_s!==null&&s.landing_guard?.resumed_at_s!==undefined)?.landing_guard;
  const activation=pair?.candidate.samples.find(s=>s.landing_guard?.activated_at_s!==null&&s.landing_guard?.activated_at_s!==undefined)?.landing_guard?.activated_at_s;
  return <main className="outage-demo">
    <header><p className="eyebrow">AEROLOOP / PHYSICS LAB</p><h1>{quality?"How much feedback quality is enough?":axis?"Which feedback keeps landing stable?":guarded?"Landing after lost captures":"Flying through missing feedback"}</h1>
      <p>Recorded Isaac PhysX flights · turbulent waypoints and landing · 200 Hz control</p>
      <p>{quality?"Both flights retain a 50 Hz horizontal channel while main captures stop for two seconds. Compare ideal captures with fixed noise, 40 ms transport delay, or both. Noise is clipped Gaussian: 10 mm position and 20 mm/s velocity sigma. Controller gains and physics scoring stay unchanged.":axis?"Both flights use the same predictor and control gains. The right replaces selected position/velocity components with a noiseless 50 Hz synthetic channel while the main captures stop for two seconds. This isolates availability; it is not a real sensor or fused estimator.":guarded?"Both controllers predict motion between captures. The right pauses commanded descent after stale captures and waits for fresh horizontal stability before descending again. Scoring still uses the original mission targets and deadlines.":"The left controller holds its last capture. The right predicts motion from captured state, known rotor thrust and ideal attitude. All acceptance thresholds stay unchanged."}</p>
    </header>
    <section className="controls" aria-label="Demo controls">
      {index?.cohorts&&<label>Cohort <select value={entry?.cohort} onChange={e=>{const c=index.cohorts!.find(c=>c.id===e.target.value)!;select(c.profiles.includes(profile)?profile:c.profiles[0],c.seeds[0],c.id);}}>{index.cohorts.map(c=><option key={c.id} value={c.id}>{c.id==="unseen"?"Previously unseen seeds":c.id==="prior-validation"?"Previously tested validation seeds":"Regression seeds"}</option>)}</select></label>}
      {quality?<label>Channel quality <select value={entry?.quality} onChange={e=>select(profile,seed,undefined,undefined,e.target.value)}>{QUALITIES.slice(1).map((q,i)=><option key={q} value={q}>{QUALITY_LABELS[i+1]}</option>)}</select></label>:axis?<label>Fresh channel <select value={entry?.fresh_axis} onChange={e=>select(profile,seed,entry?.cohort,e.target.value)}><option value="vertical">Altitude</option><option value="horizontal">Horizontal</option></select></label>:<label>Capture outage <select value={profiles.indexOf(profile)} onChange={e=>select(profiles[Number(e.target.value)],seed)}>{profiles.map((p,i)=><option key={p} value={i}>{LABELS[OUTAGE_PROFILES.indexOf(p as typeof OUTAGE_PROFILES[number])]}</option>)}</select></label>}
      <label>Seed <select value={seed} onChange={e=>select(profile,Number(e.target.value))}>{seeds.map(s=><option key={s}>{s}</option>)}</select></label>
      <button disabled={!pair} onClick={()=>{if(time>=end)setTime(0);setPlaying(v=>!v);}}>{playing?"Pause":"Play"}</button>
      <label>Speed <select value={speed} onChange={e=>setSpeed(Number(e.target.value))}>{[.25,.5,1,2].map(s=><option key={s} value={s}>{s}×</option>)}</select></label>
      <button disabled={!pair} onClick={()=>setShow3d(v=>!v)}>{show3d?"Hide 3D":"Enable paired 3D"}</button>
      <label className="timeline">Simulation time <output>{time.toFixed(3)} s</output><input aria-label="Simulation time" type="range" min={0} max={end} step={.005} value={time} disabled={!pair} onChange={e=>seek(Number(e.target.value))}/></label>
      <div className="chapters">{[[0,"Start"],[18,"First outage"],[windows[0]?.[1]??20,"Capture resumes"],[40,"Landing outage"],[48,"Settled support"]].map(([t,label])=><button key={label} disabled={!pair} onClick={()=>seek(Number(t))}>{label}</button>)}</div>
      {guarded&&<div className="chapters"><button disabled={activation==null} onClick={()=>seek(activation!)}>Guard activates</button><button disabled={transitions?.resumed_at_s==null} onClick={()=>seek(transitions!.resumed_at_s!)}>Descent resumes</button><span>{activation==null?"No guard activation in this recording.":transitions?.resumed_at_s==null?"Descent did not resume in this recording.":`Guard ${(activation).toFixed(3)} s · descent ${transitions.resumed_at_s.toFixed(3)} s`}</span></div>}
      <p>{windows.length?`Missing captures: ${windows.map(([a,b])=>`${a}–${b} s`).join(" and ")}.`:"Uninterrupted 50 Hz captures."} {outageActive(time,profile)?"OUTAGE ACTIVE":"Captures available"}</p>
      {reduced&&<p>Reduced motion: playback starts only when you press Play. Scrub or use chapters to inspect still frames.</p>}
    </section>
    {error?<p role="alert">{error}</p>:!pair?<p role="status">Loading verified comparison…</p>:<>
      {index&&<section className="controls" aria-label="Full-rate study outcomes"><h2>{title} · {entry?.cohort??"all"} three seeds</h2>
        <table><thead><tr><th>Controller</th><th>Missions</th><th>Pairs against no outage</th><th>Recovery windows</th><th>All stress gates</th></tr></thead><tbody>{(["baseline","candidate"] as const).map((name,i)=>{
          const row=index.outcomes.find(o=>o.profile===profile&&o.cohort===entry?.cohort&&o.fresh_axis===entry?.fresh_axis&&o.quality===entry?.quality)![name];return <tr key={name}><th>{labels[i]}</th><td>{row.mission_passes}/3</td><td>{row.pair_count?`${row.pair_passes}/${row.pair_count}`:"Reference"}</td><td>{row.recovery_count?`${row.recovery_passes}/${row.recovery_count}`:"No outage"}</td><td>{row.accepted?"Accepted":"Not accepted"}</td></tr>;
        })}</tbody></table><p>Recovery requires a final uninterrupted interval within 50 mm of the same controller's no-outage flight, lasting at least one second and starting within five seconds of capture resumption. Mission success alone does not pass these checks.</p>
      </section>}
      <div className="paired" ref={host}>{(["baseline","candidate"] as const).map((name,i)=>{
        const side=pair[name],held=recordedSampleAt(side.samples,time) as DemoSample,pose=sampleAt(side.samples,time);
        const points=side.samples.map(s=>`${150+s.position_m[0]*70},${220-s.position_m[1]*70}`).join(" ");
        return <section key={name} className="flight-card" aria-label={`${labels[i]} flight`}>
          <h2>{labels[i]}</h2><p className={`outcome ${side.status}`}>Full-rate mission: <strong>{side.status.toUpperCase()}</strong> · {side.gates.filter(g=>g.status==="passed").length}/{side.gates.length} gates</p>
          {side.samples.at(-1)!.time_s<50&&<p role="alert">Incomplete recording ends at {side.samples.at(-1)!.time_s} s. The last pose is held.</p>}
          {show3d&&!failed3d?<Suspense fallback={<p>Loading 3D…</p>}><Scene sample={pose} samples={side.samples} rotorFlight visible={visible&&onscreen} onFailure={fail}/></Suspense>:<svg viewBox="0 0 400 280" role="img" aria-label={`${name} recorded horizontal trajectory`}><polyline points={points} fill="none" stroke={i?"#007e80":"#ad592e"} strokeWidth="2"/><circle cx={150+pose.position_m[0]*70} cy={220-pose.position_m[1]*70} r="6" fill="#101e30"/></svg>}
          {failed3d&&<p>3D is unavailable. The recorded trajectory and numeric evidence remain available.</p>}
          <dl><div><dt>Flight phase</dt><dd>{held.mission_phase?.replaceAll("_"," ")}</dd></div>
            <div><dt>Raw capture age</dt><dd>{(held.observation.age_s*1000).toFixed(0)} ms</dd></div>
            <div><dt>Feedback mode</dt><dd>{held.axis_feedback?.mode??held.feedback.mode}</dd></div>
            <div><dt>Feedback position error</dt><dd>{distance(held.position_m,(held.axis_feedback??held.feedback).position_m).toFixed(3)} m</dd></div>
            <div><dt>Tracking error</dt><dd>{distance(held.position_m,held.target_m).toFixed(3)} m</dd></div>
            <div><dt>Recorded state time</dt><dd>{held.time_s.toFixed(3)} s</dd></div>
            {(axis||quality)&&<><div><dt>{quality?"Horizontal channel age":"Fresh channel age"}</dt><dd>{held.axis_observation?`${(held.axis_observation.age_s*1000).toFixed(0)} ms`:"None"}</dd></div><div><dt>Applied horizontal error</dt><dd>{Math.hypot(...held.position_m.slice(0,2).map((v,i)=>v-(held.axis_feedback??held.feedback).position_m[i])).toFixed(3)} m</dd></div><div><dt>Applied altitude error</dt><dd>{Math.abs(held.position_m[2]-(held.axis_feedback??held.feedback).position_m[2]).toFixed(3)} m</dd></div></>}
            {guarded&&<><div><dt>Scheduled altitude</dt><dd>{held.target_m[2].toFixed(3)} m</dd></div><div><dt>Commanded altitude</dt><dd>{(held.landing_guard?.target_m[2]??held.target_m[2]).toFixed(3)} m</dd></div><div><dt>Landing guard</dt><dd>{held.landing_guard?.mode??"Disabled"}</dd></div><div><dt>Fresh stable dwell</dt><dd>{(held.landing_guard?.stable_for_s??0).toFixed(3)} s</dd></div></>}
          </dl>
          <details><summary>Inspect all acceptance gates</summary><table><thead><tr><th>Gate</th><th>Value / limit</th><th>Result</th></tr></thead><tbody>{side.gates.map(g=><tr key={g.id}><th>{g.label}</th><td>{g.value===null?"—":g.value.toFixed(3)} / {g.operator} {g.limit.toFixed(3)} {g.unit}</td><td>{g.status.replaceAll("_"," ")}</td></tr>)}</tbody></table></details>
        </section>;
      })}</div>
      <p>Display poses interpolate between recorded frames. Capture age, feedback and numeric errors use the preceding recorded timestamp. Full-rate gates use every physics/control sample.</p>
      {quality&&<p>Feedback error remains visible after landing and disarming. The predictor does not model ground support, so its altitude estimate can drift after thrust is switched off; that error no longer drives the motors.</p>}
    </>}
    <footer><p>{quality?"Three previously tested regression seeds. No-outage flights and all failures remain in the full report. Each quality is paired against its own no-outage flight for recovery checks. The first capture is available at startup; delayed age then spans 40–55 ms. This is a synthetic sensitivity study, not a calibrated sensor or fused estimator.":axis?"All six seeds were previously tested. No-outage flights remain in the full report, including their failures. Extra captures hold between 50 Hz updates; the landing guard is disabled.":guarded?"Separate regression and frozen unseen-seed cohorts. Holding a command cannot guarantee altitude when prediction is inaccurate.":"Research comparison on three regression seeds."} Synthetic outages, ideal attitude and simplified wind/contact; predictor expires after 2.1 s. No hardware-flight claim. The independent yaw-refinement finding remains open.</p>
      {index&&<><p>{index.display}</p><p>Baseline source <code>{(cohort?.baseline_source??index.baseline_source).slice(0,12)}</code> · candidate source <code>{(cohort?.candidate_source??index.candidate_source).slice(0,12)}</code></p></>}
      {reportUrl&&<a href={reportUrl} download={quality?"horizontal-quality-study.json":axis?"axis-availability-study.json":guarded?"landing-guard-study.json":"predictive-feedback-study.json"}>Download verified full-rate study</a>}
    </footer>
  </main>;
}
