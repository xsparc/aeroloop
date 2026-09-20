# AeroLoop replay component

A read-only React 19 / Three.js 0.185 viewer for validated AeroLoop CPU and
Isaac quadrotor flight-control recordings, with explicit backend labels.
React, React DOM and Three.js remain peer dependencies; the package does not bundle
another React runtime. The TypeScript build preserves the client boundary and
loads the Three renderer only after the visitor enables 3D.

```tsx
import { ReplayViewer } from "@aeroloop/replay";
import "@aeroloop/replay/style.css";

<ReplayViewer baseUrl="/evidence/aeroloop/" indexSha256={reviewedIndexHash} />
```

The host must obtain `reviewedIndexHash` from its reviewed, immutable export,
not from the same untrusted network response. Supply a same-origin directory
ending in `/`. Mount each viewer independently; it does not alter URL fragments
or global controls. HTTPS or localhost is needed for Web Crypto.

The index loads on first visibility. Only the selected run's replay, manifest,
events and metrics load. Full-resolution sample downloads are not automatic.
The loader bounds bytes while streaming, verifies SHA-256 before parsing,
validates frames and values, rejects redirects and omits credentials. A trusted
index pins integrity, not the truth of a simulation; the exporter validates raw
recordings and recomputes full-resolution metrics before publication.

The schematic shows position; the optional original 3D mesh also shows recorded
attitude and trajectory. Orbit with the pointer or choose top, side and orbit
camera presets with the keyboard. Version 2 rotor recordings include thrust
meters and scaled thrust arrows on an X configuration. Body FLU coordinates
rotate into ENU using body-to-world wxyz quaternions,
then into the Y-up view basis `(east, up, -north)`. Quaternion interpolation follows
the shortest arc. Target steps are held until their recorded timestamp.

Playback starts paused, including under reduced motion. Hiding or scrolling away
pauses playback without automatic resume. The component cancels pending requests
and animation frames and disposes renderer, geometry and material resources on
unmount. WebGL failure retains the schematic, text and keyboard controls.

## Local demo

Build the native core first, then record hover, position-step and force-pulse runs
with `python tools/aeroloop simulate`. Prepare the ignored demo directory once:

```sh
python tools/replay_demo.py runs/<hover-run> runs/<step-run> runs/<pulse-run>
cd web/replay
npm ci --ignore-scripts
npm test
npx playwright install chromium
npm run test:browser
npm run dev
```

Open the printed loopback address. `npm run build` emits library modules and
declarations in `dist`; `npm run demo:build` emits the standalone site in
`demo-dist`. Neither output is committed. Choose a new export location or remove
only your generated demo evidence before preparing another recording set.

Use `--name <new-name>` with `tools/replay_demo.py` to retain previous bundles.
See the [Isaac drone workflow](../../docs/drone-development.md) to produce rotor
recordings through physics execution. No policy training is implied by a rotor replay.

CPU and Isaac flight-control replay are distinct from the hover training summary. No simulator
executes in the browser, and these simplified models do not validate physical flight.
This source uses the repository's Apache-2.0 license and original schematic geometry.
