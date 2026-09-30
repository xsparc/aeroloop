# 020: Inspect landing evidence at the physics cadence

Accepted 2026-09-30 after PR 23, baseline
`5bf7af8ee25558c72ca4cd1eb400a15fa2b3369d`.

AL-023 implements the requested ten-feature working demo as one diagnosis
workspace. It re-verifies the retained AL-022 recordings; it does not produce new
flight evidence or change control, physics, sensors, seeds or acceptance limits.

The ten acceptance features are:

1. A 24-flight matrix filtered by quality, profile and mission outcome.
2. Synchronized 3D views of a selected flight and its same-quality, same-seed
   no-outage reference; reference-to-self selections are explicitly labeled.
3. Clickable 200 Hz plots with a shared cursor, bounded time window and playback.
4. Exact recorded event navigation, including touchdown, landed and outages.
5. Phase-separated applied-feedback error statistics over [40,42) seconds.
6. Independently selectable truth, raw capture, predictor and applied altitude
   overlays, exposing post-disarm drift without implying motor actuation.
7. Original mission gates with signed headroom in each gate's native units.
8. Same-quality pair results and final uninterrupted recovery intervals, with
   horizon completeness and failed outcomes retained.
9. Verified source, binary, lock, sample hashes, runtime and coverage details.
10. Numeric CSV export of the selected 200 Hz window with explicit columns/units.

For feature 5, partition each recorded sample exactly once: motors-off (landed
and zero requested thrust), contact (normal force > 0.1 N), airborne descent
(landing phase), or other. Motors-off takes precedence over contact. Report
counts, coverage, horizontal/vertical RMSE and peak, and peak timestamps. Empty
groups have null metrics. These descriptive strata neither change mission gates
nor assert a causal explanation. Contact can be intermittent; "airborne descent"
is a per-sample classification, not necessarily everything before first contact.

[PX4's landing states](https://docs.px4.io/main/en/advanced_config/land_detector)
distinguish contact, landed and disarming, while its
[log-analysis guide](https://docs.px4.io/main/en/log/flight_log_analysis)
describes time-series and 3D inspection. Those references motivate separating
states and synchronized inspection; this project does not implement PX4's land
detector or operate hardware.

Export only allowlisted fields after the existing full recording reconstruction,
ideal-reference reproduction and quality-matrix validation. Each numeric row is
one original physics sample, without interpolation or decimation. Keep 3D display
poses separately decimated; numeric plots and CSV retain 200 Hz. The index pins
per-flight payloads with SHA256; use bounded same-origin loads, strict contracts,
aborted stale requests and numeric-only CSV. Never include host paths or raw logs.

Validate independent phase arithmetic and boundary/empty/truncated cases, gate
headroom semantics, export hashes, contract tampering, stale loads, playback,
3D, CSV and mobile layout. Re-derive the full 24-flight matrix and inspect actual
recordings in the browser. Update the plan with measured diagnostic findings.
No new GPU run is required for this analysis-only change. AL-010 remains open.
