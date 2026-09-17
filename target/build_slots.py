import os
import shutil
import tarfile
import sys

def build_slots():
    base_dir = "/Users/dorian/orbital-ota-bench"
    build_dir = os.path.join(base_dir, "build")
    slot_a_dir = os.path.join(build_dir, "slot_a")
    slot_b_dir = os.path.join(build_dir, "slot_b")
    minirootfs_tar = os.path.join(build_dir, "alpine-minirootfs.tar.gz")

    for d in [slot_a_dir, slot_b_dir]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    print("Unpacking minirootfs to Slot A...")
    with tarfile.open(minirootfs_tar, "r:gz") as tar:
        tar.extractall(path=slot_a_dir)

    print("Unpacking minirootfs to Slot B...")
    with tarfile.open(minirootfs_tar, "r:gz") as tar:
        tar.extractall(path=slot_b_dir)

    # Customize Slot A and Slot B to make them distinct
    # Create an identifier file in /etc/slot_id
    for name, d in [("A", slot_a_dir), ("B", slot_b_dir)]:
        with open(os.path.join(d, "etc", "slot_id"), "w") as f:
            f.write(f"{name}\n")
            
        # Write a custom banner or issue file
        with open(os.path.join(d, "etc", "issue"), "w") as f:
            f.write(f"Welcome to Spacecraft Linux (Slot {name})\n\n")

        # Create a custom etc/inittab
        inittab_content = f"""# /etc/inittab for Spacecraft Linux
::sysinit:/etc/init.d/rcS
ttyAMA0::respawn:/bin/sh
::ctrlaltdel:/sbin/reboot
::shutdown:/bin/sync
"""
        inittab_path = os.path.join(d, "etc", "inittab")
        with open(inittab_path, "w") as f:
            f.write(inittab_content)

        # Create etc/init.d directory if it doesn't exist
        os.makedirs(os.path.join(d, "etc", "init.d"), exist_ok=True)
        rcs_path = os.path.join(d, "etc", "init.d", "rcS")
        rcs_content = f"""#!/bin/sh
echo "=========================================="
echo "Welcome to Spacecraft Linux (Slot {name})"
echo "=========================================="
hostname -F /etc/hostname 2>/dev/null || hostname spacecraft-{name.lower()}
"""
        with open(rcs_path, "w") as f:
            f.write(rcs_content)
        os.chmod(rcs_path, 0o755)

    # Pack back into uncompressed tar archives
    print("Creating Slot A tar archive...")
    with tarfile.open(os.path.join(build_dir, "slot_a.tar"), "w") as tar:
        tar.add(slot_a_dir, arcname=".")

    print("Creating Slot B tar archive...")
    with tarfile.open(os.path.join(build_dir, "slot_b.tar"), "w") as tar:
        tar.add(slot_b_dir, arcname=".")

    print("Slots successfully built!")

if __name__ == "__main__":
    build_slots()
