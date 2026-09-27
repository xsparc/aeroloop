# 011: Test small-angle arithmetic against measured yaw

Accepted 2026-09-27 under autonomous continuation after PR 14. Baseline:
`04dcc208cf62b587a6029558e7ebf7e28238d361`.

AL-014 tests whether CUDA fast trigonometry can reproduce the constant-spin
signature from decision 010. The public TGS accumulation source calls
`__sincosf`; the installed GPU library reports PhysX 5.9.1.0 and its extension
manifest 110.3.2. Current public source is context, not proof of the installed
kernel. Do not patch vendors, dependencies, flight control or accuracy gates.

Compare three independent GPU arithmetic recurrences: float32 library sin/cos,
float32 intrinsic sin/cos, and float64 library sin/cos. Each composes normalized
pure-yaw delta quaternions across the declared position iterations, then applies
the accumulated delta once per outer step. This is a controlled arithmetic
experiment, not a reimplementation of the whole PhysX solver. Use constant rates
+0.05, +0.5 and -0.5 rad/s, duration 0.5 s, timesteps .005/.0025/.00125 s,
and one/four iterations: 18 comparisons. No fitted time offsets or bias terms.
Torque cases remain in the separately remeasured 30-case physics matrix but are
excluded from this recurrence because internal torque substep rates are unobserved.

Before new GPU measurements, fix these interpretation rules:

- Re-run the complete decision 010 physics matrix at a clean implementation
  revision, with all existing gates and final matched-world-rate requirements.
- Capture complete finite arithmetic quaternion traces from the actual GPU and
  recompute every metric. Preserve failed comparisons and the original yaw gate.
- Check library float32 peak error <= 5e-6 rad and float64 <= 1e-10 rad against
  the analytic reference. These are arithmetic controls, not new physics gates.
- Call the fast-intrinsic signature supported only if, in all 18 constant-spin
  cases, its peak disagreement with PhysX is <= 5e-6 rad and <= 10% of PhysX's
  peak reference error. Report individual failures without tuning these bounds.
- Record a bounded installation fingerprint: selected PhysX extension versions,
  manifest/binary hashes and existing package versions, with no host paths.
  Compare it before/after the new physics/probe measurements. A fingerprint
  identifies the tested installation, not the exact instruction path executed.
- Verify source and input identities, matrix completeness and recomputed outcomes;
  test corruption, mixed evidence and false claims. Inspect a comparison figure.

Deliver a probe, strict CPU report, plot and reproducible operator documentation.
Update REQ-PHYSICS-ACCURACY and the roadmap. The outcome can support or reject the
hypothesis; AL-010 remains open unless its original independent gates pass.
The next step depends on the measured result, not the research suggestion alone.

Sources: [GPU TGS accumulation](https://github.com/NVIDIA-Omniverse/PhysX/blob/main/physx/source/gpusolver/src/CUDA/solverMultiBlockTGS.cu),
[NVIDIA floating-point guidance](https://docs.nvidia.com/cuda/floating-point/index.html).
