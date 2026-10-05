import {lazy,Suspense,useCallback,useEffect,useMemo,useState} from 'react';
import {sampleAt} from './contracts.js';
import {evidenceBase,readVerified} from './load.js';
import {Plot} from './diagnosis.js';
import {validateDescentIndex,validateDescent,parseSelection,selectionHash,comparisonExport,windowMetrics,type DescentCase,type Descent,type Selection} from './descent-contract.js';
import './descent.css';
const Scene=lazy(()=>import('./scene.js'));
const fmt=(v:number|null|undefined,n=3)=>v==null?'Not measured':v.toFixed(n);
const series=(items:[string,number,string][])=>items.map(([name,column,color])=>({name,column,color}));
const VELOCITY=series([['Truth',3,'#68e2bc'],['Feedback',4,'#c19bff'],['Target',6,'#70baff']]);
const TERMS=series([['Position P',7,'#68e2bc'],['Velocity D',8,'#c19bff'],['Feedforward',9,'#70baff'],['Clipped sum',10,'#e7b16a']]);
const FORCE=series([['Requested',11,'#70baff'],['Realized rotor total',12,'#68e2bc'],['World vertical thrust',13,'#c19bff'],['Wind vertical',14,'#e7b16a']]);
const DISTURBANCE=series([['Learned anchor',21,'#c19bff'],['Applied estimate',22,'#68e2bc']]);
const MODES=['baseline','candidate'] as const;
export function DescentWorkspace({baseUrl,indexSha256}:{baseUrl:string;indexSha256:string}){
  const initial=useMemo(()=>parseSelection(location.hash,indexSha256),[indexSha256]);
  const [cases,setCases]=useState<DescentCase[]>([]),[selected,setSelected]=useState(initial?.id??'regression-p1-s0'),[data,setData]=useState<Descent|null>(null),[error,setError]=useState('');
  const [alignment,setAlignment]=useState<Selection['alignment']>(initial?.alignment??'time'),[time,setTime]=useState(initial?.time??40),[playing,setPlaying]=useState(false);
  const [show3d,setShow3d]=useState(false),[failed3d,setFailed3d]=useState(false),[visible,setVisible]=useState(!document.hidden),[share,setShare]=useState('');
  const fail=useCallback(()=>setFailed3d(true),[]);
  useEffect(()=>{const controller=new AbortController();setError('');
    void readVerified(new URL('index.json',evidenceBase(baseUrl,location.origin)),indexSha256,controller.signal,16384).then(v=>{if(!controller.signal.aborted)setCases(validateDescentIndex(v));}).catch(()=>{if(!controller.signal.aborted)setError('Verified study index unavailable. Prepare a descent export.');});return()=>controller.abort();
  },[baseUrl,indexSha256]);
  useEffect(()=>{setData(null);setPlaying(false);setError('');setFailed3d(false);setShare('');if(!cases.length)return;
    const controller=new AbortController(),entry=cases.find(c=>c.id===selected)!;
    void readVerified(new URL(entry.file,evidenceBase(baseUrl,location.origin)),entry.sha256,controller.signal,16*1024*1024).then(v=>{const pair=validateDescent(v,entry);if(!controller.signal.aborted)setData(pair);}).catch(()=>{if(!controller.signal.aborted)setError('Comparison failed integrity or consistency checks. No unverified flight is displayed.');});return()=>controller.abort();
  },[cases,selected,baseUrl]);
  const relative=alignment==='touchdown',canAlign=!!data&&MODES.every(m=>data[m].touchdown_s!==null);
  const offsets=useMemo(()=>MODES.map(m=>relative&&data?data[m].touchdown_s??0:0),[relative,data]);
  const start=data?Math.max(...offsets.map(o=>-o),relative?-1.5:Math.min(39,...MODES.map(m=>data[m].rows.at(-1)![0]-.005))):0;
  const end=data?Math.min(...MODES.map((m,i)=>data[m].rows.at(-1)![0]-offsets[i]),relative?1.5:44):50;
  useEffect(()=>{if(data){if(relative&&!canAlign)setAlignment('time');setTime(t=>Math.max(start,Math.min(end,t)));}},[data,relative,canAlign,start,end]);
  useEffect(()=>{const hide=()=>{setVisible(!document.hidden);if(document.hidden)setPlaying(false);};document.addEventListener('visibilitychange',hide);return()=>document.removeEventListener('visibilitychange',hide);},[]);
  useEffect(()=>{if(!playing||!visible)return;let id=0,previous=0;const tick=(now:number)=>{if(previous)setTime(t=>{const next=Math.min(end,t+Math.min((now-previous)/1000,.1)*.5);if(next>=end)setPlaying(false);return next;});previous=now;id=requestAnimationFrame(tick);};id=requestAnimationFrame(tick);return()=>cancelAnimationFrame(id);},[playing,visible,end]);
  const shown=useMemo(()=>data?MODES.map((m,i)=>data[m].rows.map(r=>[r[0]-offsets[i],...r.slice(1),r[4]-r[3]])):[],[data,offsets]);
  const seek=(t:number)=>{setPlaying(false);setTime(Math.max(start,Math.min(end,Math.round(t/.005)*.005)));setShare('');};
  function align(mode:Selection['alignment']){setPlaying(false);setAlignment(mode);setTime(mode==='time'?40:0);setShare('');}
  function shareSelection(){const hash=selectionHash({id:selected,alignment,time},indexSha256);history.replaceState(null,'',location.pathname+hash);setShare(location.origin+location.pathname+hash);}
  function download(){if(!data)return;const content=comparisonExport(data,start,end,alignment,indexSha256),url=URL.createObjectURL(new Blob([JSON.stringify(content,null,2)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`${selected}-${alignment}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  return <main className="dg ds"><header className="dg-header"><a href="/diagnosis.html">AEROLOOP / SIMULATION LAB</a><span>Recorded PhysX · simulation only</span></header>
    <div className="dg-hero"><div><p className="dg-eyebrow">PREDICTION EXPERIMENT / 02</p><h1>Watch the estimate.<br/>Measure the landing.</h1><p>A fading vertical disturbance estimate, compared with the original predictor.</p></div><div className="dg-summary"><strong>{cases.length||'—'}</strong><span>paired cases · two seed cohorts</span><strong>200 Hz</strong><span>full-rate numeric evidence</span><strong>0.2 s</strong><span>fixed decay time constant</span></div></div>
    {error&&<p className="dg-alert" role="alert">{error}</p>}
    <section className="dg-panel ds-controls"><label>Case<select aria-label="Case" value={selected} onChange={e=>{setSelected(e.target.value);setTime(alignment==='time'?40:0);}}>{cases.map(c=><option key={c.id} value={c.id}>{c.cohort} · seed {c.seed} · {c.profile==='sample-hold'?'no outage':'2 s outages'} · {c.baseline_status} → {c.candidate_status}</option>)}</select></label>
      <label>Alignment<select aria-label="Alignment" value={alignment} onChange={e=>align(e.target.value as Selection['alignment'])}><option value="time">Common simulation time</option><option value="touchdown" disabled={!canAlign}>Each flight’s touchdown</option></select></label>
      <button disabled={!data} onClick={()=>setShow3d(v=>!v)}>{show3d?'Hide 3D':'Enable paired 3D'}</button><button disabled={!data} onClick={shareSelection}>Share selection</button><button disabled={!data} onClick={download}>Export comparison JSON</button>
      {share&&<label className="ds-share">Selection link<input aria-label="Selection link" readOnly value={share} onFocus={e=>e.target.select()}/><small>Reopens this evidence version on a machine serving the same local demo.</small></label>}
    </section>
    {data&&<><section className="dg-panel ds-timeline"><div><button onClick={()=>{if(time>=end)setTime(start);setPlaying(v=>!v);}}>{playing?'Pause':'Play ½×'}</button><button onClick={()=>seek(time-.005)}>Previous step</button><button onClick={()=>seek(time+.005)}>Next step</button><strong data-testid="cursor">{fmt(time)} s {relative?'from each touchdown':'simulation time'}</strong></div><input aria-label="Comparison time" type="range" min={start} max={end} step=".005" value={time} onChange={e=>seek(Number(e.target.value))}/><p>{relative?'Each side uses its own contact time. Gust and outage phases no longer line up.':'Both flights share the same simulation time. Shading marks the scheduled outage.'} Numeric inspection uses the recorded 5 ms sample. 3D poses interpolate for display.</p></section>
      <div className="ds-pair">{MODES.map((mode,i)=>{const s=data[mode],absolute=Math.max(0,Math.min(s.rows.at(-1)![0],time+offsets[i])),r=s.rows[Math.floor((absolute+1e-9)/.005)],rows=shown[i],window=windowMetrics(s.rows,start+offsets[i],end+offsets[i]);
        const plot={rows,start,end,time,onSeek:seek,windows:data.profile==='sample-hold'?[]:[[18-offsets[i],20-offsets[i]],[40-offsets[i],42-offsets[i]]]};
        return <section key={mode} className="dg-panel ds-side" aria-label={mode}><h2>{mode==='baseline'?'Original predictor':'Vertical decay candidate'}</h2><p className={s.status==='failed'?'dg-alert':''}>Mission <strong>{s.status.toUpperCase()}</strong> · {s.failure_reason?.replaceAll('_',' ')??'all mission gates passed'}</p>
          <p>{s.outage?`Same-mode outage pair: ${s.outage.passed?'passed':'failed'} · recovery ${s.outage.recovery.filter(w=>w.passed).length}/2`:'No-outage reference · pair and recovery not applicable'}</p>
          {s.rows.length<10001&&<p className="dg-alert">Incomplete recording: {s.rows.length} / 10001 samples. Missing coverage is not a pass.</p>}
          <p className="ds-clock">Actual time <strong>{fmt(r[0])} s</strong> · touchdown {fmt(s.touchdown_s)} s · landed {fmt(s.landed_s)} s</p>
          {show3d&&!failed3d&&<div className="dg-scene"><Suspense fallback={<p>Loading 3D…</p>}><Scene sample={sampleAt(s.poses,absolute)} samples={s.poses} rotorFlight visible={visible} onFailure={fail}/></Suspense></div>}
          {failed3d&&<p>3D unavailable. Full-rate numeric diagnostics remain available.</p>}
          <h3>Velocity estimate · m/s</h3><p>Current error <strong>{fmt(r[4]-r[3],4)} m/s</strong> · window RMSE {fmt(window.vertical_velocity_error_rmse_m_s,4)} m/s ({window.samples} samples; {window.complete?'complete':'incomplete'}).</p>
          <Plot {...plot} title="Vertical velocity · m/s" series={VELOCITY}/><Plot {...plot} title="Feedback minus truth · m/s" series={series([['Velocity error',24,'#e7b16a']])}/>
          <Plot {...plot} title="Vertical controller terms · m/s²" series={TERMS}/><p>P {fmt(r[7])} + D {fmt(r[8])} + feedforward {fmt(r[9])} → clipped {fmt(r[10])} m/s² before gravity. Vertical integral gain is zero. Total thrust also depends on horizontal demand. Terms are zero while disarmed.</p>
          <Plot {...plot} title="Rotor lag and wind force · N" series={FORCE}/><p>Command {fmt(r[11])} N · realized {fmt(r[12])} N. A zero command does not imply instantaneous zero physical thrust.</p>
          <Plot {...plot} title="Vertical disturbance · m/s²" series={DISTURBANCE}/><p>Anchor {fmt(r[21],4)} · scale <strong>{fmt(r[20],4)}</strong> · applied {fmt(r[22],4)} m/s² · main capture age {fmt(r[23]*1000,0)} ms.</p>
          <section className="ds-contact" aria-label={`${mode} contact inspector`}><h3>Contact eligibility at {fmt(r[0])} s</h3><dl>
            <div><dt>Landing schedule ≥34 s</dt><dd>{r[0]>=34?'Yes':'No'}</dd></div><div><dt>Normal force &gt;0.1 N</dt><dd>{fmt(r[15])} N · {r[15]>.1?'yes':'no'}</dd></div>
            <div><dt>Clearance ≤0.015 m</dt><dd>{fmt(r[16],4)} m · {r[16]<=.015?'yes':'no'}</dd></div><div><dt>|Vertical speed| ≤0.2 m/s</dt><dd>{fmt(Math.abs(r[3]),4)} m/s · {Math.abs(r[3])<=.2?'yes':'no'}</dd></div>
            <div><dt>Eligible / continuous dwell</dt><dd>{r[17]?'Yes':'No'} · {fmt(r[18]*1000,0)} / 50 ms</dd></div><div><dt>Landed latch</dt><dd>{r[19]?'Set — motors commanded off':'Not set'}</dd></div></dl><p>Contact force reports the preceding physics interval. The ideal contact supervisor uses truth; the predictor never receives it.</p></section>
          <details><summary>Original gates and provenance</summary><div className="ds-table"><table><thead><tr><th>Gate</th><th>Value</th><th>Limit</th><th>Result</th></tr></thead><tbody>{s.gates.map(g=><tr key={g.id}><td>{g.label}</td><td>{fmt(g.value)} {g.unit}</td><td>{g.operator} {g.limit}</td><td>{g.status}</td></tr>)}</tbody></table></div><p>Source {s.provenance.source_commit} · clean recording</p><p>Samples SHA-256 {s.provenance.samples_sha256}</p>{s.outage&&<p>Same-mode peak separation {fmt(s.outage.peak_distance_m)} m · landing shift {fmt(s.outage.landed_change_s)} s · recovery times {s.outage.recovery.map(w=>fmt(w.time_s)).join(' / ')} s</p>}</details>
        </section>;
      })}</div></>}
    <footer className="dg-panel"><p>Six regression flights are retained; eighteen new flights cover both modes and the predeclared additional seeds. Development seed 73 is excluded. Full-rate mission, same-mode outage-pair and sustained-recovery gates remain unchanged. Window comparisons are descriptive.</p><p>The candidate is opt-in. Exponential decay is an engineering hypothesis, not calibrated wind estimation. Synthetic position/velocity channels, ideal attitude and contact supervision, simplified aerodynamics and unresolved yaw refinement limit these results. No hardware flight is validated.</p></footer>
  </main>;
}
