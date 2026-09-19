export type Vec3 = [number, number, number];
export type Wxyz = [number, number, number, number];
export type Sample = {
  time_s: number;
  position_m: Vec3;
  target_m: Vec3;
  quaternion_wxyz: Wxyz;
};
export type Entry = {
  run_id: string;
  scenario: string;
  seed: number;
  status: "passed" | "failed";
};
export type Index = { runs: Entry[]; checksums: Record<string, string> };
export type Recording = {
  entry: Entry;
  samples: Sample[];
  events: { time_s: number; type: string }[];
  metrics: {
    position_rmse_m: number | null;
    samples: number;
    measurement_window_s: [number, number];
  };
  manifest: {
    source_commit: string;
    source_dirty: boolean;
    failure_reason: string | null;
  };
};
export const HASH = /^[0-9a-f]{64}$/;
const ID =
  /^cpu-(hover|position-step|lateral-force-pulse)-\d{1,10}-[0-9a-f]{12}$/;
const finite = (n: unknown): n is number =>
  typeof n === "number" && Number.isFinite(n);
const vector = (v: unknown, n: number) =>
  Array.isArray(v) && v.length === n && v.every(finite);
function assertContract(value: unknown): asserts value {
  if (!value) throw Error("Invalid recording contract");
}
function object(value: unknown): Record<string, unknown> {
  assertContract(value && typeof value === "object" && !Array.isArray(value));
  return value as Record<string, unknown>;
}
export function validateIndex(value: unknown): Index {
  const data = object(value);
  assertContract(
    data.schema_version === 1 &&
      data.kind === "recorded_simulation" &&
      data.release_status === "research_preview" &&
      data.isaac_validated === false,
  );
  assertContract(
    Array.isArray(data.runs) && data.runs.length > 0 && data.runs.length <= 30,
  );
  const seen = new Set<string>();
  const checksums = object(data.checksums);
  for (const raw of data.runs) {
    const run = object(raw);
    assertContract(
      typeof run.run_id === "string" &&
        ID.test(run.run_id) &&
        !seen.has(run.run_id),
    );
    assertContract(
      ["hover", "position-step", "lateral-force-pulse"].includes(
        String(run.scenario),
      ) &&
        Number.isInteger(run.seed) &&
        Number(run.seed) >= 0 &&
        Number(run.seed) <= 2147483647,
    );
    assertContract(
      run.run_id.startsWith(`cpu-${run.scenario}-${run.seed}-`) &&
        ["passed", "failed"].includes(String(run.status)),
    );
    seen.add(run.run_id);
    for (const name of [
      "replay",
      "manifest",
      "metrics",
      "events",
      "config",
      "samples",
    ]) {
      assertContract(
        typeof checksums[`${run.run_id}/${name}.json`] === "string" &&
          HASH.test(checksums[`${run.run_id}/${name}.json`] as string),
      );
    }
  }
  return data as unknown as Index;
}
export function validateRecording(
  entry: Entry,
  replayValue: unknown,
  manifestValue: unknown,
  metricsValue: unknown,
  eventsValue: unknown,
): Recording {
  const replay = object(replayValue),
    manifest = object(manifestValue),
    metrics = object(metricsValue);
  assertContract(
    replay.schema_version === 1 &&
      replay.kind === "recorded_simulation" &&
      replay.run_id === entry.run_id,
  );
  assertContract(
    manifest.schema_version === 1 &&
      manifest.run_id === entry.run_id &&
      manifest.fixture === false &&
      manifest.kind === "recorded_simulation",
  );
  assertContract(
    manifest.experiment === "cpu-rigid-body" &&
      manifest.model === "ideal-body-wrench-v1" &&
      manifest.controller === "rate-pid-v1",
  );
  assertContract(
    manifest.world_frame === "ENU" &&
      manifest.body_frame === "FLU" &&
      manifest.quaternion_order === "wxyz" &&
      manifest.units === "SI",
  );
  assertContract(
    manifest.scenario === entry.scenario &&
      manifest.seed === entry.seed &&
      manifest.status === entry.status,
  );
  assertContract(
    typeof manifest.source_commit === "string" &&
      /^[0-9a-f]{40}$/.test(manifest.source_commit) &&
      typeof manifest.source_dirty === "boolean",
  );
  assertContract(
    [
      null,
      "model_bounds_exceeded",
      "hover_threshold",
      "recovery_threshold",
      "step_did_not_settle",
    ].includes(manifest.failure_reason as string | null),
  );
  assertContract(
    (entry.status === "passed") === (manifest.failure_reason === null),
  );
  assertContract(
    Array.isArray(replay.samples) &&
      replay.samples.length >= 2 &&
      replay.samples.length <= 10000,
  );
  let previous = -1;
  for (const value of replay.samples) {
    const s = object(value);
    assertContract(
      finite(s.time_s) &&
        s.time_s > previous &&
        s.time_s >= 0 &&
        s.time_s <= 120,
    );
    assertContract(
      vector(s.position_m, 3) &&
        vector(s.target_m, 3) &&
        vector(s.quaternion_wxyz, 4),
    );
    assertContract(
      Math.abs(Math.hypot(...(s.quaternion_wxyz as number[])) - 1) <= 1e-6,
    );
    assertContract(
      (s.position_m as number[]).every((n) => Math.abs(n) <= 1000) &&
        (s.target_m as number[]).every((n) => Math.abs(n) <= 1000),
    );
    previous = s.time_s;
  }
  assertContract(replay.samples[0].time_s === 0);
  assertContract(
    metrics.position_rmse_m === null ||
      (finite(metrics.position_rmse_m) && metrics.position_rmse_m >= 0),
  );
  assertContract(
    Number.isInteger(metrics.samples) &&
      Number(metrics.samples) >= replay.samples.length &&
      Number(metrics.samples) <= 120001,
  );
  assertContract(vector(metrics.measurement_window_s, 2));
  const window = metrics.measurement_window_s as number[];
  assertContract(window[0] >= 0 && window[1] >= window[0] && window[1] <= 120);
  assertContract(Array.isArray(eventsValue) && eventsValue.length <= 100);
  previous = -1;
  for (const value of eventsValue) {
    const e = object(value);
    assertContract(
      finite(e.time_s) &&
        e.time_s >= 0 &&
        e.time_s >= previous &&
        e.time_s <= replay.samples.at(-1).time_s,
    );
    assertContract(
      ["target_step", "force_start", "force_end"].includes(String(e.type)),
    );
    previous = e.time_s;
  }
  return {
    entry,
    samples: replay.samples,
    manifest,
    metrics,
    events: eventsValue,
  } as Recording;
}

