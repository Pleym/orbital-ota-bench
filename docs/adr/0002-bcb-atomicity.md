# ADR-0002: Boot Control Block (BCB) Atomicity Strategy

## Status
Proposed

## Context
The Boot Control Block (BCB) is the non-volatile persistent storage area holding crucial state for our dual-slot boot logic: the currently active slot, the pending slot (if switching), the boot attempt counter for the current boot cycle, and whether the running slot has been confirmed healthy.

If a power cut or reset occurs *during* a write to the BCB, and the write is not atomic, the BCB can be left in an undefined or corrupted state. In orbit, where power is unstable and a bit flip or corruption must be expected, a corrupt BCB could prevent the spacecraft from booting at all, resulting in loss of mission.

We must define a strategy that guarantees that the BCB can always be read in a consistent state, even if power is cut at any arbitrary microsecond during a write.

## Decision
We implement a **Dual-Copy Checksummed NVRAM/Flash Layout** for the Boot Control Block, mapping to a dedicated persistent storage device or partition (modeled as `/dev/vdb` in our simulation).

### BCB Structure
The BCB is a fixed-size block of 128 bytes containing:
1. `magic`: 4 bytes (ASCII `BCB!`)
2. `sequence`: 8 bytes (64-bit unsigned integer, monotonically increasing)
3. `active_slot`: 1 byte (ASCII `A` or `B`)
4. `pending_slot`: 1 byte (ASCII `A`, `B`, or `0` for none)
5. `boot_attempts`: 1 byte (integer `0` to `3`)
6. `confirmed`: 1 byte (boolean: `1` for confirmed, `0` for unconfirmed)
7. `reserved`: 80 bytes (padding)
8. `checksum`: 32 bytes (SHA-256 hash over bytes 0-95)

### Read Algorithm
1. Read Copy 0 (first 128 bytes of `/dev/vdb`) and Copy 1 (second 128 bytes of `/dev/vdb`).
2. Verify Copy 0: check magic `BCB!`, compute SHA-256 and compare with checksum.
3. Verify Copy 1: check magic `BCB!`, compute SHA-256 and compare with checksum.
4. Selection logic:
   - If both copies are valid, use the copy with the larger `sequence` value.
   - If only one copy is valid, use the valid copy.
   - If both copies are invalid (first boot / corruption), initialize a default state (Slot A, `sequence` = 0, no pending, `boot_attempts` = 0, `confirmed` = 1) and write it to both copies.

### Write Algorithm
To update the state to new values:
1. Increment the `sequence` number.
2. Construct the binary struct with the new state, sequence, and SHA-256 checksum.
3. Write the binary struct to Copy 0.
4. Issue an `fsync` or equivalent device write barrier to guarantee the write is fully flushed to physical storage.
5. Write the same binary struct to Copy 1.
6. Issue another `fsync`.

## Alternatives Rejected

### 1. In-place Write with Single Copy
- **Why Rejected:** If power is cut mid-write, the single copy is corrupted (checksum mismatches or partial bytes). There is no fallback copy to read from, leaving the boot state undefined and the vehicle unbootable.

### 2. Standard Linux Journaled Filesystem (ext4/sqlite) for BCB
- **Why Rejected:** Filesystems like ext4 are extremely heavy for early bootloader access. Reading ext4 inside an early assembly bootloader or microinit is complex and requires embedding full filesystem drivers. A raw, sector-aligned block write is simple, fast, and does not depend on heavy OS services, making it perfectly suited for bare-metal or microinit environments.

## Consequences
- **Storage Overhead:** Negligible (256 bytes total).
- **Complexity:** Simple to implement in Python (for tests/ground tools) and in Busybox Shell or light C (for the early `/init` boot logic).
- **Safety:** Extremely high. Any single-write failure is fully protected, and the system can self-heal on the next boot by overwriting the corrupted sector with the good one.
