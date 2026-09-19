# Website preview checkpoint

On 2026-09-20, the reusable viewer was integrated into a separate static website
preview at `/work/aeroloop/`. The component is pinned to AeroLoop commit
`a5734cfc2150032ee291993f955928043bca9730`, with a source allowlist, file checksums
and Apache-2.0 license. The website change is a draft for maintainer review.

Three actual CPU recordings from the clean-checkout audit are displayed: seed 0
of hover, north position-step and east force-pulse. Each selected replay requires
43 to 49 kB gzip including display samples and metadata; full-resolution samples
are retained separately. All fifteen CPU trial outcomes remain in the audit.
The measured Isaac summary is a separate section with its fixed twenty-seed
trained/untrained comparison, acceptance criterion and model limitations.

Local validation passed: format, lint, TypeScript, one preview-server test,
47 content tests, content validation, the production build, 13 static-output
checks and Cloudflare Pages compatibility. All 160 website browser tests passed.
After the final mobile chart-label adjustment, ten focused integration tests
passed again, covering keyboard controls, accessibility, no-JavaScript evidence,
3D rendering and four viewport sizes in light/dark themes. The staged privacy
scan and immutable source/data hash checks passed.

The website's hosted GitHub Actions jobs did not start because its Actions budget
prevents further use. This is an outstanding hosted validation gate, despite the
completed local checks. AeroLoop's own public PR checks passed. No budget, billing,
production configuration or merge was changed.

The implementation is ready for preview review. Maintainer review, hosted website
validation and a release decision remain required before claiming a released MVP.