// Body FLU vertices are rotated in ENU first, then converted to Three's Y-up basis.
export const enuToView = ([east, north, up]: Vec3): Vec3 => [east, up, -north];
export function slerp(a: Wxyz, input: Wxyz, t: number): Wxyz {
  let dot = a.reduce((sum, n, i) => sum + n * input[i], 0);
  const b = input.map((n) => (dot < 0 ? -n : n)) as Wxyz;
  dot = Math.min(1, Math.abs(dot));
  if (dot > 0.9995) {
    const q = a.map((n, i) => n + (b[i] - n) * t) as Wxyz;
    const norm = Math.hypot(...q);
    return q.map((n) => n / norm) as Wxyz;
  }
  const angle = Math.acos(dot),
    divisor = Math.sin(angle);
  return a.map(
    (n, i) =>
      (n * Math.sin((1 - t) * angle) + b[i] * Math.sin(t * angle)) / divisor,
  ) as Wxyz;
}
export function sampleAt(samples: Sample[], time: number): Sample {
  if (!finite(time)) throw Error("Invalid replay time");
  let low = 0,
    high = samples.length - 1;
  while (low + 1 < high) {
    const mid = (low + high) >> 1;
    if (samples[mid].time_s <= time) low = mid;
    else high = mid;
  }
  if (time >= samples[high].time_s) low = high;
  const a = samples[low],
    b = samples[Math.min(low + 1, samples.length - 1)];
  const t =
    a === b
      ? 0
      : Math.max(0, Math.min(1, (time - a.time_s) / (b.time_s - a.time_s)));
  return {
    time_s: time,
    position_m: a.position_m.map(
      (n, i) => n + (b.position_m[i] - n) * t,
    ) as Vec3,
    target_m: a.target_m,
    quaternion_wxyz: slerp(a.quaternion_wxyz, b.quaternion_wxyz, t),
  };
}
