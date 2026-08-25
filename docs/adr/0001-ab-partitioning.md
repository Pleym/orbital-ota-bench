# ADR-0001: A/B Partitioning over In-Place Updates

## Status
Proposed

## Context
Over-the-air (OTA) updates on a spacecraft are subject to extreme environmental and operational constraints. The link is hostile, intermittent, and low-bandwidth. Power loss can occur at any millisecond due to battery depletion or eclipse entries. If an update fails mid-execution or leaves the system in a non-bootable state, the vehicle is bricked. Physical access is impossible; the vehicle becomes orbital debris.

Traditionally, server systems perform in-place updates, updating files and packages on a live running system. We must evaluate whether this approach is acceptable for flight software on our spacecraft.

## Decision
We select an **A/B Partitioning Scheme** (dual active/inactive root filesystem slots) combined with an atomic Boot Control Block (BCB) stored in persistent mass memory.

Under this scheme:
- The system is partitioned into Slot A and Slot B.
- One slot is marked as `active` and currently running.
- The other slot is `inactive` and serves as the target for incoming OTA updates.
- Updates are written entirely to the inactive slot.
- Once completed, validated, and signed, the system triggers a reboot with the inactive slot marked as `pending`.
- After booting the pending slot, a health agent must verify key services. Only then does it mark the slot as `confirmed` (making it the active slot).
- If the pending slot fails to boot or verify itself, the hardware watchdog or bootloader automatically falls back to the previous known-good active slot.

## Alternatives Rejected

### 1. In-Place File/Package Updates
- **Why Rejected:** Extremely risky. An in-place update alters the currently running system. If power is lost mid-update, or if the update package contains a bad library that crashes system services, the system may fail to boot. Recovering from a partially written or corrupted filesystem requires a functioning recovery system, which itself could be damaged by the in-place write. It does not provide an atomic fallback.

### 2. Single Slot with Recovery Ramdisk (Recovery Mode)
- **Why Rejected:** A dedicated recovery ramdisk can boot the system into a minimal safe mode to download a clean image. However, if the main slot is corrupted, the satellite must spend significant time in safe mode with no operational payload active, incurring severe mission downtime. Furthermore, if a bug exists in the recovery system or the shared bootloader/kernel, recovery is impossible. A/B partitioning keeps a fully operational, validated, and complete system always ready to boot instantly.

## Consequences
- **Storage Cost:** Requires doubling the storage allocated for the root filesystem. This is a deliberate and necessary trade-off; storage is cheap and abundant on modern mass memory compared to the catastrophic cost of losing a vehicle.
- **Complexity:** Requires atomic boot control logic, a custom or configured bootloader, and a health agent.
- **Safety:** Near-zero risk of a bricked spacecraft. A failed or corrupted update leaves the running active slot completely untouched, and the spacecraft remains commandable at all times.
