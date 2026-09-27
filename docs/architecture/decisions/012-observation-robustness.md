# 012: Measure position and velocity observation robustness

Accepted 2026-09-27 after PR 15; baseline
`be513360f6b86fafbd1240eb30f7a96b92c8e90e`.

AL-015 perturbs only the position and velocity supplied to the outer trajectory
controller. Keep the 200 Hz turbulent contact mission, controller gains, actuator
model, runtime, wind seeds, physics and original mission gates fixed. Attitude,
angular rate/acceleration, mission supervisor and contact sensing remain ideal.
This is a synthetic feedback robustness study, not an IMU, GNSS or estimator model.
Recorded state, forces, safety limits and evaluation always use physics truth.

Before GPU measurements, freeze four profiles: ideal, noise, delay, noise-delay.
Noise is independent Gaussian per axis at capture with nominal standard deviations
0.01 m and 0.02 m/s, clipped at three standard deviations. Its dedicated seeded
random stream must not consume wind or initial-condition randomness. Delay is
eight control samples (40 ms). Hold the first captured observation until history
exists; record its source sequence, time and actual age. In the combined profile,
delay the already noisy capture, never regenerate noise on delivery. Preserve
the current ideal attitude when assembling feedback state.

Run development seed 73 first, then the complete four-profile by seeds 0/1/2
matrix at one clean implementation revision. Preserve every result. Require all
original mission gates and 10001 samples per trial. Against same-seed ideal
feedback, bound peak truth-position difference at 0.15 m, absolute position RMSE
change at 0.05 m, and absolute landed-time difference at 0.5 s. These are bounded
robustness checks, not convergence or real-flight certification. Do not tune the
profiles, controller or gates against final seeds. A failed bound is a finding.

Use a versioned evidence contract to reconstruct observations from truth and seed,
then recompute outer-controller requests and original truth-based mission gates.
Reject mixed profiles, source revisions, parameters, matrices and altered samples.
Keep older evidence contracts intact. Monitor each run; pace the combined profile
and report actual wall-clock lag. Inspect live 3D truth and expose observation age
and discrepancy explicitly. Keep raw traces local and publish allowlisted metrics.

Isaac Lab documents noise and delayed histories. A small Python capture FIFO is
used here for independent CPU replay without requiring Isaac at verification time;
its initial-history policy is explicitly defined above, not inherited from Lab.
AL-010's original yaw-refinement finding remains open; no solver claim changes.

Sources: [Isaac Lab delay and noise utilities](https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.utils.html).
