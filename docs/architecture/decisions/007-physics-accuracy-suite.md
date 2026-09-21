# 007: Verify the physics bridge against independent solutions

Accepted 2026-09-21 under the maintainer's simulation and physics continuation.
Baseline: `f2d7aba81b422fe745ec096965b384eb8b2e4272`.

AL-010 prioritizes numerical physics verification before sensor noise and delay.
Add a separate headless PhysX suite using the existing 1 kg cuboid, diagonal
inertia, gravity, rotor lag and drag implementation. Preserve all flight-control,
training and replay contracts. This verifies implementation and numerical error;
it does not calibrate an aircraft or atmospheric model.

Execute each case at dt = 0.005, 0.0025 and 0.00125 s (200/400/800 Hz), in
separate worker processes. The simulation context must report the requested dt.
Disable damping and sleeping, enable gyroscopic forces and use four position / one
velocity solver iterations. Use the mission floor, friction and contact offsets.
Only the drop reaches the floor. Reset body pose, velocity, wrench and sensor
between cases; never prescribe body pose during integration.

Development correction: the first 200 Hz drop exceeded the 3 mm penetration gate
(4.061 mm) with the mission's 1 mm contact offsets. The pinned GPU bridge disables
sweep CCD; a speculative CCD trial produced identical measurements. Use a 10 mm
contact-generation offset per collider for this faster drop, retaining the physical
surface, zero rest offset and acceptance thresholds. The combined 20 mm detection
margin covers approximately 16 mm of travel per 200 Hz step near impact. This is a
solver margin, not a larger collider or higher floor. Retain both failed traces and
their configurations; final reports require the corrected margin. This does not
change existing mission scenes or claim protection at arbitrarily high speeds.

Force-integration diagnostic: development traces passed each absolute error gate,
but default TGS yaw angle error did not decrease monotonically at 200/400/800 Hz.
The deprecated `enable_external_forces_every_iteration=False` option gave decreasing
errors, with larger coarse-step translational and angular errors. Preserve the
default; add an explicit `per-step` diagnostic mode and measure both modes in the
final clean-source matrix (36 cases). Report refinement separately for each mode.
Do not weaken the original refinement criterion or call the entire matrix accepted
when the default mode fails it. Keep this finding open for the next physics study.

Cases and independent continuous-time references:

- Free fall: 0.25 s from z=1.5 m, zero velocity. p=p0+g*t^2/2, v=g*t.
- Tilted thrust: fixed 30 degree roll, 0.25 s, body +Z thrust mg/cos(30).
  World acceleration is (0,-g*tan(30),0); test the force/frame bridge.
- Yaw torque: 0.5 s, torque 0.04 Nm around body +Z, thrust mg. With Izz=0.04,
  angular acceleration is 1 rad/s2; yaw=t^2/2 and yaw rate=t.
- Rotor step: 0.3 s, four initially stopped motors each commanded to 3 N.
  With tau=0.03 s, total thrust is 12*(1-exp(-t/tau)). Integrate this expression
  analytically for position and velocity, including gravity. Applied thrust uses
  the existing interval-end motor update; its integration bias must shrink with dt.
- Drag coast: 2 s from horizontal speed 5 m/s, with gravity canceled by mg and
  the wind model's pressure centre at the COM to isolate translation. In still
  air, k=rho*CdA/(2m), v=v0/(1+k*v0*t), x=log(1+k*v0*t)/k. Require dissipation.
- Floor drop: 2 s from z=0.55 m, no thrust, zero restitution. Ideal first contact
  is sqrt(2*0.5/g). Check measured contact impulse against vertical momentum,
  penetration, energy and final support. Do not treat peak impact force as a
  timestep-independent quantity or require an exact contact trajectory.

Acceptance fixed before development execution (r=dt/0.005):

- All six complete traces per dt; finite values and unit quaternions. No fixture
  can stand in for a measured GPU run. Retain failures and full-rate samples.
- Free fall / tilted thrust: peak position error <=0.02*r+0.00001 m; peak velocity
  error <=0.001 m/s. Attitude error <=0.001 rad; rate error <=0.001 rad/s.
- Yaw torque: peak position error <=0.0002 m, velocity <=0.001 m/s, angle error
  <=0.0015*r+0.00002 rad and angular-rate error <=0.0005 rad/s.
- Rotor step: peak position error <=0.01*r+0.0001 m, velocity <=0.04*r+0.0001 m/s;
  attitude and angular-rate errors <=0.001. Recompute every lagged rotor input.
- Drag coast: peak position error <=0.02*r+0.0001 m, velocity <=0.004*r+0.0001 m/s;
  attitude and rate errors <=0.001. Translational kinetic energy cannot increase
  by more than 0.00001 J in any sample interval.
- Drop: first-contact time error <=2*dt+0.002 s; penetration <=0.003 m; peak
  vertical momentum/impulse residual <=0.001 Ns; mechanical energy cannot exceed
  its initial value by >0.02 J. During 1.5-2 s: height error <=0.001 m, speed
  <=0.001 m/s and mean normal-force error <=1% of weight.
- Halving dt must reduce peak position error for free fall, tilted thrust, rotor
  step and drag coast, and peak yaw angle error for yaw torque, to <=0.65 of its
  preceding value plus a 0.00002 m/rad numerical floor. Drop contact timing may
  vary by the sampling interval; report its changes without a monotonicity claim.

Develop the suite first, then freeze a clean source revision and rerun all three
timesteps for final evidence. Do not loosen gates to make a measured failure pass.
The CPU verifier checks fixed configuration, complete case/timestep sets, file
hashes, provenance, inputs and recomputed metrics/outcomes. Public reports use
allowlisted fields only. Raw traces and host logs remain local.

Affected requirement: REQ-PHYSICS-ACCURACY. Paths: optional Isaac worker and
launcher, analytical reference/evidence module, report tool, CPU tests and docs.
Risks: frame errors, motor input timing, stale reset state, contact force aligned
to the wrong interval, fabricated aggregate success and overstated convergence.
Verification includes analytic derivative tests, force timing, corruption,
missing/duplicate cases, false aggregates and failed-trial retention. Validate
the real GPU matrix and inspect measured diagnostic plots. Existing 3D mission
replay remains available; these force-isolation cases are not mission recordings.

Sources: [Isaac simulation configuration](https://isaac-sim.github.io/IsaacLab/release/3.0.0/source/api/lab/isaaclab.sim.html),
[NASA drag relation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/drag-equation/)
and [contact sensor semantics](https://isaac-sim.github.io/IsaacLab/main/source/overview/core-concepts/sensors/contact_sensor.html).
References support the API and model form; tolerances are project decisions.
