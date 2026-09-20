const ID = /^(cpu|isaac)-(hover|position-step|lateral-force-pulse|turbulence-hold|turbulence-attitude-only|ground-mission|ground-mission-wind)-\d{1,10}-[0-9a-f]{12}$/;
const finiteVector = (v, n) => Array.isArray(v) && v.length === n && v.every(x => typeof x === "number" && Number.isFinite(x));
export function validateReplay(data) {
  if (!data || typeof data.run_id !== "string" || data.schema_version !== (data.run_id.startsWith("isaac-ground-mission-wind-") ? 5 : data.run_id.startsWith("isaac-ground-mission-") ? 4 : data.run_id.startsWith("isaac-turbulence-") ? 3 : data.run_id.startsWith("isaac-") ? 2 : 1) || data.kind !== "recorded_simulation" || !ID.test(data.run_id) || (data.run_id.startsWith("cpu-turbulence-") || data.run_id.startsWith("cpu-ground-mission-")) || !Array.isArray(data.samples) || data.samples.length < 2 || data.samples.length > 10000) throw Error("Invalid replay contract");
  let previous = -1;
  for (const sample of data.samples) {
    if (!Number.isFinite(sample.time_s) || sample.time_s < 0 || sample.time_s <= previous || sample.time_s > 120 || !finiteVector(sample.position_m, 3) || !finiteVector(sample.target_m, 3) || !finiteVector(sample.quaternion_wxyz, 4) || Math.abs(Math.hypot(...sample.quaternion_wxyz)-1) > 1e-6) throw Error("Invalid replay sample");
    previous = sample.time_s;
  }
  return data;
}
export function sampleAt(samples, time) {
  if (!Number.isFinite(time)) throw Error("Invalid replay time");
  let low = 0, high = samples.length-1;
  while (low+1 < high) { const middle = (low+high)>>1; if (samples[middle].time_s <= time) low = middle; else high = middle; }
  if (time >= samples[high].time_s) low = high;
  const a = samples[low], b = samples[Math.min(low+1, samples.length-1)];
  const mix = b.time_s === a.time_s ? 0 : Math.max(0, Math.min(1, (time-a.time_s)/(b.time_s-a.time_s)));
  return {position: a.position_m.map((v,i) => v+(b.position_m[i]-v)*mix), target: a.target_m, index: low};
}
const distance = (a,b) => Math.hypot(...a.map((v,i)=>v-b[i]));
const project = ([e,n,u]) => [400+100*e+75*n, 335+22*e-40*n-100*u];

