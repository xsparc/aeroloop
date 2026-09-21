# Physics accuracy validation

AL-010 follows [decision 007](../architecture/decisions/007-physics-accuracy-suite.md).
The harness is implemented; final clean-source validation is pending.

Development found two issues. With the mission contact offsets, the 200 Hz drop
penetrated 4.061 mm, exceeding the 3 mm gate. A speculative CCD trial produced
identical results. Both failed trials are retained and still verify against their
original configurations. A 10 mm contact-generation margin per collider reduced
penetration to 1.819 mm without moving the floor or changing rest offset.

The corrected scene passed all 18 individual checks at 200/400/800 Hz. Four of
five refinement checks passed; default TGS yaw angle error was 0.243, 0.012 and
0.217 mrad, failing the unchanged refinement gate. The deprecated per-step force
option passed its 18 cases and five refinement checks, with larger coarse-step
errors. It is retained only as a diagnostic, not substituted for the default.

Final evidence must preserve both modes and report overall acceptance as false
if the default refinement issue remains. No complete physics-accuracy acceptance
is claimed from these dirty-source development measurements.
