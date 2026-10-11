# Contact liftoff probe validation

Measured 2026-10-11 for AL-029 / ADR 026. Baseline:
`56c7df609d54f212d289958d177e2578d4378b87`. All final GPU captures used clean
source `b4db3976fb2b9653e3c8224269ee869329ed6f47`. The subsequent changes add
geometry inspection, CLI guards and closeout evidence without changing capture code.
The [numeric report](contact-probe-001.json) retains all twelve cases, raw digests,
runtime/binary identity, anomalies and historical comparisons.

## Declared physics experiment

Twelve fresh three-second seed-301 probes executed successfully: three physics
timesteps, two TGS external-force integration settings and two repeats. One
earlier development capture at 1.25 ms was excluded. The native flight controller,
rotor model, wind, material, geometry and ideal feedback are reused. Control is
200 Hz. These probes stop before mission scoring and are **diagnostic captures**,
not accepted flights. Negative values are retained in a separate strict schema.

| Physics step | Per-iteration negative intervals, each repeat | Per-step negative intervals, each repeat | Repeated rows |
| --- | --- | --- | --- |
| 5 ms | 0 | 0 | Exact match in both settings |
| 2.5 ms | 0 | 0 | Exact match in both settings |
| 1.25 ms | 1 | 0 | Exact match in both settings |

All six repeated pairs are identical across every captured field. The default
per-iteration cases match all 600 retained control-rate positions, velocities
and quaternion samples at each timestep over (0,3]. The historical finest-step
recording remains unverified; its hash-intact prefix is a repeatability reference,
not a newly accepted flight. The original reader still rejects it with
`invalid ground normal force`. No original contract or threshold changed.

## Resolved measurement and remaining physics question

Both default 1.25 ms repeats report the same substep at 2.31875 s:

- Aggregate and filtered normal Z: **−0.06032943 N**.
- Raw scalar impulse: **+0.00007541179 N·s**.
- Geometric normal approximately **(−0.00041095, 0, −0.99999994)**.
- Reported point approximately **(5.101453, −0.190759, 0.00100006) m**.
- Vehicle COM approximately **(0.002998, 0.009127, 0.052402) m**.
- Point distance outside the oriented vehicle collider: **4.898484 m**.
- Normal reconstruction difference: **1.908e−12 N·s**.
- Linear momentum residual magnitude: **3.354e−8 N·s**.

This substep explains the negative 5 ms interval average at 2.320 s in AL-028.
The sign comes from the reported downward geometric normal, not a negative
scalar impulse. The raw contact decomposition, sensor and measured linear
momentum agree within the reported errors. The point-placement anomaly is
visible in the measured 3D replay and exported numerical data.

This does not establish the internal solver cause, a physically attractive
contact, or a correct contact location. Backend APIs share the same engine.
The per-step setting is deprecated and remains diagnostic; its lack of the
incident in this cohort does not justify a default change. A predeclared geometry
isolation study with angular as well as linear balance is the next roadmap step.
Full-flight rejection, mission failures and AL-010 yaw refinement remain open.

## Validation

Independent arithmetic checked **16,800 substep intervals** using raw impulses,
applied forces, gravity and measured velocity changes. Maximum summary difference
was **6.111e−20**, below the declared 2e−9 tolerance. No capture saturated the
64-item buffer; the peak was five contact points and two friction anchors.

- CPU suite: 164 tests, 163 passed and one existing Windows symlink skip. After
  adding CLI guards, all five focused probe tests passed.
- Native CTest: two passed.
- Frontend: 59 passed, including signed data, corruption and oriented geometry.
- Full browser run: 58 passed, three existing fixture skips. After visualization
  refinement, all four focused probe browser tests passed, including context loss.
- Actual-data browser: all twelve captures passed browser contracts and opened;
  measured 3D, 320 px layout, restored bound links and CSV/JSON downloads passed,
  with no page errors. The incident CSV contains 80 intervals and 18 fixed columns;
  the JSON retains full source identity and the signed anomaly.
- Production build passed after fixing a Windows encoding issue. The existing
  renderer chunk-size warning remains.
- Project evidence, public source and version-lock checks passed. The generic
  plugin governance checker retains its sole project-name incompatibility:
  it requires `opensteward-control-plane`; this repository is `aeroloop`.
  It is not reported as a passing generic gate.

Only sanitized numerical evidence is tracked. Raw captures, browser images,
machine logs and prepared demo bundles stay ignored. The demo is a loopback
preview, not a deployment or publication of raw host artifacts.
