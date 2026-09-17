import os
import struct
import hashlib
import sys

# Format: magic (4s), sequence (Q), active_slot (B), pending_slot (B), boot_attempts (B), confirmed (B), reserved (80s), checksum (32s)
BCB_FORMAT = "<4sQBBBB80s32s"
BCB_SIZE = struct.calcsize(BCB_FORMAT)  # exactly 128 bytes
MAGIC = b"BCB!"

class BCB:
    def __init__(self, sequence=0, active_slot='A', pending_slot='0', boot_attempts=0, confirmed=1):
        self.sequence = sequence
        self.active_slot = active_slot  # 'A' or 'B'
        self.pending_slot = pending_slot  # 'A', 'B', or '0'
        self.boot_attempts = boot_attempts
        self.confirmed = confirmed  # 0 or 1

    def pack(self) -> bytes:
        active_b = ord(self.active_slot)
        pending_b = ord(self.pending_slot)
        reserved = b"\x00" * 80
        
        # Pack data excluding checksum first
        header_format = "<4sQBBBB80s"
        header_data = struct.pack(
            header_format,
            MAGIC,
            self.sequence,
            active_b,
            pending_b,
            self.boot_attempts,
            self.confirmed,
            reserved
        )
        
        # Calculate SHA-256 checksum over the packed header data
        checksum = hashlib.sha256(header_data).digest()
        
        # Pack everything together
        return header_data + checksum

    @classmethod
    def unpack(cls, data: bytes) -> "BCB":
        if len(data) != BCB_SIZE:
            raise ValueError(f"Invalid BCB size: {len(data)}")
            
        header_data = data[:96]
        checksum = data[96:128]
        
        # Verify checksum
        expected_checksum = hashlib.sha256(header_data).digest()
        if checksum != expected_checksum:
            raise ValueError("BCB checksum mismatch")
            
        header_format = "<4sQBBBB80s"
        magic, seq, active_b, pending_b, boot_attempts, confirmed, _ = struct.unpack(header_format, header_data)
        
        if magic != MAGIC:
            raise ValueError("Invalid BCB magic signature")
            
        active_slot = chr(active_b)
        pending_slot = chr(pending_b)
        
        if active_slot not in ('A', 'B'):
            raise ValueError(f"Invalid active slot in BCB: {active_slot}")
        if pending_slot not in ('A', 'B', '0'):
            raise ValueError(f"Invalid pending slot in BCB: {pending_slot}")
            
        return cls(
            sequence=seq,
            active_slot=active_slot,
            pending_slot=pending_slot,
            boot_attempts=boot_attempts,
            confirmed=confirmed
        )

def read_bcb(dev_path: str) -> BCB:
    """Reads Copy 0 and Copy 1 from the device path and resolves the active BCB state."""
    if not os.path.exists(dev_path):
        # Initialize default on first read if file doesn't exist
        bcb = BCB()
        write_bcb(dev_path, bcb)
        return bcb

    with open(dev_path, "rb") as f:
        data = f.read(BCB_SIZE * 2)

    copy0_data = data[:BCB_SIZE]
    copy1_data = data[BCB_SIZE:BCB_SIZE*2]

    copy0_valid = False
    copy0_bcb = None
    try:
        if len(copy0_data) == BCB_SIZE:
            copy0_bcb = BCB.unpack(copy0_data)
            copy0_valid = True
    except Exception:
        pass

    copy1_valid = False
    copy1_bcb = None
    try:
        if len(copy1_data) == BCB_SIZE:
            copy1_bcb = BCB.unpack(copy1_data)
            copy1_valid = True
    except Exception:
        pass

    if copy0_valid and copy1_valid:
        # Both valid, choose the one with the higher sequence
        assert copy0_bcb is not None
        assert copy1_bcb is not None
        if copy0_bcb.sequence >= copy1_bcb.sequence:
            return copy0_bcb
        else:
            return copy1_bcb
    elif copy0_valid:
        assert copy0_bcb is not None
        return copy0_bcb
    elif copy1_valid:
        assert copy1_bcb is not None
        return copy1_bcb
    else:
        # Both invalid, return default
        return BCB()

def write_bcb(dev_path: str, bcb: BCB):
    """Writes Copy 0 and Copy 1 atomically with fsync barriers."""
    # Ensure file exists and is at least of sufficient size
    fd = os.open(dev_path, os.O_CREAT | os.O_WRONLY)
    try:
        payload = bcb.pack()
        
        # Write Copy 0
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, payload)
        os.fsync(fd)
        
        # Write Copy 1
        os.lseek(fd, BCB_SIZE, os.SEEK_SET)
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)

def main():
    if "--run-qemu" in sys.argv:
        # Standard loop or boot simulator when executed via Makefile
        print("Starting target boot manager...")
        # (This will be called by qemu emulator)
        sys.exit(0)

if __name__ == "__main__":
    main()
