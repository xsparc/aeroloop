import {lazy,Suspense,useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {sampleAt} from './contracts.js';
import {evidenceBase,readVerified} from './load.js';
import {validateApproachIndex,validateApproach,type ApproachCase} from './approach-contract.js';
import {Plot} from './diagnosis.js';
import {CELLS,LABELS,COLORS,GROUPS,quartet,preset,radial,analyze,responseCurves,energyCurve,accelerationCurve,parseSelection,selectionHash,review,windowCsv,type Quartet,type Window} from './response-analysis.js';
import './response.css';
const Scene=lazy(()=>import('./scene.js'));
const fmt=(v:number|null|undefined,n=3)=>v==null?'Unavailable':v.toFixed(n);
const series=(names:string[],colors=COLORS)=>names.map((name,i)=>({name,column:i+1,color:colors[i]}));
const EFFECTS=series(['Fixed outage effect','Scheduled outage effect','Difference of effects']);
const ENERGY=series(['Wind work','Thrust work','Kinetic change','Residual']);
const ACCEL=series(['Measured X','Measured Y','Command X','Command Y']);
const FEEDBACK=series(['Radial error','Tangential error']);
const metricRows=[['rmse_m','Tracking RMSE','m'],['demand_rms_m_s2','Command RMS','m/s²'],['wind_work_j','Wind work','J'],['thrust_work_j','Thrust work','J'],['kinetic_change_j','Kinetic change','J'],['residual_j','Energy residual','J'],['demand_error_rms_m_s2','Acceleration/command mismatch RMS','m/s²'],['force_residual_rms_m_s2','Acceleration/force residual RMS','m/s²']] as const;
type SeedResult={id:string;cohort:string;seed:number;analysis:ReturnType<typeof analyze>;missions:number;outagePairs:number;recovery:number};
function Portrait({q,w,time,onSeek}:{q:Quartet;w:Window;time:number;onSeek:(t:number)=>void}){
  const traces=useMemo(()=>q.flights.map(f=>f.rows.filter(r=>r[0]>=w.start&&r[0]<=w.end).map(r=>({t:r[0],...radial(r)}))),[q,w]);
  const valid=traces.flat().filter(p=>p.closing!==null),xmax=Math.max(.1,...valid.map(p=>p.distance)),ymax=Math.max(.1,...valid.map(p=>Math.abs(p.closing!)));
  const x=(v:number)=>60+v/xmax*830,y=(v:number)=>140-v/ymax*100;
  return <div className="dg-plot"><h3>Distance versus closing velocity</h3><svg viewBox="0 0 960 290" role="img" aria-label="Radial phase portrait">
    <line x1="60" x2="890" y1="140" y2="140" stroke="#526079"/>
    {traces.map((points,k)=>{let connected=false;const path=points.map(p=>{if(p.closing===null){connected=false;return '';}const command=connected?'L':'M';connected=true;return `${command}${x(p.distance).toFixed(2)},${y(p.closing).toFixed(2)}`;}).join(' ');const current=points.find(p=>Math.abs(p.t-time)<1e-7);return <g key={k}><path d={path} fill="none" stroke={COLORS[k]} strokeWidth="1.5"/>{current?.closing!=null&&<circle cx={x(current.distance)} cy={y(current.closing)} r="5" fill={COLORS[k]}/>}</g>;})}
    <text x="60" y="20">Closing + / receding − · ±{fmt(ymax)} m/s</text><text x="60" y="280">Distance to target · 0 → {fmt(xmax)} m</text>
  </svg><div className="dg-legend">{LABELS.map((s,i)=><span key={s}><i style={{background:COLORS[i]}}/>{s}</span>)}</div><p>Each path follows recorded time; crossings need not mean the same state history. The marker follows the shared cursor.</p><button onClick={()=>onSeek(w.start)}>Inspect window start</button></div>;
}
export function ResponseWorkspace({baseUrl,indexSha256}:{baseUrl:string;indexSha256:string}){
  const initial=useMemo(()=>parseSelection(location.hash,indexSha256),[indexSha256]);
  const [entries,setEntries]=useState<ApproachCase[]>([]),[selected,setSelected]=useState(initial?.id??'stress-s401'),[q,setQ]=useState<Quartet|null>(null),[error,setError]=useState('');
  const [w,setW]=useState<Window>({start:initial?.start??40,end:initial?.end??43}),[time,setTime]=useState(initial?.time??40),[playing,setPlaying]=useState(false),[focus,setFocus]=useState(3);
  const [show3d,setShow3d]=useState(false),[failed3d,setFailed3d]=useState(false),[visible,setVisible]=useState(!document.hidden),[share,setShare]=useState('');
  const [seedResults,setSeedResults]=useState<SeedResult[]>([]),[scanning,setScanning]=useState(false),[scanError,setScanError]=useState(''),[sort,setSort]=useState('seed');
  const scan=useRef<AbortController|null>(null),fail3d=useCallback(()=>setFailed3d(true),[]);
  useEffect(()=>{const abort=new AbortController();setEntries([]);setQ(null);setError('');
    void Promise.resolve().then(()=>readVerified(new URL('index.json',evidenceBase(baseUrl,location.origin)),indexSha256,abort.signal,16384)).then(v=>{if(!abort.signal.aborted)setEntries(validateApproachIndex(v));}).catch(()=>{if(!abort.signal.aborted)setError('Verified approach index unavailable. Prepare the measured export.');});return()=>abort.abort();
  },[baseUrl,indexSha256]);
  const load=useCallback(async(id:string,signal:AbortSignal)=>{
    const group=GROUPS.find(g=>g.id===id);if(!group)throw Error();
    const pair=[0,1].map(p=>entries.find(e=>e.id===`${group.cohort}-p${p}-s${group.seed}`));if(pair.some(e=>!e))throw Error();
    const es=pair as ApproachCase[],values=await Promise.all(es.map(async e=>validateApproach(await readVerified(new URL(e.file,evidenceBase(baseUrl,location.origin)),e.sha256,signal,12*1024*1024),e)));
    return quartet(values[0],values[1],es);
  },[entries,baseUrl]);
  useEffect(()=>{setQ(null);setPlaying(false);setError('');setShare('');setFailed3d(false);if(!entries.length)return;
    const abort=new AbortController();void load(selected,abort.signal).then(value=>{if(!abort.signal.aborted)setQ(value);}).catch(()=>{if(!abort.signal.aborted)setError('Four-flight evidence failed integrity or identity checks. No unverified flight is displayed.');});return()=>abort.abort();
  },[entries,selected,load]);
  useEffect(()=>{scan.current?.abort();setSeedResults([]);setScanning(false);setScanError('');return()=>scan.current?.abort();},[w,entries]);
  useEffect(()=>{const hide=()=>{setVisible(!document.hidden);if(document.hidden)setPlaying(false);};document.addEventListener('visibilitychange',hide);return()=>document.removeEventListener('visibilitychange',hide);},[]);
  const result=useMemo(()=>q?analyze(q,w):null,[q,w]),complete=!!result?.cells.every(c=>c.complete);
  useEffect(()=>{if(!playing||!visible||!complete)return;let id=0,previous=0;const tick=(now:number)=>{if(previous)setTime(t=>{const n=Math.min(w.end,t+Math.min((now-previous)/1000,.1)*.5);if(n>=w.end)setPlaying(false);return n;});previous=now;id=requestAnimationFrame(tick);};id=requestAnimationFrame(tick);return()=>cancelAnimationFrame(id);},[playing,visible,complete,w]);
  const seek=(t:number)=>{setPlaying(false);setTime(Math.max(w.start,Math.min(w.end,Math.round(t/.005)*.005)));setShare('');};
  function windowTo(next:Window){setPlaying(false);setW(next);setTime(next.start);setShare('');}
  function editWindow(key:'start'|'end',raw:string){const n=Number(raw);if(!raw||!Number.isFinite(n))return;const value=Math.max(34,Math.min(50,Math.round(n/.005)*.005)),next={...w,[key]:value};if(next.end-next.start>=.004999)windowTo(next);}
  const effects=useMemo(()=>q?responseCurves(q,w):[],[q,w]);
  const energy=useMemo(()=>q?energyCurve(q.flights[focus],w):[],[q,w,focus]);
  const accel=useMemo(()=>q?accelerationCurve(q.flights[focus],w):[],[q,w,focus]);
  const feedback=useMemo(()=>q?q.flights[focus].rows.filter(r=>r[0]>=w.start&&r[0]<=w.end).map(r=>({t:r[0],...radial(r)})):[],[q,w,focus]);
  // Break at undefined radial directions rather than joining across the target.
  const segments=useMemo(()=>{const all:number[][][]=[[]];for(const p of feedback){if(p.radial_error===null){if(all.at(-1)!.length)all.push([]);}else all.at(-1)!.push([p.t,p.radial_error,p.tangential_error!]);}return all.filter(a=>a.length>1);},[feedback]);
  function shareReview(){const s={...w,id:selected,time:Math.round(time/.005)*.005},hash=selectionHash(s,indexSha256);history.replaceState(null,'',location.pathname+hash);setShare(location.origin+location.pathname+hash);}
  function download(kind:'json'|'csv'){if(!q)return;const s={...w,id:selected,time:Math.round(time/.005)*.005},text=kind==='json'?JSON.stringify(review(q,s,indexSha256),null,2)+'\n':windowCsv(q,w,indexSha256),url=URL.createObjectURL(new Blob([text],{type:kind==='json'?'application/json':'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`${selected}-response.${kind}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  async function compareSeeds(){scan.current?.abort();const abort=new AbortController();scan.current=abort;setSeedResults([]);setScanning(true);setScanError('');
    try{for(const g of GROUPS){const value=await load(g.id,abort.signal);if(abort.signal.aborted)return;const row={...g,analysis:analyze(value,w),missions:value.flights.filter(f=>f.status==='passed').length,outagePairs:value.flights.filter(f=>f.outage?.passed).length,recovery:value.flights.flatMap(f=>f.outage?.recovery??[]).filter(r=>r.passed).length};setSeedResults(old=>[...old,row]);}}
    catch{if(!abort.signal.aborted){setSeedResults([]);setScanError('Seed comparison rejected. No partial ranking is retained.');}}
    finally{if(!abort.signal.aborted)setScanning(false);}
  }
  const ranked=[...seedResults].sort((a,b)=>sort==='interaction'?(b.analysis.rmse.interaction??-Infinity)-(a.analysis.rmse.interaction??-Infinity):GROUPS.findIndex(g=>g.id===a.id)-GROUPS.findIndex(g=>g.id===b.id));
  return <main className="dg ds ag response"><header className="dg-header"><a href="/approach.html">AEROLOOP / APPROACH STUDY</a><span>Recorded PhysX · simulation only</span></header>
    <div className="dg-hero"><div><p className="dg-eyebrow">LANDING RESPONSE / 04</p><h1>Separate the gains.<br/>Expose the outage.</h1><p>Four measured flights, one clock. Inspect where tracking changes, how forces do work, and what remains unexplained.</p></div><div className="dg-summary"><strong>2 × 2</strong><span>gain mode × observation profile</span><strong>36</strong><span>retained PhysX flights · 9 seeds</span><strong>5 ms</strong><span>recorded physics intervals</span></div></div>
    <p><a href="/friction.html">Open measured ground friction and momentum closure</a></p>
    {error&&<p role="alert" className="dg-alert">{error}</p>}
    <section className="dg-panel"><h2>01 / Choose a matched seed</h2><div className="ag-cases">{GROUPS.map(g=><button key={g.id} aria-pressed={g.id===selected} onClick={()=>{setSelected(g.id);setPlaying(false);}}>{g.cohort} · seed {g.seed}</button>)}</div><p>Each group includes both gain modes with and without 18–20 s and 40–42 s outages. Landing differences reflect the whole prior flight history.</p></section>
    {!q&&!error&&<p role="status">Verifying four-flight evidence…</p>}
    {q&&result&&<><section className="dg-panel"><h2 data-testid="response-selected">02 / {q.cohort} · seed {q.seed}</h2><div className="response-window"><label>Window start (s)<input aria-label="Window start" type="number" min="34" max="49.995" step=".005" value={w.start} onChange={e=>editWindow('start',e.target.value)}/></label><label>Window end (s)<input aria-label="Window end" type="number" min="34.005" max="50" step=".005" value={w.end} onChange={e=>editWindow('end',e.target.value)}/></label></div>
      <div className="ag-chapters">{[['full','Common available'],['airborne','All pre-contact'],['armed','All armed'],['disarmed','All disarmed'],['gust','Landing gust']].map(([kind,label])=>{const value=preset(q,kind as Parameters<typeof preset>[1]);return <button key={kind} disabled={!value} onClick={()=>windowTo(value!)}>{label}</button>;})}</div>
      <p>Same requested window for all four flights. Pre-contact/armed ends one sample before the first relevant event; disarmed begins after every flight has disarmed.</p>
      {!complete&&<p className="dg-alert" role="alert">Requested window is not fully recorded in all four flights. Contrasts and playback are unavailable; incomplete evidence is not a pass.</p>}
      <div className="ag-chapters"><button disabled={!complete} onClick={()=>{if(time>=w.end)setTime(w.start);setPlaying(p=>!p);}}>{playing?'Pause':'Play four flights ½×'}</button><button disabled={!complete} onClick={()=>seek(time-.005)}>Previous interval</button><button disabled={!complete} onClick={()=>seek(time+.005)}>Next interval</button><strong data-testid="response-cursor">{fmt(time)} s</strong></div>
      <input aria-label="Response time" type="range" min={w.start} max={w.end} step=".005" value={time} disabled={!complete} onChange={e=>seek(Number(e.target.value))}/><p>3D playback interpolates poses; numeric cursor values use the nearest recorded 5 ms state. Plots and exports retain every physics interval.</p>
      <div className="ag-chapters"><button disabled={!complete} onClick={()=>setShow3d(v=>!v)}>{show3d?'Hide four-flight 3D':'Enable four-flight 3D'}</button><button onClick={shareReview}>Share response review</button><button onClick={()=>download('json')}>Export response JSON</button><button onClick={()=>download('csv')}>Export interval CSV</button></div>
      {share&&<label className="ds-share">Evidence-bound link<input aria-label="Response review link" value={share} readOnly onFocus={e=>e.target.select()}/></label>}
    </section>
    <div className="response-cells">{q.flights.map((f,i)=>{const c=result.cells[i],r=f.rows[Math.round((time-34)/.005)];return <section className="dg-panel" aria-label={CELLS[i]} key={CELLS[i]}><h2 style={{color:COLORS[i]}}>{LABELS[i]}</h2><p className={f.status==='failed'?'dg-alert':''}>Original mission: <strong>{f.status.toUpperCase()}</strong></p><p>{f.outage?`Original outage pair: ${f.outage.passed?'passed':'failed'} · recovery ${f.outage.recovery.filter(r=>r.passed).length}/2`:'No-outage reference'}</p>
      {show3d&&complete&&!failed3d&&<div className="dg-scene"><Suspense fallback={<p>Loading 3D…</p>}><Scene sample={sampleAt(f.poses,time)} samples={f.poses} rotorFlight visible={visible} onFailure={fail3d}/></Suspense></div>}{show3d&&failed3d&&<p>3D unavailable. Numeric diagnostics remain available.</p>}
      <p>{c.states} states · {c.intervals} intervals · {c.complete?'complete':'incomplete'} requested window</p><p>Airborne {fmt(c.airborne_s)} s · contact-affected {fmt(c.contact_s)} s · disarmed {fmt(c.disarmed_s)} s</p><p>Cursor error {fmt(r?.[31])} m · speed {fmt(r?.[32])} m/s · tilt {fmt(r?.[37])}°</p>
      <details><summary>Original gates and recording identity</summary><p>Source {f.provenance.source_commit}</p><p>Samples SHA-256 {f.provenance.samples_sha256}</p><ul>{f.gates.map(g=><li key={g.id}>{g.label}: {fmt(g.value)} {g.unit} · {g.status}</li>)}</ul></details></section>;})}</div>
    <section className="dg-panel"><h2>03 / Outage effects on tracking</h2><div className="response-effects"><p>Fixed RMSE effect<strong>{fmt(result.rmse.fixed)} m</strong></p><p>Scheduled RMSE effect<strong>{fmt(result.rmse.scheduled)} m</strong></p><p>Difference of RMSE effects<strong>{fmt(result.rmse.interaction)} m</strong></p></div><p>Outage − intact within each gain mode; interaction = scheduled effect − fixed effect. Negative means lower recorded error, not success or statistical significance.</p>
      {effects.length>1&&<Plot title="Instantaneous tracking-error effects · m" rows={effects} series={EFFECTS} start={w.start} end={w.end} time={time} onSeek={seek} windows={[[40,42]]}/>}
      <p>The curve subtracts instantaneous distances. The cards subtract window RMSEs; these are different metrics.</p><div className="ds-table"><table aria-label="Four-flight window metrics"><thead><tr><th>Metric</th>{LABELS.map(l=><th key={l}>{l}</th>)}</tr></thead><tbody>{metricRows.map(([key,label,unit])=><tr key={key}><th>{label} · {unit}</th>{result.cells.map((s,i)=><td key={i}>{fmt(s[key])}</td>)}</tr>)}</tbody></table></div>
    </section>
    <section className="dg-panel"><h2>04 / Radial motion</h2><Portrait q={q} w={w} time={Math.round(time/.005)*.005} onSeek={seek}/><p>Closing speed uses velocity relative to the target. Below 1 nm distance the direction is undefined and omitted.</p></section>
    <section className="dg-panel"><h2>05 / Inspect interval physics</h2><label>Diagnostic flight<select aria-label="Diagnostic flight" value={focus} onChange={e=>setFocus(Number(e.target.value))}>{LABELS.map((l,i)=><option key={l} value={i}>{l}</option>)}</select></label>
      {energy.length>1&&<Plot title="Horizontal translational work budget · J" rows={energy} series={ENERGY} start={w.start} end={w.end} time={time} onSeek={seek} windows={[[40,42]]}/>}<p>Wind/thrust work sums preceding force × observed displacement. Kinetic change uses recorded endpoint velocity for the 1 kg model. Residual includes unmeasured contact/solver and integration effects; it is not measured friction or battery energy.</p>
      {accel.length>1&&<><Plot title="Interval acceleration and preceding command · m/s²" rows={accel} series={ACCEL} start={w.start} end={w.end} time={time} onSeek={seek} windows={[[40,42]]}/><Plot title="Acceleration mismatches · m/s²" rows={accel} series={[{name:'Against command',column:5,color:COLORS[1]},{name:'Against applied force / mass',column:6,color:COLORS[3]}]} start={w.start} end={w.end} time={time} onSeek={seek} windows={[[40,42]]}/></>}
      <p>Acceleration is Δvelocity / 5 ms over the next interval. Contact impulses and actuator dynamics can separate it from demand. The terminal state has no next-interval estimate.</p>
      {segments.map((rows,i)=><Plot key={i} title={`Applied-feedback radial / tangential position error · m${segments.length>1?` · segment ${i+1}`:''}`} rows={rows} series={FEEDBACK} start={w.start} end={w.end} time={time} onSeek={seek} windows={[[40,42]]}/>)}<p>{feedback.filter(p=>p.closing===null).length} states with undefined radial direction. Radial points away from target; tangent is counterclockwise. Error = applied feedback − physics truth.</p>
    </section></>}
    <section className="dg-panel"><h2>06 / Compare all nine seeds</h2><p>Apply the exact {fmt(w.start)}–{fmt(w.end)} s window to every seed. A selected seed’s phase boundaries need not describe another seed; exposure is retained per row.</p><div className="ag-chapters"><button disabled={!entries.length||scanning} onClick={()=>void compareSeeds()}>{scanning?`Verifying seeds ${seedResults.length}/9…`:'Compare nine seeds'}</button><label>Sort comparison<select aria-label="Sort seed comparison" value={sort} onChange={e=>setSort(e.target.value)}><option value="seed">Cohort / seed</option><option value="interaction">Largest RMSE interaction first</option></select></label></div>{scanError&&<p role="alert" className="dg-alert">{scanError}</p>}
      {!scanning&&seedResults.length===9&&<div className="ds-table"><table aria-label="Seed response comparison"><thead><tr><th>Seed</th><th>Fixed outage ΔRMSE</th><th>Scheduled outage ΔRMSE</th><th>Interaction</th><th>Airborne s · four cells</th><th>Original missions / pairs / recovery</th></tr></thead><tbody>{ranked.map(r=><tr key={r.id}><td><button onClick={()=>setSelected(r.id)}>{r.cohort} {r.seed}</button></td><td>{fmt(r.analysis.rmse.fixed)}</td><td>{fmt(r.analysis.rmse.scheduled)}</td><td>{fmt(r.analysis.rmse.interaction)} m</td><td>{r.analysis.cells.map(s=>fmt(s.airborne_s,2)).join(' / ')}</td><td>{r.missions}/4 · {r.outagePairs}/2 · {r.recovery}/4</td></tr>)}</tbody></table></div>}
    </section>
    <footer className="dg-panel"><p>Every original failure remains unchanged. Verified index mission passes: fixed {entries.filter(e=>e.baseline_status==='passed').length}/{entries.length}, scheduled {entries.filter(e=>e.candidate_status==='passed').length}/{entries.length}. These are small synthetic cohorts, with ideal attitude/contact supervision and simplified wind and rotor models. Scheduled gains remain opt-in; AL-010 yaw refinement remains open.</p><p>This workspace analyzes recorded physics; it does not run a new flight or test a counterfactual controller. Live monitoring remains available from the approach study.</p></footer>
  </main>;
}
