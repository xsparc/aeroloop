# 004: Demonstrate stabilization under repeatable turbulent wind

Accepted 2026-09-20 under the maintainer's explicit turbulence-simulation request.
Baseline: `3c550e80233da2fd9ac52cf2d05d9758f7962a1d`.

AL-007 adds two airborne Isaac PhysX scenarios: `turbulence-hold` and
`turbulence-attitude-only`. Both retain the same body, rotor limits, motor lag,
native rate gains, altitude and attitude loops. The reference disables only
horizontal position/velocity feedback. Compare identical initial conditions and
seeded wind velocities; aerodynamic forces may differ as the vehicles move.
No learned-policy, takeoff/contact, hardware or website deployment change is included.

Use a declared temporal Ornstein-Uhlenbeck wind test, not a Dryden/Von Karman
implementation or measured weather. Independent ENU gust components have stationary
standard deviations (1.2, 1.0, 0.5) m/s and 0.6 s correlation time. Initialize the
process from its stationary Gaussian distribution and use its exact discrete
transition at 200 Hz with a dedicated seed stream. Mean wind is (3, -1, 0) m/s.
Wind ramps on over 5–6 s and off over 24–25 s. A 3 m/s eastward half-sine gust
occupies 12–14 s. Cap the combined wind speed at 12 m/s; retain the exact sampled
velocities so this bounded engineering model is reproducible.

Compute quadratic drag from wind minus velocity at a body-fixed pressure centre
(0, 0, 0.03) m, including angular velocity at that point. Density is 1.225 kg/m³
and isotropic effective CdA is 0.06 m². Force is
`0.5 * rho * CdA * |relative_velocity| * relative_velocity`; moment about the COM
is `pressure_centre cross body_drag_force`. Transform world force into body axes
and add the drag moment to the rotor moment before each PhysX step. Drag remains
active in still air. Pose writes are allowed only during the initial reset.
Coefficients and offset are illustrative parameters, not identified hardware data.

Define acceptance before executing trials: 35 s per trial; development seed 73;
final seeds 0–4 for both modes, with no tuning against final seeds. Position hold
must keep 5–25 s position RMSE ≤0.5 m, full-trial peak error ≤1 m and peak tilt
≤25 degrees, then return within 0.10 m for two continuous seconds within five
seconds after wind ends. The reference must complete inside model bounds with
peak altitude error ≤0.25 m and tilt ≤25 degrees; completion does not mean it held
position. Every paired held run must reduce 5–25 s RMSE by at least 75% relative
to its reference. Preserve failures and report all trials and pair comparisons.

Version 3 evidence uses `quadrotor-x-wind-v1`, fixed wind and stabilization config,
recorded ENU wind velocity and external force, and body external moment. Export
recomputes wind, drag/moment, rotor evolution and metrics from full-resolution
samples. Versions 1 and 2 retain their existing contracts and experiment defaults.
The local viewer identifies the control mode, renders a wind vector beside the
drone, shows measured thrust, tilt, error and recovery, and provides the reference
recording for comparison. Display interpolation never replaces full-rate metrics.

Validate seed repeatability, exact OU transition, calm/relative-velocity drag,
moment-arm and frame signs, disabled horizontal feedback, recovery dwell, tampered
evidence, old contracts and browser behavior. Then execute actual GPU physics and
inspect the 3D replay. Main risks are frame/sign errors, misleading comparisons,
invented realism, incorrect outcome labels and private metadata in public evidence.

References: [NASA drag equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/drag-equation/)
and [relative air velocity](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/velocity-effects/).
[MathWorks' Dryden model](https://www.mathworks.com/help/aeroblks/drydenwindturbulencemodelcontinuous.html)
describes spectral shaping beyond this explicitly simpler temporal test.
