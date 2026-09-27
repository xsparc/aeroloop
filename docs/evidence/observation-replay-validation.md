# Recorded observation evaluation validation

AL-016 re-evaluated the retained AL-015 observations on 2026-09-27 after squash
merge `48b8b72df0e968d042eaeae205af8e5b844ffc19`. This is an export and display
change. No new GPU flight, controller tuning, training or physics change was
performed.

The full verifier reconstructed feedback and controller setpoints across all
120012 control samples. The exported study is structurally identical to
[the original report](isaac-observation-001.json): twelve mission passes and nine
paired robustness passes. All 288 individual mission gates retain their original
thresholds. The historical measured source remains
`27afe01388df4a778bdcb9a7fe7a4d3655739fe3`.

The compact bundle contains 49 JSON files totaling 12427254 bytes. All 48 display
document hashes were independently checked. Its 104419-byte index has SHA-256
`6a77181132ca7400caa9d6c63e7f444de782e9fad674be7589387a720f8d76b9`.
The largest replay is 1029831 bytes. These fit the existing index, per-document
and total budgets. Raw samples, configuration, runtime logs and screenshots stay
local and ignored.

Measured browser inspection covered seed 0 ideal versus combined noise/delay at
takeoff (2 s), landing gust (40 s) and settled support (48 s). Both 3D views
rendered. At settled support, both aircraft were landed at 0.050 m with 9.86 N
normal support while the recorded wind continued at 3.5 m/s. The candidate panel
retained its 47.960 s capture and 40 ms delivery age. Selecting seed 2 noise reset
the timeline and showed zero delay with distinct feedback discrepancies.
At seed 2 time 40.010 s, the feedback panel held the retained 40.005 s event
neighbor while the truth pose advanced. Reduced-motion settings were respected
throughout this measured inspection.

Protocol tests separately exercise the twelve-case matrix, fixed profile
parameters, failed/truncated results, changed thresholds, corrupted or swapped
feedback, source identity, checksums, event neighbors and absent raw data.
Seeking between display samples retains the actual preceding feedback snapshot
while truth pose interpolates. Browser checks cover profile selection, paired
WebGL, keyboard seeks, JSON download, reduced motion, narrow layout, offscreen
pause and unavailable-WebGL fallback. Synthetic browser fixtures do not stand
in for measured physics results.

Local regression passed 104 Python tests with one existing Windows symlink
permission skip, two native CTest checks, 16 frontend tests and three legacy
viewer tests. The browser suite passed 18 tests with three conditional skips for
scenarios absent from the selected legacy replay bundle; all eight evaluation
browser tests passed. The production build and dependency-lock check passed.
Existing renderer chunk-size and client-directive build warnings remain.
Public-source, UTF-8 and dated AeroLoop evidence checks passed. Generic OpenSteward
static and strict checks retain only the known hardcoded `project.identity`
mismatch; the AeroLoop registry identity is unchanged.

The bounded [AL-015 limitations](isaac-observation-validation.md) still apply:
synthetic position/velocity sensing, ideal attitude/rate/contact channels and
three fixed seeds. AL-010's original yaw-refinement gate remains open. Further
sensor realism requires a separately specified study and new PhysX measurements.
