# Ground-contact mission validation

AL-008 acceptance is defined in [decision 005](../architecture/decisions/005-ground-contact-mission.md).
The preliminary seed-73 PhysX trial passed all mission gates over 10,001 samples.
All four waypoints were reached, peak tracking error was 0.545309 m and peak tilt
1.523402 degrees. Touchdown occurred at 44.770 s with preceding-sample downward
speed 0.048367 m/s; landing latched at 44.855 s. Final mean normal support was
9.806650 N with stopped motors. This development run used a modified working tree.

Local checks passed: 63 Python tests, eight React contract tests, three legacy
viewer tests and seven browser checks against the measured development recording.
The two wind-only browser checks were skipped on the mission bundle. Route and
landed 3D views were inspected. The clean-revision final five-seed suite is pending;
these preliminary results are not its substitute.
