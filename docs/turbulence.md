# Turbulence and stabilization

Run a pair of airborne drone experiments under identical seeded wind velocities.
`turbulence-hold` uses the existing position, attitude and native rate loops.
`turbulence-attitude-only` keeps altitude and attitude control but disables
horizontal position/velocity feedback. Its drift demonstrates the contribution
of position hold; reference completion is not a claim of position stability.

The [declared model and acceptance](architecture/decisions/004-turbulence-stabilization.md)
use correlated three-axis wind, a stronger east gust, quadratic relative-velocity
drag and torque from a pressure-centre offset. Isaac PhysX integrates the motion
at 200 Hz with the original four lagged rotors and unchanged gains. Neither run
overwrites poses after initialization. This is an illustrative temporal wind
experiment, not measured weather, CFD or a Dryden/Von Karman model.

Use the existing isolated Isaac installation after reviewing its NVIDIA terms as
described in the [drone workflow](drone-development.md). Run the development pair:

```sh
python tools/isaac.py flight --scenario turbulence --seeds 73 --output runs/wind-development --timeout 600
```

Freeze the implementation before running the final five paired seeds:

```sh
python tools/isaac.py flight --scenario turbulence --seeds 0 1 2 3 4 --output runs/wind-regression --timeout 900
python tools/wind_report.py runs/wind-regression --output docs/evidence/isaac-wind-001.json
```

The report requires a complete suite from one clean source revision, verifies
each recording and its pair, and writes only allowlisted model/provenance/metric
fields. Choose unused output paths. The worker returns a nonzero status for
incomplete execution, failed trial gates or a failed paired comparison. Failed
trials remain inspectable. Existing `--scenario all` still runs hover, step and
force-pulse; it does not silently add the more expensive wind experiments.

## Inspect the demonstration

Take the held and reference run directories for the same seed from `result.json`:

```sh
python tools/replay_demo.py --name turbulence-demo runs/wind-regression/<hold-run> runs/wind-regression/<reference-run>
cd web/replay
npm run dev
```

Open the printed loopback address. Select **Enable 3D view**, then **Compare
reference**. The held drone remains the subject of the 3D view; the orange dashed
error curve and synchronized numeric comparison come from the reference recording.
Selecting the reference experiment lets you inspect its separate 3D trajectory.

- Violet arrow: recorded world wind direction and speed (0.13 m per m/s).
- Orange arrow: aerodynamic force (0.5 m per N, capped at 2 m for display).
- Green arrows and meters: applied rotor thrust, including motor lag.
- Gold marker: hover target. The camera follows the drone during wind experiments;
  the target can leave the camera view as the reference drifts.
- The position schematic fits the whole path, including reference drift.

Jump to **12s / gust start**, play through the gust, then use **25s / wind end**
to observe recovery. The wind/drag vectors describe the following physics interval;
display values and poses interpolate retained samples. The comparison checks
matching seed, initial position, wind samples and source provenance. Full-resolution
metrics use 7,001 samples per complete run, with wind RMSE measured over 5–25 s.
Different trajectories naturally produce different relative-velocity drag forces.

The model starts airborne with perfect state and illustrative drag coefficients.
Ground contact, battery discharge, propeller aerodynamics, sensors and physical
flights remain outside this slice. The separate learned hover policy is unchanged.
