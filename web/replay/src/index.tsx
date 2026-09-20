"use client";
import {
  Component,
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  sampleAt,
  tiltDegrees,
  validateWindPair,
  type Index,
  type Recording,
  type Vec3,
} from "./contracts.js";
import { evidenceBase, loadIndex, loadRecording } from "./load.js";

const Scene = lazy(() => import("./scene.js"));
class SceneBoundary extends Component<
  { children: ReactNode; onFailure: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onFailure();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}
const project = ([e, n, u]: Vec3) => [
  340 + 95 * e + 60 * n,
  300 + 18 * e - 35 * n - 100 * u,
];
const label = (text: string) => text.replaceAll("-", " ").replaceAll("_", " ");
const distance = (a: Vec3, b: Vec3) => Math.hypot(...a.map((v, i) => v - b[i]));
export type ReplayViewerProps = {
  baseUrl: string;
  indexSha256: string;
  title?: string;
};

/** Host-reviewed, same-origin recorded evidence. Never runs or controls a simulator. */
export function ReplayViewer({
  baseUrl,
  indexSha256,
  title = "Explore a physics recording",
}: ReplayViewerProps) {
  const id = useId(),
    root = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false),
    [seen, setSeen] = useState(false);
  const [reduced, setReduced] = useState(true),
    [playing, setPlaying] = useState(false);
  const [index, setIndex] = useState<Index | null>(null),
    [selected, setSelected] = useState(0);
  const [recording, setRecording] = useState<Recording | null>(null),
    [time, setTime] = useState(0);
  const [compare, setCompare] = useState(false),
    [reference, setReference] = useState<Recording | null>(null),
    [comparisonMessage, setComparisonMessage] = useState("");
  const [speed, setSpeed] = useState(1),
    [three, setThree] = useState(false),
    [gpuFailed, setGpuFailed] = useState(false);
  const [message, setMessage] = useState(
    "Recordings load when this panel is visible.",
  );
  const gpuFailure = useCallback(() => {
    setThree(false);
    setGpuFailed(true);
  }, []);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const motion = () => {
      setReduced(media.matches);
      setPlaying(false);
    };
    motion();
    media.addEventListener("change", motion);
    let intersecting = false;
    const visibility = () => {
      const active = intersecting && !document.hidden;
      setVisible(active);
      if (!active) setPlaying(false);
    };
    const observer = new IntersectionObserver(([entry]) => {
      intersecting = entry.isIntersecting;
      if (intersecting) setSeen(true);
      visibility();
    });
    observer.observe(root.current!);
    document.addEventListener("visibilitychange", visibility);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", visibility);
      media.removeEventListener("change", motion);
    };
  }, []);
  useEffect(() => {
    if (!seen) return;
    const abort = new AbortController();
    setIndex(null);
    setRecording(null);
    setReference(null);
    setCompare(false);
    setPlaying(false);
    setMessage("Verifying recording index...");
    async function read() {
      try {
        const result = await loadIndex(
          evidenceBase(baseUrl, location.href),
          indexSha256,
          abort.signal,
        );
        if (!abort.signal.aborted) {
          setSelected(0);
          setIndex(result);
        }
      } catch {
        if (!abort.signal.aborted)
          setMessage("Replay unavailable: index failed verification.");
      }
    }
    void read();
    return () => abort.abort();
  }, [seen, baseUrl, indexSha256]);
  useEffect(() => {
    if (!index) return;
    const abort = new AbortController();
    setRecording(null);
    setReference(null);
    setCompare(false);
    setPlaying(false);
    setTime(0);
    setMessage("Verifying selected recording...");
    async function read() {
      try {
        const result = await loadRecording(
          evidenceBase(baseUrl, location.href),
          index!,
          index!.runs[selected],
          abort.signal,
        );
        if (!abort.signal.aborted) {
          setRecording(result);
          setMessage(
            result.manifest.experiment === "isaac-quadrotor"
              ? "Checksums verified. Isaac PhysX quadrotor recording."
              : "Checksums verified. CPU simulation recording.",
          );
        }
      } catch {
        if (!abort.signal.aborted)
          setMessage("Replay unavailable: recording failed verification.");
      }
    }
    void read();
    return () => abort.abort();
  }, [index, selected, baseUrl]);
  const referenceEntry =
    recording?.entry.scenario === "turbulence-hold"
      ? index?.runs.find(
          (entry) =>
            entry.scenario === "turbulence-attitude-only" &&
            entry.seed === recording.entry.seed,
        )
      : undefined;
  useEffect(() => {
    setReference(null);
    setComparisonMessage("");
    if (!compare || !referenceEntry || !recording || !index) return;
    const abort = new AbortController();
    const contactFlight =
      recording?.manifest.model === "quadrotor-x-contact-v1";
    const missionMetrics = recording?.metrics.mission;
    const held = recording;
    setComparisonMessage("Verifying the matching reference...");
    loadRecording(
      evidenceBase(baseUrl, location.href),
      index,
      referenceEntry,
      abort.signal,
    )
      .then((result) => {
        const paired = validateWindPair(held, result);
        if (!abort.signal.aborted) {
          setReference(paired);
          setComparisonMessage(
            "Same seed, initial position, wind samples and source verified. Reference keeps altitude and attitude control; horizontal position hold is disabled.",
          );
        }
      })
      .catch(() => {
        if (!abort.signal.aborted)
          setComparisonMessage(
            "Comparison unavailable: matching evidence failed verification.",
          );
      });
    return () => abort.abort();
  }, [compare, referenceEntry, recording, index, baseUrl]);
  const duration = recording?.samples.at(-1)?.time_s ?? 0;
  useEffect(() => {
    if (!playing || !visible || !recording) return;
    let frame = 0,
      previous: number | null = null;
    const tick = (now: number) => {
      if (previous !== null) {
        const delta = Math.min(0.1, (now - previous) / 1000) * speed;
        setTime((t) => Math.min(duration, t + delta));
      }
      previous = now;
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, visible, recording, duration, speed]);
  useEffect(() => {
    if (time >= duration) setPlaying(false);
  }, [time, duration]);
  const sample = recording ? sampleAt(recording.samples, time) : null;
  const referenceSample =
    reference && recording?.entry.scenario === "turbulence-hold"
      ? sampleAt(reference.samples, time)
      : null;
  const plot = useMemo(() => {
    if (!recording) return null;
    const errors = recording.samples.map((s) =>
      distance(s.position_m, s.target_m),
    );
    const referenceErrors =
      reference?.samples.map((s) => distance(s.position_m, s.target_m)) ?? [];
    const max = Math.max(0.01, ...errors, ...referenceErrors) * 1.1;
    return {
      max,
      referencePoints: reference?.samples
        .map(
          (s, i) =>
            `${40 + (640 * s.time_s) / duration},${110 - (90 * referenceErrors[i]) / max}`,
        )
        .join(" "),
      points: recording.samples
        .map(
          (s, i) =>
            `${40 + (640 * s.time_s) / duration},${110 - (90 * errors[i]) / max}`,
        )
        .join(" "),
    };
  }, [recording, reference, duration]);
  const seek = (t: number) => {
    setPlaying(false);
    setTime(t);
  };
  const projection = useMemo(() => {
    if (recording?.manifest.model !== "quadrotor-x-wind-v1") return project;
    const points = recording.samples.flatMap((s) => [
      project(s.position_m),
      project(s.target_m),
    ]);
    const xs = points.map((p) => p[0]),
      ys = points.map((p) => p[1]);
    const left = Math.min(...xs),
      right = Math.max(...xs),
      top = Math.min(...ys),
      bottom = Math.max(...ys);
    const scale = Math.min(
      1,
      580 / Math.max(1, right - left),
      240 / Math.max(1, bottom - top),
    );
    return (value: Vec3) => {
      const [x, y] = project(value);
      return [
        360 + (x - (left + right) / 2) * scale,
        170 + (y - (top + bottom) / 2) * scale,
      ];
    };
  }, [recording]);
  const xy = sample ? projection(sample.position_m) : [340, 150],
    target = sample ? projection(sample.target_m) : [340, 150];
  const rotorFlight = recording?.manifest.experiment === "isaac-quadrotor";
  const windFlight = recording?.manifest.model === "quadrotor-x-wind-v1";
  const windMission =
    recording?.manifest.model === "quadrotor-x-contact-wind-v1";
  const contactFlight =
    recording?.manifest.model === "quadrotor-x-contact-v1" || windMission;
  const missionMetrics = recording?.metrics.mission;
  const held = recording?.entry.scenario === "turbulence-hold";
  const windMetrics = recording?.metrics.turbulence;
  const referenceRmse = reference?.metrics.turbulence?.wind_position_rmse_m;
  const reduction =
    windMetrics?.wind_position_rmse_m != null &&
    referenceRmse != null &&
    referenceRmse > 0
      ? 100 * (1 - windMetrics.wind_position_rmse_m / referenceRmse)
      : null;
  return (
    <section ref={root} className="al-replay" aria-labelledby={`${id}-title`}>
      <header className="al-heading">
        <div>
          <p className="al-kicker">AEROLOOP / RECORDED SIMULATION</p>
          <h2 id={`${id}-title`}>{title}</h2>
        </div>
        <span className="al-badge">
          {recording
            ? rotorFlight
              ? "Isaac PhysX"
              : "CPU physics"
            : "Physics replay"}
        </span>
      </header>
      <p>
        {rotorFlight
          ? "Four-rotor X drone with motor lag, thrust limits and a native C++ flight controller."
          : "Inspect a rigid-body experiment with a native rate controller."}{" "}
        These recorded trajectories are separate from the learned hover policy.
      </p>
      {contactFlight && (
        <div className="al-wind-intro">
          <strong>Takeoff / waypoint route / contact landing</strong>
          <p>
            Start with stopped motors, climb to 1.5 m, visit the north and east
            waypoints, return home and land on a physical floor.
          </p>
          <p>
            {windMission
              ? "Turbulent wind stays active through landing and after motor shutdown. A stronger gust acts during descent at 40-42 s. Trajectory feedforward and bounded integral feedback stabilize the route. "
              : "Calm air. "}
            Perfect state and illustrative contact parameters. The white
            wireframe shows the actual 0.4 x 0.4 x 0.1 m body collider; the
            rotor drawing is schematic.
          </p>
        </div>
      )}
      {windFlight && (
        <div className="al-wind-intro">
          <strong>
            {held
              ? "Position hold enabled"
              : "Reference: horizontal position hold disabled"}
          </strong>
          <p>
            Seeded turbulent wind applies drag and overturning moments in PhysX.
            Altitude and attitude control remain enabled in both experiments.
            Wind acts from 5–25 s, with a stronger gust at 12–14 s.
          </p>
          <p>
            Illustrative temporal wind and drag model; airborne start with
            perfect state.
          </p>
        </div>
      )}
      <div className="al-controls">
        <label>
          Experiment{" "}
          <select
            value={selected}
            disabled={!index}
            onChange={(e) => {
              setPlaying(false);
              setRecording(null);
              setReference(null);
              setCompare(false);
              setSelected(Number(e.target.value));
            }}
          >
            {index?.runs.map((entry, n) => (
              <option key={entry.run_id} value={n}>
                {label(entry.scenario)} / seed {entry.seed}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={!recording || gpuFailed}
          onClick={() => setThree((value) => !value)}
        >
          {three ? "Use schematic" : "Enable 3D view"}
        </button>
        {referenceEntry && (
          <button
            type="button"
            aria-pressed={compare}
            onClick={() => setCompare((value) => !value)}
          >
            {compare ? "Hide reference comparison" : "Compare reference"}
          </button>
        )}
      </div>
      <div
        className="al-stage"
        role="group"
        aria-label={
          sample
            ? `Recorded position: east ${sample.position_m[0].toFixed(2)}, north ${sample.position_m[1].toFixed(2)}, up ${sample.position_m[2].toFixed(2)} metres. Gold marks the target.`
            : "Simulation schematic. Recording not loaded."
        }
      >
        <svg
          viewBox="0 0 720 360"
          aria-hidden="true"
          className="al-schematic"
          style={{ visibility: three ? "hidden" : "visible" }}
        >
          <path
            d="M60 300H660 M120 325L540 210 M200 340L620 225 M180 270L530 340 M250 230L660 315"
            fill="none"
            stroke="#29465c"
          />
          <path
            d="M65 300h65m-65 0l42-36m-42 36v-65"
            fill="none"
            stroke="#b6c9d9"
          />
          <g fill="#b6c9d9" fontSize="13">
            <text x="134" y="305">
              E
            </text>
            <text x="110" y="260">
              N
            </text>
            <text x="60" y="228">
              U
            </text>
          </g>
          {recording && (
            <polyline
              points={recording.samples
                .map((s) => projection(s.position_m).join(","))
                .join(" ")}
              fill="none"
              stroke="#67e8f9"
              strokeWidth="2"
              opacity=".5"
            />
          )}
          <circle
            cx={target[0]}
            cy={target[1]}
            r="10"
            stroke="#fbbf24"
            strokeWidth="2"
            fill="none"
          />
          <g
            transform={`translate(${xy[0]} ${xy[1]})`}
            stroke="#67e8f9"
            strokeWidth="4"
          >
            <path d="M-20-10L20 10M-20 10L20-10" />
            <circle r="5" fill="#67e8f9" />
          </g>
        </svg>
        {three && sample && (
          <SceneBoundary onFailure={gpuFailure}>
            <Suspense
              fallback={<p className="al-overlay">Loading 3D view...</p>}
            >
              <Scene
                sample={sample}
                samples={recording!.samples}
                rotorFlight={rotorFlight}
                visible={visible}
                onFailure={gpuFailure}
              />
            </Suspense>
          </SceneBoundary>
        )}
        <span className="al-stage-note">
          {three && windMission
            ? "White collider / violet wind / orange drag / pink support"
            : three && contactFlight
              ? "White collider / gold route / green thrust / pink ground support"
              : three && windFlight
                ? "Violet wind / orange drag / green thrust · camera follows drone"
                : three
                  ? "3D attitude / gold nose and target"
                  : windFlight
                    ? "Position schematic fits full path / gold target"
                    : "Position schematic / gold target"}
        </span>
      </div>
      {sample?.mission_phase && (
        <dl
          className="al-wind-readings"
          aria-label="Mission and ground contact"
        >
          <div>
            <dt>Mission phase</dt>
            <dd>{label(sample.mission_phase)}</dd>
          </div>
          <div>
            <dt>Normal ground support</dt>
            <dd>{sample.contact_normal_force_n![2].toFixed(2)} N</dd>
          </div>
          <div>
            <dt>Collider clearance</dt>
            <dd>{(sample.support_clearance_m! * 1000).toFixed(1)} mm</dd>
          </div>
          <div>
            <dt>Motors</dt>
            <dd>
              {["grounded", "landed"].includes(sample.mission_phase)
                ? "Disarmed"
                : "Armed"}
            </dd>
          </div>
        </dl>
      )}
      {sample?.wind_velocity_m_s && (
        <dl className="al-wind-readings" aria-label="Wind and stabilization">
          <div>
            <dt>Wind phase</dt>
            <dd>
              {windMission
                ? time < 1
                  ? "Wind ramp"
                  : time >= 40 && time < 42
                    ? "Landing gust"
                    : "Turbulent wind"
                : time < 5
                  ? "Calm"
                  : time >= 25
                    ? "Recovery in calm air"
                    : time >= 12 && time < 14
                      ? "Stronger gust"
                      : "Turbulent wind"}
            </dd>
          </div>
          <div>
            <dt>Wind speed</dt>
            <dd>{Math.hypot(...sample.wind_velocity_m_s).toFixed(2)} m/s</dd>
          </div>
          <div>
            <dt>Drag force</dt>
            <dd>{Math.hypot(...sample.external_force_n!).toFixed(2)} N</dd>
          </div>
          <div>
            <dt>Drone tilt</dt>
            <dd>{tiltDegrees(sample.quaternion_wxyz).toFixed(2)}°</dd>
          </div>
        </dl>
      )}
      {sample?.rotor_thrust_n && (
        <div className="al-rotors" aria-label="Applied rotor thrust">
          {sample.rotor_thrust_n.map((thrust, i) => (
            <label key={i}>
              {["Front left", "Rear left", "Rear right", "Front right"][i]}
              <meter
                min={0}
                max={5}
                value={thrust}
                aria-label={`Rotor ${i + 1} thrust`}
              />
              <span>{thrust.toFixed(3)} N</span>
            </label>
          ))}
          <p>
            Applied thrust per physics interval, 0 to 5 N per rotor. Display
            values are interpolated.
          </p>
        </div>
      )}
      {gpuFailed && (
        <p>
          3D is unavailable. The schematic and recording controls remain
          available.
        </p>
      )}
      <div className="al-controls">
        <button
          type="button"
          disabled={!recording || !visible}
          onClick={() => {
            if (time >= duration) setTime(0);
            setPlaying((value) => !value);
          }}
        >
          {playing ? "Pause replay" : "Play replay"}
        </button>
        <button type="button" disabled={!recording} onClick={() => seek(0)}>
          Restart
        </button>
        <label>
          Speed{" "}
          <select
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
          >
            <option value="0.5">0.5x</option>
            <option value="1">1x</option>
            <option value="2">2x</option>
          </select>
        </label>
        <span className="al-clock" aria-live="off">
          {time.toFixed(2)} / {duration.toFixed(2)} s
        </span>
      </div>
      <label className="al-scrub">
        Replay time
        <input
          type="range"
          min="0"
          max={duration || 1}
          step="0.01"
          value={time}
          disabled={!recording}
          onChange={(e) => seek(Number(e.target.value))}
          aria-valuetext={`${time.toFixed(2)} seconds`}
        />
      </label>
      {plot && (
        <div>
          <div className="al-plot-labels">
            <span>
              Position error: 0 to {plot.max.toFixed(2)} m
              {reference ? " · cyan: hold / orange: reference" : ""}
            </span>
          </div>
          <svg
            className="al-plot"
            viewBox="0 0 720 120"
            preserveAspectRatio="none"
            role="img"
            aria-label="Position error over time. Plot uses display samples; summary RMSE uses full-resolution data."
          >
            {windFlight && (
              <rect
                x={40 + (640 * 5) / duration}
                y="20"
                width={(640 * 20) / duration}
                height="90"
                fill="#a855f7"
                opacity=".08"
              />
            )}
            <path
              d="M40 20v90h640"
              stroke="currentColor"
              fill="none"
              opacity=".4"
            />
            <polyline
              points={plot.points}
              stroke="#0891b2"
              strokeWidth="2"
              fill="none"
            />
            {plot.referencePoints && (
              <polyline
                points={plot.referencePoints}
                stroke="#ea580c"
                strokeWidth="2"
                strokeDasharray="6 3"
                fill="none"
              />
            )}
            <path
              d={`M${40 + (640 * time) / duration} 20v90`}
              stroke="currentColor"
            />
          </svg>
          <div className="al-plot-labels">
            <span>0 s</span>
            <span>{duration} s</span>
          </div>
        </div>
      )}
      {compare && <p className="al-comparison-message">{comparisonMessage}</p>}
      {referenceSample && sample && windMetrics && (
        <div className="al-comparison" aria-label="Stabilization comparison">
          <strong>
            {reduction === null
              ? "RMSE comparison unavailable"
              : `${reduction.toFixed(1)}% less position error during wind`}
          </strong>
          <p>
            5–25 s full-resolution RMSE: hold{" "}
            {windMetrics!.wind_position_rmse_m?.toFixed(3)} m; reference{" "}
            {referenceRmse?.toFixed(3)} m.
          </p>
          <p>
            At {time.toFixed(2)} s: hold{" "}
            {distance(sample!.position_m, sample!.target_m).toFixed(3)} m;
            reference{" "}
            {distance(
              referenceSample.position_m,
              referenceSample.target_m,
            ).toFixed(3)}{" "}
            m from target.
          </p>
        </div>
      )}
      <div className="al-controls" aria-label="Recorded events">
        {recording?.events.map((event, i) => (
          <button type="button" key={i} onClick={() => seek(event.time_s)}>
            {event.time_s}s / {label(event.type)}
          </button>
        ))}
      </div>
      <p role="status">{message}</p>
      {recording && (
        <>
          <dl className="al-metrics">
            <div>
              <dt>Position error now</dt>
              <dd>
                {sample
                  ? distance(sample.position_m, sample.target_m).toFixed(3)
                  : "-"}{" "}
                m
              </dd>
            </div>
            <div>
              <dt>Full-resolution RMSE</dt>
              <dd>
                {recording.metrics.position_rmse_m === null
                  ? "Unavailable"
                  : `${recording.metrics.position_rmse_m.toPrecision(4)} m`}
              </dd>
            </div>
            <div>
              <dt>Recorded outcome</dt>
              <dd>
                {windFlight && !held && recording.entry.status === "passed"
                  ? "Reference completed (position hold disabled)"
                  : recording.entry.status}
              </dd>
            </div>
          </dl>
          {missionMetrics && (
            <p aria-label="Mission measurements">
              Waypoints reached:{" "}
              {
                missionMetrics.waypoint_reached_s.filter((t) => t !== null)
                  .length
              }
              /4 (within {missionMetrics.waypoint_band_m ?? 0.15} m for 1 s).
              Touchdown:{" "}
              {missionMetrics.touchdown_time_s?.toFixed(3) ?? "not reached"} s;{" "}
              pre-contact descent speed:{" "}
              {missionMetrics.touchdown_descent_speed_m_s?.toFixed(3) ??
                "unavailable"}{" "}
              m/s. Maximum penetration:{" "}
              {(missionMetrics.max_penetration_m * 1000).toFixed(2)} mm. Contact
              readings use the last measured sample; full-rate measurements
              determine the outcome.
            </p>
          )}
          {windMission && missionMetrics && (
            <p aria-label="Wind landing measurements">
              Pre-contact horizontal speed:{" "}
              {missionMetrics.touchdown_horizontal_speed_m_s?.toFixed(3) ??
                "unavailable"}{" "}
              m/s. Final mean vertical force-balance error:{" "}
              {missionMetrics.final_support?.mean_vertical_balance_error_n.toFixed(
                3,
              ) ?? "unavailable"}{" "}
              N, including wind and the preceding rotor interval. Normal support
              excludes friction and need not equal weight in vertical wind.
            </p>
          )}
          {windMetrics && (
            <p>
              Wind-window RMSE:{" "}
              {windMetrics.wind_position_rmse_m?.toFixed(3) ?? "unavailable"} m.
              Peak tilt: {windMetrics.peak_tilt_deg.toFixed(2)}°. Recovery after
              wind ends:{" "}
              {windMetrics.recovery_time_s === null
                ? "did not recover"
                : `${windMetrics.recovery_time_s.toFixed(3)} s`}
              , within 0.10 m for 2 s.
            </p>
          )}
          <p>
            {recording.metrics.samples.toLocaleString("en-US")} full-resolution
            samples. RMSE window:{" "}
            {recording.metrics.measurement_window_s.join(" to ")} s. Source{" "}
            {recording.manifest.source_commit.slice(0, 8)}
            {recording.manifest.source_dirty ? " + recorded changes" : ""}.
            {recording.manifest.failure_reason
              ? ` Failure: ${label(recording.manifest.failure_reason)}.`
              : ""}
          </p>
          <a href={`${baseUrl}${recording.entry.run_id}/manifest.json`}>
            Inspect recording provenance
          </a>
        </>
      )}
      <p className="al-footnote">
        {reduced
          ? "Reduced motion is enabled. Scrub directly or explicitly start playback. "
          : ""}
        Playback pauses when hidden or offscreen. No hardware flight or
        simulator commands.
      </p>
    </section>
  );
}
