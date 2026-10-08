# 025: Measure ground friction and close interval momentum

Accepted 2026-10-08 under the ten-feature implementation and draft PR request,
after PR 30, baseline `f7efe92fe5b1045717479de04262b5ef1baf5d00`.
AL-028 is a bounded contact instrumentation and evaluation slice.

## Ten features and acceptance

1. Opt-in filtered ground-friction capture at every physics step, averaged over
   each control interval, with a capacity guard and hash-bound flight sidecar.
2. Three-axis momentum closure, showing residuals with and without friction.
3. Horizontal translational work accounting separating wind, thrust, friction,
   kinetic change and the remaining discrete residual.
4. COM sliding alignment diagnostics with missing low-speed directions retained.
5. Tangential friction / normal-force ratios alongside material coefficients.
6. Shared-cursor 3D aircraft replay with measured normal and friction vectors.
7. A bounded live contact endpoint and stale-aware monitoring page.
8. A three-timestep sensitivity sweep with unchanged 200 Hz flight control.
9. Sortable gain/outage/seed comparison matrix retaining original mission gates.
10. Verified bundle export, interval CSV, full JSON review and digest-bound links.

No controller, default gain, material, acceptance limit, pinned dependency or
original recording schema changes. No physical flights. AL-010 remains open.
Requirements: REQ-DRONE-CONTROL, REQ-FLIGHT-EVALUATION,
REQ-REUSABLE-REPLAY and REQ-LIVE-FLIGHT-TESTS.

## Measurement contract

[Isaac Lab's contact sensor](https://isaac-sim.github.io/IsaacLab/v3.0.0-EA/source/concepts/sensors/contact_sensor.html)
supports filtered friction in Isaac Sim PhysX, while its aggregate normal force
does not include friction. Capture `/World/Vehicle` against `/World/Ground`,
capacity 64 friction anchors. Reject capacity saturation and disagreement between
filtered and aggregate normal. Read installed backend fields explicitly.

Row at t describes the preceding control interval. Initial row is zero. Capture
every physics substep, including world thrust orientation at that substep, and
average forces. Momentum residual is m*(v_next-v_prev) minus dt times applied,
normal, friction and gravity. Window states [start,end] use force rows (start,end].
Force values are newtons, not impulses; multiply by the 5 ms control interval.

Work estimates use mean force dot horizontal COM displacement. They exclude
rotational and contact-point work; residual is not friction. COM friction alignment
uses midpoint horizontal velocity and is unavailable below .01 m/s or 1e-6 N.
Ratios require normal > .1 N. Static .7 and dynamic .5 material coefficients are
references, not new flight gates. [PhysX dynamics](https://nvidia-omniverse.github.io/PhysX/physx/5.4.0/docs/RigidBodyDynamics.html)
uses contact constraints; these diagnostics do not establish a calibrated
airframe or exact Coulomb stopping law.

## Frozen execution and validation protocol

Commit clean source before workers. Development seed 83 is excluded. Final
gain/outage matrix: seeds 1, 401, 709 and 1009; fixed/scheduled gains crossed
with sample-hold / hold-dropout-2000ms: 16 fresh 50 s flights at 5 ms physics.
Both modes retain vertical decay, predictive feedback and noisy/delayed fresh
horizontal observations. Every flight is monitored; outage sessions are paced.
Seeds 1/401/709 are known diagnostic cases, 1009 is an additional declared seed.
Keep all failures. Compare the twelve previously observed cases to their retained
originals to measure instrumentation repeatability, without assuming identity.

Separately run seed 301 with ideal state feedback at .005/.0025/.00125 s physics,
otherwise unchanged turbulent contact flight, for numerical sensitivity. These
three flights are not gain/outage comparisons or analytical friction calibration.
No acceptance thresholds are tuned against these results.

Validate exact synthetic impulse/work cases, missing directions, interval edges,
malformed/saturated captures, loopback origin/path restrictions, export integrity,
actual recorded browser plots/3D/mobile/downloads and independent arithmetic.
Run CPU/native/frontend/browser/build/public/evidence checks. Public evidence is
sanitized numerical summaries; raw recordings, runtime logs and local paths stay
ignored. Broad generic governance has a known project-identity incompatibility;
record it separately from AeroLoop's project evidence gate.

Risks: contact instrumentation could perturb repeatability; filtered buffer
semantics are runtime-specific; COM proxies can be misread as contact-point
measurements. Preserve hashes, original gates, omitted intervals and limitations.

## Development sensor compatibility finding

The excluded development seed 83 probe rejected static-cuboid ground filtering
on the installed GPU backend. Opt-in contact capture therefore adds a stationary
kinematic rigid body to the same ground cuboid. Geometry, pose and materials stay
fixed. Sidecars explicitly record `ground_kind: stationary-kinematic`; historical
unfiltered runs used a static collider. The twelve retained comparisons measure
this combined setup/instrumentation change, not instrumentation alone. Default
unfiltered flights keep their static ground. No claim of exact noninterference
is made without measured comparison.

## Measured closeout and unresolved refinement

The 2026-10-09 suite attempted all 19 declared flights. Eighteen completed
verification (nine mission passes, nine mission failures). The 1.25 ms seed 301
flight reached 50 s but sidecar completion rejected a negative normal force;
the unchanged original flight reader independently rejects the same sample.
The browser shows this third timestep as unverified with its recording digest,
invalid time and raw anomaly, without inventing friction/work metrics or replay.
No normal-force contract or acceptance limit was relaxed. The 18 valid captures
support all measured contact features; the failed refinement remains an open
physics question alongside AL-010. Numerical sensitivity is not certified as
converged. See the [validation record](../../evidence/contact-friction-validation.md).
