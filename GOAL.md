# AeroLoop MVP checkpoints

- [x] Runnable C++ and Python CPU foundation.
- [x] Custom rate controller executing inside a measured CPU physics experiment.
- [x] Repeatable CPU scenarios with retained outcomes and reproducible metrics.
- [x] Actual Isaac Sim physics execution and measured reduced-workload environment evidence.
- [x] Actual Isaac Lab training, fresh-process reload and fixed held-out evaluation.
- [x] Strict, privacy-reviewed CPU export and accessible local recorded replay.
- [x] Reusable viewer and reviewed website integration.
- [x] Clean-checkout reproduction and post-merge evidence audit.

The simulation-only MVP is implemented. See the [final audit](docs/evidence/mvp-audit.md)
for the retained measurements and read-only checks of the served integration.

Release follow-up:

- [ ] Complete hosted website validation after its Actions budget permits execution.
- [ ] Obtain a versioned release decision before creating a tag or publishing packages.

The maintainer removed PX4 flight execution on 2026-09-20. Isaac simulation and
training remain required. The website's existing automatic build ran after the
maintainer merge; this does not close the outstanding hosted validation gate.
