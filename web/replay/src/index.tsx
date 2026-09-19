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
          setMessage("Checksums verified. CPU simulation recording.");
        }
      } catch {
        if (!abort.signal.aborted)
          setMessage("Replay unavailable: recording failed verification.");
      }
    }
    void read();
    return () => abort.abort();
  }, [index, selected, baseUrl]);
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
  const plot = useMemo(() => {
    if (!recording) return null;
    const errors = recording.samples.map((s) =>
      distance(s.position_m, s.target_m),
    );
    const max = Math.max(0.01, ...errors) * 1.1;
    return {
      max,
      points: recording.samples
        .map(
          (s, i) =>
            `${40 + (640 * s.time_s) / duration},${110 - (90 * errors[i]) / max}`,
        )
        .join(" "),
    };
  }, [recording, duration]);
  const seek = (t: number) => {
    setPlaying(false);
    setTime(t);
  };
  const xy = sample ? project(sample.position_m) : [340, 150],
    target = sample ? project(sample.target_m) : [340, 150];
  return (
    <section ref={root} className="al-replay" aria-labelledby={`${id}-title`}>
      <header className="al-heading">
        <div>
          <p className="al-kicker">AEROLOOP / RECORDED SIMULATION</p>
          <h2 id={`${id}-title`}>{title}</h2>
        </div>
        <span className="al-badge">CPU physics</span>
      </header>
      <p>
        Inspect an ideal body-wrench model with a native rate controller. These
        trajectories are separate from the Isaac learning experiment.
      </p>
      <div className="al-controls">
        <label>
          Experiment{" "}
          <select
            value={selected}
            disabled={!index}
            onChange={(e) => {
              setPlaying(false);
              setRecording(null);
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
      </div>
      <div
        className="al-stage"
        role="img"
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
                .map((s) => project(s.position_m).join(","))
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
              <Scene sample={sample} visible={visible} onFailure={gpuFailure} />
            </Suspense>
          </SceneBoundary>
        )}
        <span className="al-stage-note">
          {three
            ? "3D attitude / gold nose and target"
            : "Position schematic / gold target"}
        </span>
      </div>
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
        <svg
          className="al-plot"
          viewBox="0 0 720 140"
          role="img"
          aria-label="Position error over time. Plot uses display samples; summary RMSE uses full-resolution data."
        >
          <text x="5" y="14" fill="currentColor" fontSize="12">
            {plot.max.toFixed(2)} m
          </text>
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
          <path
            d={`M${40 + (640 * time) / duration} 20v90`}
            stroke="currentColor"
          />
          <text x="40" y="134" fill="currentColor" fontSize="12">
            0 s
          </text>
          <text x="640" y="134" fill="currentColor" fontSize="12">
            {duration} s
          </text>
        </svg>
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
              <dd>{recording.entry.status}</dd>
            </div>
          </dl>
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
