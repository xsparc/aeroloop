# Landing capture guard validation

AL-020 is in progress under [decision 017](../architecture/decisions/017-landing-capture-guard.md).
The fixed protocol compares twelve fresh guarded regression flights with retained
AL-019 recordings and twelve fresh predictor-only/guarded flights on previously
unused seeds. No final GPU outcomes are claimed yet.

The implementation records commanded descent separately from the original
scheduled target. CPU verification reconstructs every guard transition and
controller setpoint. The paired demo separates regression from unseen cases,
retains failed gates and uses full-rate evidence for acceptance.

The guard remains opt-in. Original mission, timing, recovery and physics limits
stay unchanged. AL-010 yaw refinement remains open.
