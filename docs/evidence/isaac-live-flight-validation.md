# Live flight test validation

The acceptance protocol is fixed in [decision 008](../architecture/decisions/008-live-physics-flight-tests.md).
The final three-seed, three-frequency study has not yet been captured. AL-011
remains in progress; the earlier yaw-refinement finding remains open separately.

Development seed 73 completed the 50 s turbulent mission at 400 Hz physics with
unchanged 200 Hz control, wind and actuator cadence. All mission gates passed:
position RMSE 0.083518 m, peak error 0.256850 m, peak tilt 7.582221 degrees,
landed at 43.470 s. Wall-paced execution took 68.744 s in the control loop
(0.727335x real-time factor), with maximum lag 18.744 s. This development run
used a dirty revision and is not final clean-source acceptance evidence.

The browser observed actual simulation time advancing from 30.5 to 31.7 s during
the active worker, with a rendered 3D canvas and no page errors. Synthetic browser
fixtures separately exercise stale data, failed/verified status and reconnection;
they are not physics measurements. Privacy, full recording and final matrix
verification are required before closeout.
