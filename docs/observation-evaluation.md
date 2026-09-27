# Recorded observation evaluation

Inspect the [four-profile PhysX study](observation-robustness.md) in synchronized
3D. The explorer compares each noisy or delayed flight with the same wind seed's
ideal-feedback flight. It displays recorded results; use the
[live monitor](observation-robustness.md#run-and-monitor) during new experiments.

From the repository root, export the four complete study directories:

```sh
python tools/evaluation_demo.py runs/observation-ideal runs/observation-noise runs/observation-delay runs/observation-noise-delay --observations --name observation-evaluation-001
cd web/replay
npm ci --ignore-scripts
npm run dev
```

Open `/evaluation.html` on the printed loopback URL. Substitute the directories
from your own study and choose a new bundle name on every export. Exporting needs
no GPU: the CPU verifier rechecks all recorded samples, reconstructs the seeded
feedback and controller setpoints, and recomputes the unchanged mission and pair
metrics. The complete three-seed, four-profile matrix is required. Valid failed
or truncated flights remain visible; incomplete pairs cannot pass.

Select a wind seed and candidate profile, then enable **paired 3D**. The fixed
profiles use nominal position noise of 0.01 m and velocity noise of 0.02 m/s,
clipped at three standard deviations; delayed profiles hold eight control steps
(40 ms). Physics and control run at 200 Hz in these recordings.

Both aircraft, their routes and the error plot show physics truth. The shared
timeline and mission chapters seek both flights together. Each **Delivered
feedback** panel shows a recorded delivery snapshot, its capture time, age at
delivery, and position/velocity discrepancy from truth at that snapshot. Between
display points the feedback panel holds its preceding recorded sample while the
aircraft pose interpolates. The discrepancy is not computed against that
interpolated pose, and no new noisy feedback is generated during playback.

Playback starts paused. Manual seeking remains available with reduced motion;
leaving the page or scrolling the pair offscreen pauses animation. Without WebGL,
the trajectory schematic and all evaluation controls remain usable. Changing a
profile or seed resets the timeline. Touchdown chapters use each flight's own
measured contact event. **Download evaluation JSON** saves all twelve cases,
288 mission gates, nine pair results and the artifact hashes.

## Evidence boundary

Evaluation schema two binds 48 display documents to a pinned index. Selected
pairs are loaded using the existing same-origin, cancellable, bounded checksum
reader. Limits remain 256 KiB for the index, 4 MiB per replay, 64 KiB for other
documents and 16 MiB for the bundle. Checksums detect content changes relative to
the pinned index; they do not authenticate a publisher who replaces that pin.

Approximately 20 Hz display samples retain endpoints and each mission event's
neighboring control samples. Scores use every 200 Hz control sample. The original
source revision and raw sample/configuration hashes remain attached to each run;
raw traces and configuration files stay outside the compact bundle. The legacy
single-run exporter still rejects observation recordings; use this workflow.
The existing [frequency-study explorer](flight-evaluation.md) remains supported
without `--observations`.

Attitude, rates, acceleration and mission/contact supervision remain ideal.
These synthetic observations are not calibrated sensors or an estimator. The
original yaw-refinement gate remains open. No hardware-flight or general
stability claim follows from this display. See
[decision 013](architecture/decisions/013-observation-replay.md) and
[retained-data validation](evidence/observation-replay-validation.md).
