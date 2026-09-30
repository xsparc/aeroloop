# Horizontal quality validation

AL-022 implementation and protocol are under verification. No new GPU results
have been recorded yet. Final measurement must use a clean committed revision and
the fixed [ADR 019 protocol](../architecture/decisions/019-horizontal-channel-quality.md).

The generic OpenSteward checker hardcodes a different project identity; its
`project.identity` finding is a known tool limitation. AeroLoop retains its real
identity and uses `tools/check_evidence.py` for project traceability. Independent
AL-010 yaw refinement remains open.
