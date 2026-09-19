# MVP implementation audit

Audited 2026-09-20 against AeroLoop main commit
`baae7d1c6da59d26fc4177d0f0c75e6a2a281aaf`. The maintainer squash-merged the
reusable viewer and separate website integration. Both main-branch trees match
their reviewed feature-branch trees exactly. The public
[main-branch CI run](https://github.com/xsparc/aeroloop/actions/runs/35476116501)
passed.

## Boundary and acceptance

This audit completes the already planned AL-005 website and reproduction work.
It checks merged-source continuity, retained measurement integrity, served
recordings and accessible replay. It updates the checklist, roadmap and evidence
index without changing controller gains, physics, training, dependencies or
acceptance thresholds. A release tag, package publication and changes to hosting
or billing are separate actions.

The main risks are stale source references, altered exported data and overstating
what a successful check establishes. Evidence is therefore separated into source,
measurement, browser and hosted-validation results below.

## Retained measurements

The controller, physics and Isaac implementation is unchanged from the
[clean-checkout reproduction](reproduction.md). The current validators reread
all fifteen raw CPU recordings, checked their hashes and recomputed their
full-resolution metrics. Every result matched the public audit.

Both forty-trial Isaac summaries were also recomputed from their retained raw
evaluations, with checkpoint hashes checked. Each still reports 20/20 trained
and 0/20 untrained successes. These are rechecks of the original and reproduction
measurements, not newly trained policies or eighty independent trials. The
earlier GPU runs remain the execution evidence; no new GPU run was needed for
this documentation audit.

## Website integration

After the maintainer merge, the website's existing automatic Cloudflare build
reported success. Read-only checks of the served site then passed:

- 34 semantic page comparisons against the reviewed local build.
- 36 production comparisons covering those pages, the sitemap and RSS.
- 10 focused Chromium checks covering CPU/Isaac separation, keyboard controls,
  accessibility, no-JavaScript evidence, and optional 3D at 375, 768, 1440 and
  1920 px in light and dark themes.
- 23 exact byte/hash comparisons for the served AeroLoop evidence files,
  including all three recordings' full-resolution samples and display samples.
- Two existing local source/data tests covering immutable viewer provenance,
  recording checksums, payload budgets and complete CPU/Isaac trial counts.

The [structured audit](mvp-audit-001.json) retains the public source revision,
evidence hashes and check counts. Retained report hashes use committed Git bytes
so checkout line-ending conversion cannot change them. Host details, account identifiers, private
repository locations, logs and checkpoints are excluded. The live-site checks
were read-only; they did not initiate a deployment or submit URLs to a service.

## Result and remaining gate

The simulation-only MVP is implemented and the website integration has been
reviewed and verified. This includes actual Isaac physics and training; CPU
replay remains explicitly separate from Isaac policy evaluation. Ideal actuators,
perfect state and the measured single-machine workload remain the model boundary.

The website's GitHub Actions checks, including its production audit job, still
could not start because of an Actions budget block. Local and live checks do not
turn those hosted jobs into passes. Restore execution capacity through the
maintainer's account controls, then rerun the existing checks before closing
release validation. No budget changes are part of this audit.

A versioned release has not been created. Reopen implementation work for an
observed defect or an approved extension; no further feature is required by the
current MVP acceptance criteria.
