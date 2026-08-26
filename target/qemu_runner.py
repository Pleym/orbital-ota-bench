import subprocess
import time
import os
import sys

def launch_qemu(bcb_path="build/bcb.bin", slot_a_path="build/slot_a.tar", slot_b_path="build/slot_b.tar") -> subprocess.Popen:
    base_dir = "/Users/dorian/orbital-ota-bench"
    build_dir = os.path.join(base_dir, "build")
    kernel_path = os.path.join(build_dir, "vmlinuz-lts")
    initrd_path = os.path.join(build_dir, "initramfs.cpio.gz")
    
    # Ensure all files exist
    for f in [kernel_path, initrd_path, bcb_path, slot_a_path, slot_b_path]:
        if not os.path.exists(f):
            raise FileNotFoundError(f"Required file not found: {f}")
            
    # Command to run qemu-system-arm
    cmd = [
        "qemu-system-arm",
        "-M", "virt",
        "-m", "256M",
        "-kernel", kernel_path,
        "-initrd", initrd_path,
        "-nographic",
        "-append", "console=ttyAMA0 loglevel=3",
        "-drive", f"file={slot_a_path},format=raw,id=hd0,if=none",
        "-device", "virtio-blk-device,drive=hd0",
        "-drive", f"file={slot_b_path},format=raw,id=hd1,if=none",
        "-device", "virtio-blk-device,drive=hd1",
        "-drive", f"file={bcb_path},format=raw,id=hd2,if=none",
        "-device", "virtio-blk-device,drive=hd2"
    ]
    
    # Start process with piped stdin and stdout
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    return proc

def wait_for_output(proc: subprocess.Popen, pattern: str, timeout_s=15) -> str:
    """Reads QEMU output until pattern is found or timeout is reached."""
    output = []
    start_time = time.time()
    
    # Set non-blocking stdout reading
    assert proc.stdout is not None
    os.set_blocking(proc.stdout.fileno(), False)
    
    while True:
        if time.time() - start_time > timeout_s:
            break
            
        # Check if process died
        if proc.poll() is not None:
            break
            
        try:
            line = proc.stdout.readline()
            if line:
                output.append(line)
                sys.stdout.write(line)
                sys.stdout.flush()
                if pattern in line:
                    return "".join(output)
        except IOError:
            pass
            
        time.sleep(0.05)
        
    full_output = "".join(output)
    if pattern not in full_output:
        raise TimeoutError(f"Pattern '{pattern}' not found in QEMU boot output within {timeout_s}s. Output:\n{full_output}")
    return full_output

def send_command(proc: subprocess.Popen, command: str):
    """Sends a command to QEMU guest stdin."""
    if proc.stdin:
        proc.stdin.write(command + "\n")
        proc.stdin.flush()

def kill_qemu(proc: subprocess.Popen):
    """Cleanly terminates QEMU process."""
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()

if __name__ == "__main__":
    print("Testing QEMU Boot...")
    # Initialize BCB to default if empty
    from target.boot_control import BCB, write_bcb
    write_bcb("build/bcb.bin", BCB(sequence=0, active_slot='A', pending_slot='0', boot_attempts=0, confirmed=1))
    
    proc = launch_qemu()
    try:
        print("QEMU process started. Waiting for login/shell prompt...")
        # Wait for our custom shell or issue banner
        wait_for_output(proc, "Welcome to Spacecraft Linux", timeout_s=20)
        print("\nSUCCESS: Reached login shell in QEMU!")
        
        # Test executing a command
        print("Sending command: 'cat /etc/slot_id'")
        send_command(proc, "cat /etc/slot_id")
        out = wait_for_output(proc, "A", timeout_s=5)
        print("\nCommand output verified slot ID is A.")
    finally:
        print("Killing QEMU...")
        kill_qemu(proc)
