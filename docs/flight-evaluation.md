# Flight evaluation and guided demonstration

The explorer presents the complete three-seed PhysX timestep study, with named
mission gates, full-rate pair metrics and synchronized recorded 3D. It makes
the [retained study](evidence/isaac-live-flight-validation.md) inspectable; it
does not execute a simulator or replace the [live monitor](live-flight-tests.md).

Prepare the three frequency directories produced by the live flight workflow:

```sh
python tools/evaluation_demo.py runs/isaac-flight-study-200-001 runs/isaac-flight-study-400-001 runs/isaac-flight-study-800-001 --name evaluation-study-001
cd web/replay
npm ci --ignore-scripts
npm run dev
```

Open `/evaluation.html` on the printed loopback URL. Each export needs a new
`--name`; existing evidence is never overwritten. The command re-verifies every
full recording, source/configuration match and exact paired wind sequence before
writing the compact bundle. An incomplete matrix is rejected. Valid failed or
truncated trials remain visible; missing measurements cannot pass gates.

Select a wind seed and a 400 or 800 Hz candidate. Both views use the same simulation
time and compare with that seed's 200 Hz baseline. Enable **paired 3D**, then use
the timeline, keyboard arrows or mission chapters. The touchdown chapters use
each recording's measured contact time. **Play**, **Pause** and speed selection
control playback; visibility loss or scrolling the views offscreen pauses it.
Reduced-motion mode keeps manual seeking available. The top-view trajectory and
numeric readouts work without WebGL. Cameras may be adjusted independently.

The matrix shows mission status, position RMSE and measured wall speed. Below the
views, inspect all 24 gates for both runs, including support balance and touchdown
speed. Full-rate pair differences are separate from the illustrative error plot.
**Download evaluation JSON** saves the nine cases, gates, comparisons and hashes.

## Evidence boundary

The separate `flight_evaluation` contract has a SHA-256-pinned index capped at
256 KiB. It binds 36 display documents: replay, manifest, metrics and events for
each of nine runs. Selected pairs alone are loaded, using same-origin URLs,
bounded reads, checksums, source identity checks and cancellable requests.
Replay files are capped at 4 MiB; other documents at 64 KiB. The export is capped
at 16 MiB. A deployment must pin the configuration/index together; checksums
detect changed content, not a malicious publisher replacing that trust anchor.

Evaluation uses every 200 Hz control sample. Display samples are approximately
20 Hz with event instants, neighboring samples and endpoints retained. Pose
interpolation and the display error plot are not additional solver measurements.
Raw samples/configuration remain in the original verified recording directories;
the compact bundle contains their hashes rather than duplicate raw data.

The study demonstrates bounded sensitivity for these missions. Independent yaw
refinement remains unresolved, and perfect feedback plus simplified wind, rotors
and contact limit physical realism. No hardware-flight, convergence or new
learned-policy claim follows from this presentation. See
[decision 009](architecture/decisions/009-evaluation-demonstration.md) and
[validation](evidence/flight-evaluation-validation.md).
