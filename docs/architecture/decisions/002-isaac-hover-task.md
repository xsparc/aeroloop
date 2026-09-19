# 002: Use an original body-wrench task on Isaac Sim PhysX

Accepted 2026-09-20 within the approved physics-only MVP.

Isaac Lab `v3.0.0-EA` no longer includes the older registered direct quadcopter
training task. It retains a quadcopter demonstration, but its asset and mass differ
from AeroLoop's CPU model. Implement a small original `DirectRLEnv` task using a
primitive rigid body, explicit 1 kg mass and diagonal inertia (0.02, 0.02, 0.04)
kg m². No vendor drone mesh or checkpoint is redistributed.

Select `isaacsim_physx` explicitly. The alternative Kit-less backends do not satisfy
this experiment. Start Kit before importing scene or asset modules: loading the
standalone USD libraries first causes conflicting DLLs on the tested Windows setup.

The task uses ideal body thrust and moments, with no motor dynamics, drag, estimator,
camera or physical-flight claim. World axes are ENU and body axes FLU. Lab 3 stores
quaternions as **xyzw**; AeroLoop's CPU/public replay uses **wxyz**. Learning records
name their ordering explicitly and are not silently passed into the CPU exporter.

Physics runs at 200 Hz and control at 50 Hz. Four clipped actions map to
`thrust = 9.80665 * (1 + action[0])` N and body moments
`action[1:4] * (0.4, 0.4, 0.2)` N m. There is no stabilizing controller hidden behind
the policy. The separate CPU experiments continue to execute the C++ rate controller.

The 13 observations are target-minus-position (3), world linear velocity (3),
body-to-world xyzw quaternion with nonnegative w (4), and body angular velocity (3).
The actor and critic use running observation normalization. The target is (0, 0, 1.5)
m. Resets sample each position offset in [-0.5, 0.5] m, XYZ Euler angle in [-0.1, 0.1]
rad and velocity component in [-0.1, 0.1] m/s or rad/s. Training seed is 73.

Episodes last 10 s. Terminate for non-finite state, altitude outside [0.2, 3.5] m,
or horizontal distance above 3 m. The reward combines survival, exponential position
accuracy, upright attitude and velocity/rate/action penalties; the exact coefficients
are versioned with the task source. No target or threshold changes follow held-out
evaluation. Development seeds are 500–519; held-out seeds are 10000–10019. Success
requires a complete episode with no failure and error <=0.30 m at every 50 Hz sample
from 8 through 10 s. Capture state before automatic reset, and retain all failures.

Use upstream RSL-RL PPO with local TensorBoard files. Save the untrained and trained
checkpoints; reload using PyTorch's restricted `weights_only=True` loader in a fresh
process. Raw logs, checkpoints and trajectories remain ignored local artifacts.

References: [pinned quadcopter demonstration](https://github.com/isaac-sim/IsaacLab/blob/ae37b028ea415c91ea2bc32609efcd759ed2b974/scripts/demos/quadcopter.py),
[direct environment example](https://github.com/isaac-sim/IsaacLab/blob/ae37b028ea415c91ea2bc32609efcd759ed2b974/source/isaaclab_tasks/isaaclab_tasks/core/cartpole/cartpole_direct_env.py),
[pose convention](https://github.com/isaac-sim/IsaacLab/blob/ae37b028ea415c91ea2bc32609efcd759ed2b974/source/isaaclab/isaaclab/assets/asset_base_cfg.py).
