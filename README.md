# Orbital OTA Bench

[![CI](https://github.com/Pleym/orbital-ota-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/Pleym/orbital-ota-bench/actions)

Modern software deployment assumes a persistent, high-bandwidth, and reliable connection to the machine. In space, these assumptions catastrophically break down. Satellites are reachable only for short, physics-derived ground-station contact windows, and a single failed update can permanently turn a multimillion-dollar spacecraft into uncontrollable orbital debris.

`orbital-ota-bench` is a complete, production-quality, fault-injection testbed for over-the-air (OTA) software deployment to satellites. It simulates a fleet of Linux spacecraft orbiting Earth, and proves that software updates can survive extreme conditions: telemetry link interruptions, flight package corruption, sudden power loss mid-write, buggy build rollouts, and hostile tenant workloads.

![Console Recovery Demo](docs/assets/console-demo.gif)

---

## Architecture Overview

The system consists of several dedicated segments:
*   **/ground**: Ground station uplink scheduler, delta-packager, transfer protocol, and operator CLI.
*   **/target**: Custom dual-slot rootfs manager, boot control logic, and target health validation agent.
*   **/runtime**: Customer container runner with cgroup and memory isolation limits.
*   **/bundles**: CUE schemas defining configuration, services, and multi-tenant resource constraints.
*   **/console**: Dense, dark-themed operator dashboard with a live contact timeline, fleet states, and fault-injection panels.
*   **/chaos**: Fault injection harness to trigger link drop, corruption, power cuts, and rogue tenants.

---

## Roadmap & Milestones

*   **M0: Scaffold** — Core directory structure, Makefile, GitHub Actions, and initial documentation.
*   **M1: Dual-Slot Target** — Real QEMU bootable ARM target with transactional A/B boot manager.
*   **M2: Orbital Link** — Celestial orbital mechanics (TLE/SGP4 propagation) constraint model and chunked-resumable signing uplink protocol.
*   **M3: Autonomous Recovery** — Target-side health checks, automated watchdogs, and zero-ground autonomous rollbacks.
*   **M4: Tenant Isolation** — Read-only container sandboxes, cgroup constraints, resource protections, and rogue tenant tests.
*   **M5: CUE Bundles** — Strict declarative satellite configuration schemas and compile-time conflict solver.
*   **M6: Operator Console & Chaos** — Live fleet operator console with 24h timeline, rolling deployment pipeline, and live chaos injection.
*   **M7: Polish** — Final test coverages, static analyses, failure mode analysis report, and GitLab mirror.

---

## Getting Started

### Prerequisites

You will need `make`, `uv`, `qemu-system-arm`, and `cue` installed.

To set up the complete environment automatically:
```bash
make setup
```

To run the full test suite:
```bash
make verify
```
