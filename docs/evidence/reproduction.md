# Clean-checkout reproduction

On 2026-09-20, a new checkout of
`adf668eaf69df7c90cc07da9ba510c76fd0ae66e` built the native controller from source
with MSVC 19.51 and CMake/Ninja. Both C++ tests and all 40 Python tests passed.
No source modifications were present. Existing local compiler and Python 3.12.13
installations were reused; no previous build products were copied.

`python tools/aeroloop regress --output runs/audit` then executed all fifteen
predefined trials: five seeds each for hover, north position-step and east force
pulse. Every raw recording passed checksum, convention, sample and recomputed
metric validation. [The complete audit](reproduction-001.json) retains every
trial's outcome, metrics and manifest hash. The step settled in 3.09 seconds;
the force pulse never left the 0.30 m recovery band. Zero reported recovery time
therefore describes this threshold, not instantaneous response.

From that same fresh checkout, the isolated Isaac runtime reloaded the original
saved checkpoints and reran all forty fixed held-out comparisons. The task hash
matched training. [The revalidated summary](isaac-reproduction-001.json) again
reports 20/20 trained and 0/20 untrained successes; the worst trained final-window
error was 0.0509996 m. Raw samples were recomputed and checkpoint hashes verified
by `tools/isaac_report.py`. Training was not repeated and the installed Isaac
environment was reused. This checks source reproduction and saved-policy reload
on the previously measured machine, not a second-machine or fresh-install claim.

For the original installation, smoke, training and acceptance details, see
[Isaac validation](isaac-validation.md). Website review remains a separate MVP
gate; none of these checks authorizes deployment or establishes physical flight.
