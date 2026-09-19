# Reusable replay delivery

AL-005 is split into independently reviewable changes: the reusable viewer
(AL-005A), a separate website preview (AL-005B), and clean-checkout reproduction
(AL-005C), followed by the post-merge evidence audit (AL-005D). This follows the
approved autonomous MVP implementation scope.

## Viewer acceptance

- React and Three.js are peer dependencies, with a standalone local demo.
- Only selected, bounded recordings load from the same origin. The host pins the
  index checksum; every displayed evidence document must match its checksum.
- ENU positions and body-to-world wxyz attitudes convert explicitly to the
  renderer's Y-up coordinates. Interpolation preserves target discontinuities.
- Playback starts paused, pauses offscreen and when hidden, and requires explicit
  restart. Reduced motion retains scrubbing and a static schematic.
- Play, pause, speed, scrub and event controls are keyboard accessible. A static
  text summary and SVG remain usable without WebGL. GPU resources are disposed.
- Metrics come from the export's full-resolution analysis. CPU replay never
  represents an Isaac trajectory. The measured Isaac summary remains separate.
- Browser tests cover actual exports, checksum rejection, lazy selection,
  responsive layouts and lifecycle cleanup; frame/math tests cover orientations.

Expected paths are `web/replay/`, export packaging tools, focused tests, CI and
project evidence. No changes to controller gains, training, thresholds, deployment
or physical-flight scope are included. Principal risks are frame conversion,
stale asynchronous loads, GPU leaks and evidence mislabeling.

## Website and reproduction acceptance

The website consumes an immutable copy with source revision, file checksums and
license. Its change is reviewed separately through a draft PR. Check its
repository rules, content integrity, production build, accessibility and local
preview. Do not deploy or merge. A fresh checkout must build the native core and
repeat all fifteen CPU scenarios before any completion claim. Retained Isaac
measurements describe only the tested environment and fixed experiment.

The maintainer has now merged both reviewed changes. See the
[post-merge audit](evidence/mvp-audit.md) for the served-site checks and remaining
hosted validation item. The release gate is retained without adding a new feature.