async function start() {
  const $ = id => document.getElementById(id);
  let index, replay, runMetrics, manifest, time = 0, duration = 1, playing = false, previous = null, serial = 0;
  async function read(name, verified = true) {
    const response = await fetch(name, {cache:"no-store"});
    if (!response.ok) throw Error("Evidence file unavailable");
    const text = await response.text();
    if (text.length > 32*1024*1024) throw Error("Evidence exceeds size limit");
    if (verified) {
      const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
      const hash = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2,"0")).join("");
      if (hash !== index.checksums[name]) throw Error("Evidence checksum mismatch");
    }
    return JSON.parse(text);
  }
  function pause() { playing = false; previous = null; $("play").textContent = "Play replay"; }
  function draw() {
    if (!replay) return;
    const sample = sampleAt(replay.samples, time);
    const [x,y] = project(sample.position), [tx,ty] = project(sample.target);
    $("drone").setAttribute("transform", `translate(${x} ${y})`);
    $("target").setAttribute("transform", `translate(${tx} ${ty})`);
    $("trail").setAttribute("points", [...replay.samples.slice(0,sample.index+1).map(s=>project(s.position_m).join(",")), `${x},${y}`].join(" "));
    $("cursor").setAttribute("x1", 50+930*time/duration); $("cursor").setAttribute("x2", 50+930*time/duration);
    $("time").value = time; $("clock").textContent = `${time.toFixed(2)} / ${duration.toFixed(2)} s`;
    $("error").textContent = `${distance(sample.position,sample.target).toFixed(3)} m`;
  }
  function saveState() { history.replaceState(null,"",`#run=${$("experiment").selectedIndex}&t=${time.toFixed(2)}`); }
  async function choose(entry, initialTime = 0) {
    const request = ++serial; pause(); replay = null;
    $("play").disabled = $("restart").disabled = $("time").disabled = true;
    $("message").textContent = "Verifying recording checksums…";
    const [r,m,e,f] = await Promise.all(["replay.json","metrics.json","events.json","manifest.json"].map(name=>read(`${entry.run_id}/${name}`)));
    if (request !== serial) return;
    validateReplay(r);
    if (r.run_id !== entry.run_id || f.run_id !== entry.run_id || f.fixture !== false || f.kind !== "recorded_simulation") throw Error("Recording identity mismatch");
    const flight = r.schema_version >= 2, wind = r.schema_version === 3, contact = [4,5].includes(r.schema_version), windMission = r.schema_version === 5;
    if (f.schema_version !== r.schema_version || f.experiment !== (flight ? "isaac-quadrotor" : "cpu-rigid-body") || f.model !== (windMission ? "quadrotor-x-contact-wind-v1" : contact ? "quadrotor-x-contact-v1" : wind ? "quadrotor-x-wind-v1" : flight ? "quadrotor-x-v1" : "ideal-body-wrench-v1")) throw Error("Recording backend mismatch");
    $("backend").textContent = flight ? "Isaac PhysX / four-rotor X" : "CPU physics / ideal body wrench";
    $("model-name").textContent = flight ? "Four rotors with thrust limits and lag" : "Ideal body wrench";
    $("model-boundary").textContent = flight ? "A 1 kg X quadrotor with bounded per-rotor thrust, first-order motor lag and perfect state. No propeller aerodynamics, battery, estimator or contact model. Initial conditions are airborne." : "Perfect state, ideal thrust and body moments. No individual motor dynamics, estimator, drag or contact model. Initial conditions are airborne.";
    if (contact) $("model-boundary").textContent = "Calm takeoff, waypoint route and contact-latched landing on a physical floor. Measured normal support, cuboid collision geometry and stopped motors. Illustrative contact parameters and perfect state.";
    if (windMission) $("model-boundary").textContent = "Turbulent takeoff, waypoint route and contact landing with trajectory feedforward and integral feedback. Wind remains active during descent and after disarm. Illustrative drag/contact parameters, perfect state.";
    if (wind) $("model-boundary").textContent = "Seeded temporal turbulent wind with relative-velocity drag and pressure-centre torque. Illustrative parameters; perfect state and airborne start. The attitude-only reference disables horizontal position hold and can drift far from target.";
    replay = r; runMetrics = m; manifest = f; duration = replay.samples.at(-1).time_s;
    time = Math.max(0,Math.min(duration,Number.isFinite(initialTime)?initialTime:0));
    $("time").max = duration;
    $("play").disabled = $("restart").disabled = $("time").disabled = false;
    $("whole-trail").setAttribute("points", replay.samples.map(s=>project(s.position_m).join(",")).join(" "));
    $("rmse").textContent = runMetrics.position_rmse_m === null ? "Unavailable" : `${runMetrics.position_rmse_m > 0 && runMetrics.position_rmse_m < .0001 ? runMetrics.position_rmse_m.toExponential(2) : runMetrics.position_rmse_m.toFixed(4)} m`;
    $("seed").textContent = manifest.seed; $("outcome").textContent = manifest.status;
    if (entry.scenario === "turbulence-attitude-only" && manifest.status === "passed") $("outcome").textContent = "Reference completed; position hold disabled";
    $("revision").textContent = `${manifest.source_commit.slice(0,8)}${manifest.source_dirty ? " + changes" : ""}`;
    $("message").textContent = flight ? "Checksums verified · Isaac PhysX quadrotor" : "Checksums verified · CPU simulation";
    $("record-link").href = `${entry.run_id}/manifest.json`;
    $("summary").textContent = `${entry.scenario.replaceAll("-"," ")}, seed ${manifest.seed}: ${manifest.status}. ${runMetrics.samples.toLocaleString()} full-resolution samples over ${duration.toFixed(1)} seconds. RMSE uses the ${runMetrics.measurement_window_s.join("–")} s measurement window. ${manifest.failure_reason ? `Failure: ${manifest.failure_reason}.` : ""}`;
    $("events").replaceChildren();
    for (const event of e) {
      const button = document.createElement("button"); button.textContent = `${event.time_s}s · ${event.type.replaceAll("_"," ")}`;
      button.addEventListener("click",()=>{pause(); time=event.time_s; draw(); saveState();}); $("events").append(button);
    }
    const errors = replay.samples.map(s=>distance(s.position_m,s.target_m));
    const max = Math.max(.01,...errors)*1.1;
    $("error-line").setAttribute("points", replay.samples.map((s,i)=>`${50+930*s.time_s/duration},${150-130*errors[i]/max}`).join(" "));
    $("plot-max").textContent = max.toFixed(2); $("plot-end").textContent = `${duration} s`;
    draw();
  }
  function fail(error) { pause(); replay=null; $("play").disabled=$("restart").disabled=$("time").disabled=true; $("message").textContent = `Replay unavailable: ${error.message}`; }
  $("play").addEventListener("click",()=>{if(!replay)return; if(playing){pause();saveState();} else{if(time>=duration)time=0;playing=true;previous=null;$("play").textContent="Pause replay";}});
  $("restart").addEventListener("click",()=>{pause();time=0;draw();saveState();});
  $("time").addEventListener("input",()=>{pause();time=Number($("time").value);draw();});
  $("time").addEventListener("change",saveState);
  $("experiment").addEventListener("change",()=>choose(index.runs[$("experiment").selectedIndex]).then(saveState).catch(fail));
  function tick(now) { if(playing && replay){ if(previous!==null)time=Math.min(duration,time+Math.min(.1,(now-previous)/1000)*Number($("speed").value));previous=now;draw();if(time>=duration){pause();saveState();}}requestAnimationFrame(tick); }
  requestAnimationFrame(tick);
  try {
    index = await read("index.json",false);
    if(!((index.schema_version===1 && index.isaac_validated===false) || ([2,3,4,5].includes(index.schema_version) && index.learning_validated===false && !("isaac_validated" in index))) || index.kind!=="recorded_simulation" || index.release_status!=="research_preview" || !Array.isArray(index.runs) || !index.runs.length || index.runs.length>30 || !index.checksums || index.runs.some(r=>!ID.test(r.run_id) || (index.schema_version===1 && !r.run_id.startsWith("cpu-")) || (r.run_id.includes("-ground-mission-wind-") && index.schema_version!==5) || (r.run_id.includes("-ground-mission-") && (![4,5].includes(index.schema_version) || !r.run_id.startsWith("isaac-"))) || (r.run_id.includes("-turbulence-") && (![3,4,5].includes(index.schema_version) || !r.run_id.startsWith("isaac-"))))) throw Error("Invalid preview index");
    $("experiment").replaceChildren();
    for (const entry of index.runs) { const option=document.createElement("option");option.textContent=`${entry.scenario.replaceAll("-"," ")} · seed ${entry.seed}`;$("experiment").append(option); }
    const params = new URLSearchParams(location.hash.slice(1));
    const selected = Number(params.get("run") ?? 0);
    $("experiment").selectedIndex = Number.isInteger(selected) && selected >= 0 && selected < index.runs.length ? selected : 0;
    $("experiment").disabled=false;
    await choose(index.runs[$("experiment").selectedIndex],Number(params.get("t")??0));
  } catch(error) { fail(error); }
}
if (typeof document !== "undefined") start();
