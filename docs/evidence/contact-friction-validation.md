# Contact friction validation

Measured 2026-10-09 under AL-028 / ADR 025. Frozen capture source:
`c0be5717c1b58869ee8d8ab7aa53438b85324c14`; baseline:
`f7efe92fe5b1045717479de04262b5ef1baf5d00`.
The [numeric report](contact-friction-001.json) contains case identities,
unchanged failed-gate IDs, original-recording digests and repeatability results.

## Physics execution

The declared matrix attempted 19 fresh 50 s flights: sixteen gain/outage cases
at 5 ms and three ideal-feedback seed 301 sensitivity cases at 5/2.5/1.25 ms.
Every flight enabled live monitoring; the eight outage flights were paced.
Development seed 83 was excluded. An initial development probe rejected GPU
filtering against the static cuboid; the compatible probe used the explicitly
recorded stationary kinematic ground with unchanged geometry/pose/material.

Eighteen recordings completed verification: nine mission passes and nine mission
failures. The fixed gain matrix passed 4/8, scheduled gains 5/8. All four new
seed 1009 flights passed. All twelve previously observed seed/profile/mode cases
matched their retained complete 10,001-state trajectories exactly, including
original failures. This observation covers these cases only and does not prove
universal noninterference of the ground/instrumentation change.

For seed 301, final support horizontal error was 0.476821 m at 5 ms and
0.445225 m at 2.5 ms, both above the unchanged 0.35 m limit. The 1.25 ms capture
reached 50 s but failed sidecar completion at validation: at 2.320 s during
takeoff it contained a vertical normal force of -0.01508235745 N. The original
recording reader independently rejected the same normal-force sample. This
case is explicitly **unverified**, with its raw recording digest and anomaly
visible in the demo. It has no verified friction replay, work metrics or mission
claim. No force was clipped and no existing contract or gate was relaxed.

The negative normal is a remaining sensor/solver investigation, not a demonstrated
physical attractive contact. This sweep does not establish numerical convergence.
The existing AL-010 yaw refinement issue also remains open.

## Force accounting

The 18 verified captures contain 180,000 control intervals. Independent arithmetic
recomputed all three momentum residual components, norms with/without friction,
wind/thrust/friction work, kinetic change, remaining work residual and defined
COM alignments directly from raw samples/sidecars. Maximum difference from the
exported arithmetic was 1.12e-16, below the predeclared 2e-9 tolerance.

Across verified flights, including measured friction reduces full-flight RMS
momentum residuals from 0.000919301–0.00444718 N s to 9.27819e-08–1.5821e-07 N s.
Every verified case used at most two of 64 friction anchors. Filtered and aggregate
normal matched under the capture guard. Small impulse residuals demonstrate
internal accounting consistency, not real-airframe accuracy.

The bundle digest is
`5c97bf7862b3e4ddcdf3346d7287051288e2db166456629c229aebda940f1b1e`.
Exports carry actual recorded targets into 3D, omit undefined alignment points,
and retain all original mission gates. Full-flight table statistics and selected
window statistics have different, explicitly labeled scopes.

## Browser and software verification

The real-data browser check loaded all 18 cases through hash verification, rendered
the measured 3D flight/contact vectors, downloaded CSV and JSON, restored a
hash-bound review link and fitted a 320 px viewport without horizontal overflow.
No page errors occurred. Visual inspection identified and corrected a canvas
containment issue; a dedicated browser assertion now keeps the canvas within its
replay panel. The live endpoint was observed advancing during seed 1009, with
fresh telemetry and no browser errors.

Focused contact tests verify synthetic impulse/work closure, interval boundaries,
missing directions, saturation rejection, exact-flight sidecar binding and
loopback origin/path/write restrictions. Browser cases exercise corrupted data,
rejected timestep visibility, stale live data, 3D containment and review exports.
Final local CPU regression ran 160 tests: 159 passed with one existing Windows
symlink-permission skip. All 56 frontend tests passed; all 55 available browser
tests passed with three existing fixture skips. Both native CTest checks passed.
Production build, public-source scan, dependency-lock check and dated AeroLoop
evidence-index check passed. The build retains the existing large-renderer-chunk
warning. Generic OpenSteward static and 2026-10-09 strict checks retain only the
known `project.identity` mismatch requiring the plugin's own name; AeroLoop's
identity is preserved and that generic gate is not claimed green.

## Limitations and next work

Friction is a measured resultant against the ground; COM alignment is not
contact-point slip. Work is a discrete horizontal translational estimate and
excludes rotational/contact-point work. Material coefficients are references,
not new acceptance gates. These small synthetic cohorts retain simplified wind,
rotors, ideal attitude and contact supervision. Next isolate the signed normal
sample before changing force validation or claiming timestep convergence.
