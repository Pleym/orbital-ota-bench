# STATE

## Current Milestone
M1 — DUAL-SLOT TARGET

## Tasks Done
- Scaffolded project structure (ground, target, runtime, bundles, console, chaos, docs, tests)
- Created public GitHub repository (Pleym/orbital-ota-bench) and pushed initial code
- Wrote self-documenting Makefile skeleton
- Configured GitHub Actions pipeline for CI
- Set up pinned python dependencies inside virtualenv
- Created STATE.md and BLOCKERS.md
- Created README.md with problem statement and roadmap
- Created ADR-0001: why A/B partitioning over in-place updates

## Tasks Remaining
- Implement M1: Bootable QEMU ARM image with two rootfs slots.
- Implement persistent boot-control block (BCB) holding active slot, pending slot, boot attempt counter, confirmed flag.
- Implement boot logic that selects active slot, increments counter before userspace, auto-reverts after 3 unconfirmed attempts.
- Ensure the boot-control block is written atomically.
- Create ADR-0002 documenting the atomicity strategy.
- Implement tests/test_ab_slots.py covering normal boot, pending slot confirmed, pending slot unconfirmed reverting after 3 attempts, and simulated power cut during BCB write.
- Run `make test-boot` to boot a real QEMU instance and reach a login shell.

## Decisions Made
- Use Python 3.11 with a venv or uv as preferred
- Target ARM QEMU for A/B boot simulation
- Use CUE for mission configuration
- Adopt A/B partitioning scheme to ensure fail-safe updates

## Open Problems
- None
