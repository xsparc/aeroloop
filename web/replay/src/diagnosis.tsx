import {lazy,Suspense,useCallback,useEffect,useMemo,useState} from 'react';
import {sampleAt} from './contracts.js';
import {evidenceBase,readVerified} from './load.js';
import {QUALITY,PROFILE,PHASES,validateDiagnosisIndex,validateDiagnosis,validateDiagnosisPair,windowCsv,type DiagnosisCase,type Diagnosis} from './diagnosis-contract.js';
import './diagnosis.css';
const Scene=lazy(()=>import('./scene.js'));
const labels:Record<string,string>={ideal:'Ideal',noise:'Noise',delay:'40 ms delay','noise-delay':'Noise + delay','sample-hold':'No outage','hold-dropout-2000ms':'2 s outages'};
const fmt=(n:number|null|undefined,d=3)=>n==null?'Not measured':n.toFixed(d);
const phaseLabel=(s:string)=>s.replaceAll('-',' ');
type Series={name:string;column:number;color:string};
function Plot({title,rows,series,start,end,time,onSeek,band}:{title:string;rows:number[][];series:Series[];start:number;end:number;time:number;onSeek:(t:number)=>void;band?:number}){
  const chart=useMemo(()=>{
    const selected=rows.filter(r=>r[0]>=start&&r[0]<=end),values=selected.flatMap(r=>series.map(s=>r[s.column]));
    let min=Math.min(0,...values),max=Math.max(.001,...values,band??0);const pad=(max-min)*.08;min-=pad;max+=pad;
    const x=(t:number)=>45+(t-start)/(end-start)*900,y=(v:number)=>150-(v-min)/(max-min)*130;
    return {min,max,x,y,paths:series.map(s=>({...s,path:selected.map((r,i)=>`${i?'L':'M'}${x(r[0]).toFixed(2)},${y(r[s.column]).toFixed(2)}`).join(' ')})),count:selected.length};
  },[rows,series,start,end,band]);
  return <div className="dg-plot"><div className="dg-plot-title"><h3>{title}</h3><small>{chart.count.toLocaleString()} recorded points</small></div>
    <svg viewBox="0 0 960 180" role="img" aria-label={`${title}; click to move cursor`} onClick={e=>{const r=e.currentTarget.getBoundingClientRect();onSeek(Math.max(start,Math.min(end,start+((e.clientX-r.left)/r.width*960-45)/900*(end-start))));}}>
      {[18,40].map(s=><rect key={s} x={chart.x(Math.max(start,s))} y="15" width={Math.max(0,chart.x(Math.min(end,s+2))-chart.x(Math.max(start,s)))} height="135" fill="#f59e0b" opacity=".09"/>)}
      {[0,.5,1].map(f=><g key={f}><line x1="45" x2="945" y1={20+f*130} y2={20+f*130} stroke="#273547"/><text x="2" y={23+f*130}>{(chart.max-(chart.max-chart.min)*f).toFixed(2)}</text></g>)}
      {band!==undefined&&<line x1="45" x2="945" y1={chart.y(band)} y2={chart.y(band)} stroke="#fbbf24" strokeDasharray="5 4"/>}
      {chart.paths.map(s=><path key={s.name} d={s.path} fill="none" stroke={s.color} strokeWidth="1.7"/>)}
      {time>=start&&time<=end&&<line x1={chart.x(time)} x2={chart.x(time)} y1="10" y2="151" stroke="white" strokeDasharray="3 3"/>}
      <text x="45" y="173">{start.toFixed(3)} s</text><text x="945" y="173" textAnchor="end">{end.toFixed(3)} s</text>
    </svg><div className="dg-legend">{series.map(s=><span key={s.name}><i style={{background:s.color}}/>{s.name}</span>)}</div>
  </div>;
}
const ALTITUDE:Series[]=[{name:'Truth',column:1,color:'#68e2bc'},{name:'Raw capture',column:2,color:'#e7b16a'},{name:'Predictor',column:3,color:'#c19bff'},{name:'Applied',column:4,color:'#70baff'}];
const ERROR:Series[]=[{name:'Horizontal',column:5,color:'#68e2bc'},{name:'Vertical',column:6,color:'#c19bff'}];
const FORCE:Series[]=[{name:'Requested thrust',column:7,color:'#70baff'},{name:'Contact force',column:8,color:'#e7b16a'}];
const DISTANCE:Series[]=[{name:'Distance to no-outage reference',column:11,color:'#68e2bc'}];
export function DiagnosisWorkspace({baseUrl,indexSha256}:{baseUrl:string;indexSha256:string}){
  const [cases,setCases]=useState<DiagnosisCase[]>([]),[selected,setSelected]=useState('q3-p1-s0'),[data,setData]=useState<{reference:Diagnosis;flight:Diagnosis}|null>(null),[error,setError]=useState('');
  const [quality,setQuality]=useState('all'),[profile,setProfile]=useState('all'),[status,setStatus]=useState('all'),[sort,setSort]=useState('matrix');
  const [time,setTime]=useState(40),[start,setStart]=useState(40),[end,setEnd]=useState(43),[playing,setPlaying]=useState(false),[speed,setSpeed]=useState(1);
  const [show3d,setShow3d]=useState(false),[failed3d,setFailed3d]=useState(false),[visible,setVisible]=useState(!document.hidden),[overlays,setOverlays]=useState(['Truth','Raw capture','Predictor','Applied']);
  const fail=useCallback(()=>setFailed3d(true),[]);
  useEffect(()=>{const abort=new AbortController();setCases([]);setData(null);setError('');
    void readVerified(new URL('index.json',evidenceBase(baseUrl,location.origin)),indexSha256,abort.signal,32768).then(v=>{const c=validateDiagnosisIndex(v);if(!abort.signal.aborted)setCases(c);}).catch(()=>{if(!abort.signal.aborted)setError('Evidence index unavailable or invalid. Prepare a verified diagnosis export.');});
    return()=>abort.abort();},[baseUrl,indexSha256]);
  useEffect(()=>{setData(null);setError('');setPlaying(false);setFailed3d(false);if(!cases.length)return;
    const abort=new AbortController(),entry=cases.find(c=>c.id===selected)!,ref=cases.find(c=>c.id===entry.reference_id)!;
    const load=async(c:DiagnosisCase)=>validateDiagnosis(await readVerified(new URL(c.file,evidenceBase(baseUrl,location.origin)),c.sha256,abort.signal,8*1024*1024),c);
    void (async()=>{const [reference,flight]=entry.id===ref.id?await load(entry).then(v=>[v,v]):await Promise.all([load(ref),load(entry)]);validateDiagnosisPair(reference,flight);
      if(!abort.signal.aborted){const last=flight.rows.at(-1)![0];setTime(Math.min(40,last));setStart(Math.min(40,Math.max(0,last-.005)));setEnd(Math.min(43,last));setData({reference,flight});}
    })().catch(()=>{if(!abort.signal.aborted)setError('Flight failed integrity or consistency checks. No unverified flight is displayed.');});return()=>abort.abort();
  },[cases,selected,baseUrl]);
  useEffect(()=>{const hide=()=>{setVisible(!document.hidden);if(document.hidden)setPlaying(false);};document.addEventListener('visibilitychange',hide);return()=>document.removeEventListener('visibilitychange',hide);},[]);
  useEffect(()=>{if(!playing||!visible)return;let id=0,previous=0;const tick=(now:number)=>{if(previous)setTime(t=>{const next=Math.min(end,t+Math.min((now-previous)/1000,.1)*speed);if(next===end)setPlaying(false);return next;});previous=now;id=requestAnimationFrame(tick);};id=requestAnimationFrame(tick);return()=>cancelAnimationFrame(id);},[playing,visible,speed,end]);
  const filtered=useMemo(()=>{const result=cases.filter(c=>(quality==='all'||c.quality===quality)&&(profile==='all'||c.profile===profile)&&(status==='all'||c.status===status));if(sort==='support')result.sort((a,b)=>(a.support_headroom_m??-Infinity)-(b.support_headroom_m??-Infinity));return result;},[cases,quality,profile,status,sort]);
  const series=useMemo(()=>ALTITUDE.filter(s=>overlays.includes(s.name)),[overlays]);
  const seek=useCallback((t:number)=>{setPlaying(false);setTime(Math.round(t/.005)*.005);},[]);
  function windowTo(a:number,b:number){if(!data)return;const last=data.flight.rows.at(-1)![0];a=Math.max(0,Math.min(a,last-.005));b=Math.max(a+.005,Math.min(b,last));setStart(a);setEnd(b);seek(a);}
  function jump(t:number){windowTo(Math.max(0,t-1),t+1);seek(t);}
  function download(){if(!data)return;const blob=URL.createObjectURL(new Blob([windowCsv(data.flight,start,end)],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=blob;a.download=`${selected}-${start.toFixed(3)}-${end.toFixed(3)}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(blob),1000);}
  const flight=data?.flight,reference=data?.reference,row=flight?.rows[Math.min(flight.rows.length-1,Math.floor((time+1e-9)/.005))];
  return <main className="dg"><header className="dg-header"><a href="/quality.html">AEROLOOP / SIMULATION LAB</a><span>Recorded PhysX · simulation only</span></header>
    <div className="dg-hero"><div><p className="dg-eyebrow">FLIGHT DIAGNOSIS / 01</p><h1>Find the moment<br/>control gives way.</h1><p>Inspect landing, feedback and recovery at every physics step.</p></div><div className="dg-summary"><strong>{cases.length||'—'}</strong><span>retained flights</span><strong>200 Hz</strong><span>original physics samples</span><strong>{cases.length?`${cases.filter(c=>c.status==='passed').length} / ${cases.length}`:'—'}</strong><span>missions passed · failures retained</span></div></div>
    {error&&<p className="dg-alert" role="alert">{error}</p>}
    <div className="dg-layout"><aside className="dg-panel"><h2>01 / Case matrix</h2><div className="dg-filters">
      <label>Quality<select aria-label="Quality" value={quality} onChange={e=>setQuality(e.target.value)}><option value="all">All qualities</option>{QUALITY.map(q=><option key={q} value={q}>{labels[q]}</option>)}</select></label>
      <label>Profile<select aria-label="Profile" value={profile} onChange={e=>setProfile(e.target.value)}><option value="all">All profiles</option>{PROFILE.map(p=><option key={p} value={p}>{labels[p]}</option>)}</select></label>
      <label>Mission outcome<select aria-label="Mission outcome" value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All outcomes</option><option value="failed">Failed</option><option value="passed">Passed</option></select></label>
      <label>Sort cases<select aria-label="Sort cases" value={sort} onChange={e=>setSort(e.target.value)}><option value="matrix">Quality / profile / seed</option><option value="support">Least support headroom</option></select></label></div>
      <p className="dg-muted">{filtered.length} of {cases.length} cases · seed 0 / 1 / 2</p><div className="dg-case-list" aria-label="Flight cases">{filtered.map(c=><button key={c.id} aria-pressed={selected===c.id} onClick={()=>setSelected(c.id)}><span>{labels[c.quality]} · seed {c.seed}<small>{labels[c.profile]}</small></span><span className={c.status==='failed'?'dg-bad':'dg-good'}>{c.status}</span></button>)}</div>
      <p className="dg-note">Previously tested regression seeds. These recordings do not establish general robustness.</p></aside>
    <section className="dg-panel dg-flight" aria-label="Selected flight"><h2>02 / Same-quality comparison</h2>
      {!flight||!reference||!row?<p role="status">{error?'Evidence rejected.':'Verifying flight evidence…'}</p>:<>
      <div className="dg-flight-heading"><h3>{labels[flight.quality]} · seed {flight.seed}<small>{labels[flight.profile]}</small></h3><span className={flight.status==='failed'?'dg-badge dg-bad':'dg-badge dg-good'}>{flight.status.toUpperCase()}</span></div>
      {flight.id===reference.id&&<p className="dg-note">Reference-to-self: both views show the no-outage flight. Pair and recovery scoring do not apply.</p>}
      {flight.rows.length!==10001&&<p className="dg-alert" role="alert">Incomplete recording: {flight.rows.length} of 10,001 samples. Missing intervals are not evidence of recovery.</p>}
      <div className="dg-scenes">{[{name:'No-outage reference',run:reference},{name:'Selected flight',run:flight}].map(({name,run})=><div key={name} className="dg-scene"><h4>{name} <span className={run.status==='passed'?'dg-good':'dg-bad'}>{run.status}</span></h4>{show3d&&!failed3d?<Suspense fallback={<p>Loading renderer…</p>}><Scene sample={sampleAt(run.poses,time)} samples={run.poses} rotorFlight={true} visible={visible} onFailure={fail}/></Suspense>:<div className="dg-scene-placeholder">{failed3d?'3D unavailable. Numeric evidence remains available.':'Recorded path · schematic 3D'}</div>}</div>)}</div>
      <div className="dg-controls"><button disabled={failed3d} onClick={()=>setShow3d(v=>!v)}>{show3d?'Hide paired 3D':'Enable paired 3D'}</button><button onClick={()=>{if(time>=end||time<start)setTime(start);setPlaying(v=>!v);}}>{playing?'Pause':'Play'}</button><label>Speed<select value={speed} onChange={e=>setSpeed(Number(e.target.value))}>{[.25,.5,1,2].map(s=><option key={s} value={s}>{s}×</option>)}</select></label><output aria-label="Recorded time">{row[0].toFixed(3)} s</output></div>
      <label className="dg-scrub">Recorded time<input aria-label="Recorded time" type="range" min={start} max={end} step=".005" value={Math.min(end,Math.max(start,time))} onChange={e=>seek(Number(e.target.value))}/></label>
      <div className="dg-readings"><span>State<strong>{phaseLabel(PHASES[row[12]])}</strong></span><span>Thrust request<strong>{fmt(row[7])} N</strong></span><span>Applied Z error<strong>{fmt(row[6])} m</strong></span><span>Main / horizontal age<strong>{fmt(row[9]*1000,0)} / {fmt(row[10]*1000,0)} ms</strong></span></div>
      </>}
    </section></div>
    {flight&&row&&<>
    <section className="dg-panel"><h2>03–04 / Timeline & events</h2><div className="dg-controls"><button onClick={()=>windowTo(0,50)}>Whole flight</button><button onClick={()=>windowTo(18,21)}>First outage</button><button onClick={()=>windowTo(40,43)}>Landing window</button><button onClick={()=>windowTo(48,50)}>Final support</button><label>Window start (s)<input type="number" min="0" max={end-.005} step=".005" value={start} onChange={e=>{if(e.target.value!==''&&Number.isFinite(e.target.valueAsNumber))windowTo(e.target.valueAsNumber,end);}}/></label><label>Window end (s)<input type="number" min={start+.005} max={flight.rows.at(-1)![0]} step=".005" value={end} onChange={e=>{if(e.target.value!==''&&Number.isFinite(e.target.valueAsNumber))windowTo(start,e.target.valueAsNumber);}}/></label></div>
      <div className="dg-events">{flight.events.map((e,i)=><button key={i} onClick={()=>jump(e.time_s)}>{e.type.replaceAll('_',' ')}<small>{e.time_s.toFixed(3)} s</small></button>)}</div>
      <p className="dg-muted">Click a plot or use the time slider. Numeric values use the preceding 5 ms sample; only schematic poses interpolate. Amber bands mark the scheduled outage windows.</p>
      <Plot title="Applied feedback error (m)" rows={flight.rows} series={ERROR} start={start} end={end} time={time} onSeek={seek}/>
      <Plot title="Thrust request and ground contact (N)" rows={flight.rows} series={FORCE} start={start} end={end} time={time} onSeek={seek}/>
    </section>
    <section className="dg-panel"><h2>05 / Landing error by state</h2><p>Applied feedback minus physics truth over [40, 42) s. Every sample belongs to one state; motors-off takes precedence over contact.</p><p className="dg-muted">{flight.phase_errors.sample_count} / 400 samples · {flight.phase_errors.complete?'complete coverage':'incomplete coverage'}. Empty states remain unmeasured.</p>
      <div className="dg-table-wrap"><table><thead><tr><th>State</th><th>Samples</th><th>XY RMSE / peak (m)</th><th>Z RMSE / peak (m)</th><th>Z peak time (s)</th></tr></thead><tbody>{flight.phase_errors.groups.map(g=><tr key={g.phase}><th>{phaseLabel(g.phase)}</th><td>{g.samples}</td><td>{fmt(g.horizontal_rmse_m)} / {fmt(g.horizontal_peak_m)}</td><td>{fmt(g.vertical_rmse_m)} / {fmt(g.vertical_peak_m)}</td><td><button disabled={g.vertical_peak_time_s===null} onClick={()=>jump(g.vertical_peak_time_s!)}>{fmt(g.vertical_peak_time_s)}</button></td></tr>)}</tbody></table></div>
      <p className="dg-note">Contact may be intermittent. Motors-off means landed with zero requested thrust; residual rotor thrust can still decay. Predictor drift then no longer drives motor commands. These descriptive groups do not alter acceptance or prove the cause of an early touchdown.</p>
    </section>
    <section className="dg-panel"><h2>06 / Feedback layers</h2><div className="dg-controls">{ALTITUDE.map(s=><label key={s.name}><input type="checkbox" checked={overlays.includes(s.name)} onChange={e=>setOverlays(v=>e.target.checked?[...v,s.name]:v.filter(n=>n!==s.name))}/>{s.name}</label>)}</div><Plot title="Altitude (m)" rows={flight.rows} series={series} start={start} end={end} time={time} onSeek={seek}/><p className="dg-muted">Predictor and applied altitude overlap: only horizontal feedback is replaced in this experiment.</p></section>
    <section className="dg-panel"><h2>07 / Acceptance headroom</h2><p>Original full-rate mission gates. Positive headroom means remaining allowance; negative means exceeded. Equality gates have zero headroom when satisfied. A strict &lt; gate still fails at zero.</p><div className="dg-table-wrap"><table><thead><tr><th>Gate</th><th>Measured</th><th>Rule</th><th>Headroom</th><th>Outcome</th></tr></thead><tbody>{flight.gates.map(g=><tr key={g.id}><th>{g.label}</th><td>{fmt(g.value,5)} {g.unit}</td><td>{g.operator} {g.limit} {g.unit}</td><td>{g.headroom!=null&&g.headroom>0?'+':''}{fmt(g.headroom,5)} {g.unit}</td><td className={g.status==='passed'?'dg-good':'dg-bad'}>{g.status.replace('_',' ')}</td></tr>)}</tbody></table></div></section>
    <section className="dg-panel"><h2>08 / Sustained recovery</h2>{flight.comparison?<><p>Pair: <strong className={flight.comparison.passed?'dg-good':'dg-bad'}>{flight.comparison.passed?'passed':'failed'}</strong> · Landed-time change: {fmt(flight.comparison.landed_time_change_s)} s (limit 0.5 s). Recovery requires a final uninterrupted ≤0.05 m interval lasting ≥1 s, starting within 5 s of outage end.</p><Plot title="Separation from reference (m)" rows={flight.rows} series={DISTANCE} start={start} end={end} time={time} onSeek={seek} band={.05}/><div className="dg-recovery">{flight.comparison.recovery_windows.map(w=><div key={w.window_start_s}><h3>{w.window_start_s}–{w.window_end_s} s outage</h3><p className={w.passed?'dg-good':'dg-bad'}>{w.passed?'PASSED':'FAILED'} · {w.complete_horizon?'complete horizon':'incomplete horizon'}</p><p>Settled after {fmt(w.recovery_time_s)}{w.recovery_time_s===null?'':' s'} · horizon ends {w.horizon_end_s} s</p><button onClick={()=>windowTo(w.window_start_s,w.horizon_end_s)}>Inspect recovery horizon</button>{w.recovery_time_s!==null&&<button onClick={()=>jump(w.window_end_s+w.recovery_time_s!)}>Jump to final recovery</button>}</div>)}</div></>:<p>Not applicable to the no-outage reference. Self-comparison is not a recovery pass.</p>}</section>
    <section className="dg-panel"><h2>09 / Evidence provenance</h2><p>Retained Isaac Sim / PhysX recordings, re-verified for this workspace. No new flights. All three seeds were tested previously.</p><details><summary>Inspect source, hashes and runtime</summary><dl className="dg-provenance">{Object.entries(flight.provenance).map(([k,v])=><div key={k}><dt>{k.replaceAll('_',' ')}</dt><dd>{typeof v==='object'?Object.entries(v).map(([a,b])=>`${a}: ${b}`).join(' · '):String(v)}</dd></div>)}<div><dt>Coverage</dt><dd>{flight.rows.length} of 10,001 original samples; {flight.poses.length} display poses</dd></div></dl></details><p className="dg-note">Synthetic sensors, simplified wind/contact and ideal attitude remain limitations. Independent yaw refinement (AL-010) remains open. These are recorded simulations, not a live flight.</p></section>
    <section className="dg-panel"><h2>10 / Export this window</h2><p>Download numeric columns at 200 Hz for {start.toFixed(3)}–{end.toFixed(3)} s, inclusive. Phase codes: 0 other, 1 airborne descent, 2 contact, 3 motors-off.</p><button onClick={download}>Download window CSV</button></section>
    </>}
    <footer>AeroLoop · Flight diagnosis workspace · Original mission, pair and recovery limits preserved.</footer>
  </main>;
}
