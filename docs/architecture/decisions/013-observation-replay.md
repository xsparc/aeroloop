# 013: Inspect recorded observation robustness in paired 3D

Accepted 2026-09-27 after PR 16; baseline
`48b8b72df0e968d042eaeae205af8e5b844ffc19`.

AL-016 extends the existing evaluation explorer to AL-015's twelve retained
PhysX flights. Compare ideal feedback against noise, delay or their combination
for the same seed. Reuse the existing shared timeline, chapters, optional 3D,
truth trajectory plots and complete mission gates. Preserve AL-011's frequency
study and AL-015's physics/runtime/controller definitions unchanged.

Revalidate all 120012 full-rate samples, seeded observations, setpoints and paired
metrics before exporting a bounded compact bundle. Preserve historical source
identity and all failed/incomplete results. Add a distinct evaluation schema for
the four-profile matrix; require twelve unique cases, nine pairs, fixed profile
parameters and verified selected recordings. Keep the existing 256 KiB index,
4 MiB individual replay and 16 MiB total evaluation budgets. Never copy raw
control samples, configuration files or local metadata into the browser bundle.

Each 3D aircraft shows recorded physics truth, interpolated for display. Feedback
readouts use the preceding exported sample without interpolating or regenerating
noise. Show that sample's delivery time, capture time, age at delivery and its
position/velocity discrepancy against truth at the same recorded instant. A held
20 Hz display snapshot must not be mislabeled as new 200 Hz feedback. Preserve
start/end points and both sides of mission events.

Acceptance: re-export the complete retained matrix with identical full-rate
results; verify all artifact hashes; exercise malformed profile/age, missing or
duplicate cases, changed thresholds, swapped/corrupt recordings and failed pairs.
Inspect measured paired 3D at takeoff, landing gust and settled support, including
profile/seed selection, timeline controls and visible ideal-channel limitations.
Keep reduced-motion, offscreen pause, narrow layout and unavailable-WebGL paths.
Run CPU/native/frontend/browser and public-evidence gates. No new GPU measurements
are required for this export/display-only slice, and none should be implied.

Same-origin bounded hashing follows [Web Crypto guidance](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest).
Explicit pause controls follow [W3C motion guidance](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html).
AL-010 remains open; attitude/rates and mission/contact supervision remain ideal.
