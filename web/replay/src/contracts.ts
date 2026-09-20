export type Vec3 = [number, number, number];
export type Wxyz = [number, number, number, number];
export type Sample = {
  time_s: number;
  position_m: Vec3;
  target_m: Vec3;
  quaternion_wxyz: Wxyz;
  rotor_thrust_n?: [number, number, number, number];
  wind_velocity_m_s?: Vec3;
  external_force_n?: Vec3;
  external_moment_nm?: Vec3;
  mission_phase?: string;
  contact_normal_force_n?: Vec3;
  support_clearance_m?: number;
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
    mission?: {
      liftoff_time_s: number | null;
      touchdown_time_s: number | null;
      touchdown_descent_speed_m_s: number | null;
      landed_time_s: number | null;
      waypoint_reached_s: (number | null)[];
      waypoint_band_m?: number;
      touchdown_horizontal_speed_m_s?: number | null;
      final_support?: { mean_vertical_balance_error_n: number } | null;
      max_penetration_m: number;
      peak_tilt_deg: number;
    };
    turbulence?: {
      wind_position_rmse_m: number | null;
      peak_tilt_deg: number;
      recovery_time_s: number | null;
      recovery_band_m: number;
      recovery_dwell_s: number;
    };
  };
  manifest: {
    experiment: "cpu-rigid-body" | "isaac-quadrotor";
    model:
      | "ideal-body-wrench-v1"
      | "quadrotor-x-v1"
      | "quadrotor-x-wind-v1"
      | "quadrotor-x-contact-v1"
      | "quadrotor-x-contact-wind-v1";
    source_commit: string;
    source_dirty: boolean;
    source_tree_sha256?: string;
    controller_binary_sha256?: string;
    lock_sha256?: string;
    failure_reason: string | null;
  };
};
export const MISSION_PHASES = [
  "grounded",
  "takeoff",
  "hover",
  "north",
  "north_hold",
  "east",
  "east_hold",
  "return",
  "home_hold",
  "landing",
  "landed",
];
export const HASH = /^[0-9a-f]{64}$/;
const ID =
  /^(cpu|isaac)-(hover|position-step|lateral-force-pulse|turbulence-hold|turbulence-attitude-only|ground-mission|ground-mission-wind)-\d{1,10}-[0-9a-f]{12}$/;
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
    ((data.schema_version === 1 && data.isaac_validated === false) ||
      ([2, 3, 4, 5].includes(Number(data.schema_version)) &&
        typeof data.schema_version === "number" &&
        data.learning_validated === false &&
        !("isaac_validated" in data))) &&
      data.kind === "recorded_simulation" &&
      data.release_status === "research_preview",
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
      [
        "hover",
        "position-step",
        "lateral-force-pulse",
        "turbulence-hold",
        "turbulence-attitude-only",
        "ground-mission",
        "ground-mission-wind",
      ].includes(String(run.scenario)) &&
        Number.isInteger(run.seed) &&
        Number(run.seed) >= 0 &&
        Number(run.seed) <= 2147483647,
    );
    if (String(run.scenario).startsWith("turbulence-"))
      assertContract(
        [3, 4, 5].includes(Number(data.schema_version)) &&
          run.run_id.startsWith("isaac-"),
      );
    assertContract(
      (run.run_id.startsWith(`cpu-${run.scenario}-${run.seed}-`) ||
        ([2, 3, 4, 5].includes(Number(data.schema_version)) &&
          run.run_id.startsWith(`isaac-${run.scenario}-${run.seed}-`))) &&
        ["passed", "failed"].includes(String(run.status)),
    );
    if (run.scenario === "ground-mission")
      assertContract(
        [4, 5].includes(Number(data.schema_version)) &&
          run.run_id.startsWith("isaac-"),
      );
    if (run.scenario === "ground-mission-wind")
      assertContract(
        data.schema_version === 5 && run.run_id.startsWith("isaac-"),
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
  const flight = entry.run_id.startsWith("isaac-");
  const windMission = entry.scenario === "ground-mission-wind";
  const wind = entry.scenario.startsWith("turbulence-") || windMission;
  const contact = entry.scenario === "ground-mission" || windMission;
  const schema = windMission ? 5 : contact ? 4 : wind ? 3 : flight ? 2 : 1;
  assertContract(!(wind || contact) || flight);
  assertContract(
    replay.schema_version === schema &&
      replay.kind === "recorded_simulation" &&
      replay.run_id === entry.run_id,
  );
  assertContract(
    manifest.schema_version === schema &&
      manifest.run_id === entry.run_id &&
      manifest.fixture === false &&
      manifest.kind === "recorded_simulation",
  );
  assertContract(
    manifest.experiment === (flight ? "isaac-quadrotor" : "cpu-rigid-body") &&
      manifest.model ===
        (windMission
          ? "quadrotor-x-contact-wind-v1"
          : contact
            ? "quadrotor-x-contact-v1"
            : wind
              ? "quadrotor-x-wind-v1"
              : flight
                ? "quadrotor-x-v1"
                : "ideal-body-wrench-v1") &&
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
      "attitude_altitude_threshold",
      "turbulence_hold_threshold",
      "mission_threshold",
      "mission_support_threshold",
      "wind_mission_threshold",
      "wind_mission_support_threshold",
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
    if (flight)
      assertContract(
        vector(s.rotor_thrust_n, 4) &&
          (s.rotor_thrust_n as number[]).every((n) => n >= 0 && n <= 5),
      );
    else assertContract(s.rotor_thrust_n === undefined);
    for (const field of [
      "wind_velocity_m_s",
      "external_force_n",
      "external_moment_nm",
    ])
      assertContract(wind ? vector(s[field], 3) : s[field] === undefined);
    if (wind)
      assertContract(
        Math.hypot(...(s.wind_velocity_m_s as number[])) <= 12.000001,
      );
    if (contact) {
      assertContract(
        MISSION_PHASES.includes(String(s.mission_phase)) &&
          vector(s.contact_normal_force_n, 3) &&
          finite(s.support_clearance_m),
      );
      const force = s.contact_normal_force_n as number[];
      assertContract(
        force[2] >= -1e-6 &&
          force[2] <= 10000 &&
          force.slice(0, 2).every((n) => Math.abs(n) <= 1e-4),
      );
    } else
      assertContract(
        s.mission_phase === undefined &&
          s.contact_normal_force_n === undefined &&
          s.support_clearance_m === undefined,
      );
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
  if (wind && !contact) {
    const turbulence = object(metrics.turbulence);
    for (const field of ["wind_position_rmse_m", "recovery_time_s"])
      assertContract(
        turbulence[field] === null ||
          (finite(turbulence[field]) && turbulence[field] >= 0),
      );
    assertContract(
      finite(turbulence.peak_tilt_deg) &&
        turbulence.peak_tilt_deg >= 0 &&
        turbulence.peak_tilt_deg <= 180,
    );
    assertContract(
      turbulence.recovery_band_m === 0.1 && turbulence.recovery_dwell_s === 2,
    );
    for (const field of [
      "source_tree_sha256",
      "controller_binary_sha256",
      "lock_sha256",
    ])
      assertContract(
        typeof manifest[field] === "string" && HASH.test(manifest[field]),
      );
  } else assertContract(metrics.turbulence === undefined);
  if (contact) {
    const mission = object(metrics.mission);
    if (windMission) {
      assertContract(mission.waypoint_band_m === 0.35);
      assertContract(
        mission.touchdown_horizontal_speed_m_s === null ||
          (finite(mission.touchdown_horizontal_speed_m_s) &&
            mission.touchdown_horizontal_speed_m_s >= 0),
      );
      for (const field of ["initial_support", "final_support"])
        assertContract(
          mission[field] === null ||
            finite(object(mission[field]).mean_vertical_balance_error_n),
        );
    }
    for (const field of [
      "liftoff_time_s",
      "touchdown_time_s",
      "landed_time_s",
      "touchdown_descent_speed_m_s",
    ])
      assertContract(
        mission[field] === null ||
          (finite(mission[field]) &&
            mission[field] >= 0 &&
            mission[field] <= 50),
      );
    assertContract(
      Array.isArray(mission.waypoint_reached_s) &&
        mission.waypoint_reached_s.length === 4 &&
        mission.waypoint_reached_s.every(
          (n) => n === null || (finite(n) && n >= 0 && n <= 34),
        ),
    );
    assertContract(
      finite(mission.max_penetration_m) &&
        mission.max_penetration_m >= 0 &&
        finite(mission.peak_tilt_deg) &&
        mission.peak_tilt_deg >= 0 &&
        mission.peak_tilt_deg <= 180,
    );
    for (const field of [
      "source_tree_sha256",
      "controller_binary_sha256",
      "lock_sha256",
    ])
      assertContract(
        typeof manifest[field] === "string" && HASH.test(manifest[field]),
      );
  } else assertContract(metrics.mission === undefined);
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
      (contact
        ? [
            ...MISSION_PHASES,
            "liftoff",
            "touchdown",
            ...(windMission ? ["wind_start", "gust_start", "gust_end"] : []),
          ]
        : wind
          ? ["wind_start", "gust_start", "gust_end", "wind_end"]
          : ["target_step", "force_start", "force_end"]
      ).includes(String(e.type)),
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
    ...(a.rotor_thrust_n
      ? {
          rotor_thrust_n: a.rotor_thrust_n.map(
            (n, i) => n + (b.rotor_thrust_n![i] - n) * t,
          ) as [number, number, number, number],
        }
      : {}),
    ...(a.mission_phase
      ? {
          // Discrete contact/phase readings stay at the last measured sample.
          mission_phase: a.mission_phase,
          contact_normal_force_n: a.contact_normal_force_n,
          support_clearance_m: a.support_clearance_m,
        }
      : {}),
    ...(a.wind_velocity_m_s
      ? Object.fromEntries(
          (
            [
              "wind_velocity_m_s",
              "external_force_n",
              "external_moment_nm",
            ] as const
          ).map((key) => [
            key,
            a[key]!.map((n, i) => n + (b[key]![i] - n) * t),
          ]),
        )
      : {}),
  };
}

export const tiltDegrees = ([w, x, y, z]: Wxyz) =>
  (Math.acos(Math.max(-1, Math.min(1, 1 - 2 * (x * x + y * y)))) * 180) /
  Math.PI;

export function validateWindPair(held: Recording, reference: Recording) {
  assertContract(
    held.entry.scenario === "turbulence-hold" &&
      reference.entry.scenario === "turbulence-attitude-only" &&
      held.entry.seed === reference.entry.seed,
  );
  for (const key of [
    "source_commit",
    "source_dirty",
    "source_tree_sha256",
    "controller_binary_sha256",
    "lock_sha256",
  ] as const)
    assertContract(held.manifest[key] === reference.manifest[key]);
  assertContract(held.samples.length === reference.samples.length);
  for (let i = 0; i < held.samples.length; i++) {
    const a = held.samples[i],
      b = reference.samples[i];
    assertContract(
      a.time_s === b.time_s &&
        a.wind_velocity_m_s &&
        b.wind_velocity_m_s &&
        a.wind_velocity_m_s.every((v, j) => v === b.wind_velocity_m_s![j]),
    );
  }
  assertContract(
    held.samples[0].position_m.every(
      (v, i) => v === reference.samples[0].position_m[i],
    ),
  );
  return reference;
}
