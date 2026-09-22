import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { historyAppend, positionError, validateLive, type LiveFrame, type LiveSample } from "./live-contract.js";
const Scene = lazy(() => import("./scene.js"));
const number = (v: number | undefined, digits=2) => v === undefined ? "—" : v.toFixed(digits);

export function LiveMonitor() {
  const [frame, setFrame] = useState<LiveFrame | null>(null);
  const [connection, setConnection] = useState("Connecting");
  const [history, setHistory] = useState<LiveSample[]>([]);
  const [sceneSamples, setSceneSamples] = useState<LiveSample[]>([]);
  const [show3d, setShow3d] = useState(false);
  const [visible, setVisible] = useState(!document.hidden);
  const [webglFailed, setWebglFailed] = useState(false);
  const failed = useCallback(() => setWebglFailed(true), []);
  const received = useRef(0);
  const [now, setNow] = useState(performance.now());
  useEffect(() => {
    let stopped = false, timer: ReturnType<typeof setTimeout>, request: AbortController | undefined;
    let key = "", samples: LiveSample[] = [];
    const poll = async () => {
      if (stopped) return;
      if (document.hidden) { timer = setTimeout(poll, 250); return; }
      request = new AbortController();
      const timeout = setTimeout(() => request?.abort(), 1500);
      try {
        const response = await fetch("/api/live", {cache: "no-store", signal: request.signal, credentials: "omit"});
        if (!response.ok) throw Error("Unavailable");
        const text = await response.text();
        if (text.length > 16384) throw Error("Oversized telemetry");
        const next = validateLive(JSON.parse(text));
        if (stopped) return;
        if (next.state === "waiting") { setFrame(null); setConnection("Waiting for worker"); }
        else {
          const nextKey = `${next.seed}/${next.physics_dt_s}`;
          if (key !== nextKey) { key = nextKey; samples = []; setHistory([]); setSceneSamples([]); }
          if (next.sample) {
            const empty = samples.length === 0;
            samples = historyAppend(samples, next.sample);
            setHistory(samples);
            if (empty) setSceneSamples([next.sample]);
          }
          received.current = performance.now(); setFrame(next); setConnection("Connected");
        }
      } catch { if (!stopped) setConnection("Disconnected — reconnecting"); }
      finally { clearTimeout(timeout); if (!stopped) timer = setTimeout(poll, 250); }
    };
    void poll();
    const clock = setInterval(()=>setNow(performance.now()), 250);
    const visibility = () => setVisible(!document.hidden);
    document.addEventListener("visibilitychange", visibility);
    return () => { stopped = true; clearTimeout(timer); clearInterval(clock); request?.abort(); document.removeEventListener("visibilitychange", visibility); };
  }, []);
  const s = frame?.sample;
  const age = frame ? frame.age_s + Math.max(0, now-received.current)/1000 : 0;
  const stale = frame && ["running", "verifying"].includes(frame.state) && (frame.stale || age > 1);
  const status = connection !== "Connected" ? connection : stale ? "Stale — worker updates stopped" :
    ({starting: "Starting physics", running: "Live · provisional", verifying: "Verifying recordings", completed: "Completed · recording verified", failed: "Failed · inspect local results"})[frame!.state];
  const tilt = s ? Math.acos(Math.max(-1, Math.min(1, 1-2*(s.quaternion_wxyz[1]**2+s.quaternion_wxyz[2]**2))))*180/Math.PI : 0;
  const error = s ? positionError(s) : undefined;
  const alarm = !!s && (error! > 1 || tilt > 25 || s.support_clearance_m! < -.003);
  const historyStart = history[0]?.time_s ?? 0;
  const historyEnd = history.at(-1)?.time_s ?? 1;
  const points = history.map(p=>`${10+580*(p.time_s-historyStart)/Math.max(.1,historyEnd-historyStart)},${140-120*Math.min(1.5,positionError(p))/1.5}`).join(" ");
  return <article className="al-live">
    <header><span className="al-eyebrow">AEROLOOP / PHYSICS LAB</span><h1>Flight test monitor</h1>
      <p>Native flight control · turbulent waypoint mission · Isaac PhysX</p>
      <p role="status" className={`al-live-status ${stale || alarm || frame?.state === "failed" ? "al-alert" : ""}`}>{status}</p>
    </header>
    <div className="al-live-grid">
      <section className="al-live-card"><h2>Measured flight</h2>
        <p>Seed {frame?.seed ?? "—"} · {s?.mission_phase?.replaceAll("_", " ") ?? "Awaiting first sample"}</p>
        <button onClick={()=>setShow3d(v=>!v)}>{show3d ? "Hide 3D" : "Enable 3D"}</button>
        {show3d && s && sceneSamples.length > 0 && !webglFailed && <Suspense fallback={<p>Loading 3D…</p>}><Scene sample={s} samples={sceneSamples} rotorFlight visible={visible} onFailure={failed}/></Suspense>}
        {webglFailed && <p>3D is unavailable. Numeric telemetry remains available.</p>}
        {!show3d && <p className="al-live-placeholder">Enable 3D to follow the simulated aircraft. No flight commands are sent from this page.</p>}
        <dl className="al-live-values">
          <div><dt>Simulation time</dt><dd>{number(s?.time_s)} s</dd></div>
          <div><dt>Tracking error</dt><dd>{number(error,3)} m</dd></div>
          <div><dt>Altitude</dt><dd>{number(s?.position_m[2],3)} m</dd></div>
          <div><dt>Tilt</dt><dd>{number(s ? tilt : undefined)}°</dd></div>
          <div><dt>Wind speed</dt><dd>{number(s ? Math.hypot(...s.wind_velocity_m_s!) : undefined)} m/s</dd></div>
          <div><dt>Ground support</dt><dd>{number(s?.contact_normal_force_n?.[2])} N</dd></div>
        </dl>
        {alarm && <p role="alert">Flight envelope exceeded. The final recording determines acceptance.</p>}
      </section>
      <section className="al-live-card"><h2>Controller and timing</h2>
        <dl className="al-live-values">
          <div><dt>Control / physics</dt><dd>200 / {frame ? Math.round(1/frame.physics_dt_s) : "—"} Hz</dd></div>
          <div><dt>Wall time</dt><dd>{number(frame?.elapsed_s)} s</dd></div>
          <div><dt>Real-time factor</dt><dd>{number(frame && s && frame.elapsed_s > 0 ? s.time_s/frame.elapsed_s : undefined)}×</dd></div>
          <div><dt>Current lag</dt><dd>{number(frame?.lag_s,3)} s</dd></div>
          <div><dt>Maximum lag</dt><dd>{number(frame?.max_lag_s,3)} s</dd></div>
          <div><dt>Sample age</dt><dd>{frame ? number(age,2) : "—"} s</dd></div>
          <div><dt>Late control samples (&gt;5 ms)</dt><dd>{frame?.late_steps ?? "—"}</dd></div>
          <div><dt>Pacing</dt><dd>{frame ? frame.paced ? "Wall clock" : "As fast as available" : "—"}</dd></div>
        </dl>
        <h3>Rotor thrust</h3>
        {(s?.rotor_thrust_n ?? [0,0,0,0]).map((v,i)=><div className="al-rotor" key={i}><label htmlFor={`rotor-${i}`}>R{i+1}</label><meter id={`rotor-${i}`} min={0} max={5} value={v}/><span>{number(v,3)} N</span></div>)}
        <p>Rate effort (roll / pitch / yaw): {s ? s.effort_normalized.map(v=>number(v,3)).join(" / ") : "—"}</p>
        <p>Measured rates: {s ? s.rates_rad_s.map(v=>number(v,3)).join(" / ") : "—"} rad/s</p>
        <p>Requested rates: {s ? s.rate_setpoint_rad_s.map(v=>number(v,3)).join(" / ") : "—"} rad/s</p>
        <p>Allocation scale: {number(s?.allocation_scale,3)}</p>
      </section>
    </div>
    <section className="al-live-card"><h2>Tracking error · recent received samples</h2>
      <svg className="al-live-chart" viewBox="0 0 600 160" role="img" aria-label="Recent position tracking error, zero to one point five metres"><line x1="10" y1="60" x2="590" y2="60" stroke="#db8d64" strokeDasharray="5 4"/><polyline points={points} fill="none" stroke="#007e80" strokeWidth="2"/></svg>
      <p>{number(historyStart,1)}–{number(historyEnd,1)} s · {history.length}/300 received samples · dashed line: 1 m · chart clipped at 1.5 m</p>
    </section>
    <footer><p>Live samples are provisional and may skip frames. Full recordings retain every 200 Hz control sample. Rendering and wall pacing do not change the physics timestep.</p>
      <p>Perfect state feedback, simplified wind/rotors/contact. The independent yaw-refinement finding remains open. This test does not validate hardware flight.</p></footer>
  </article>;
}
