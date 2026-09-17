import pytest
import os
import time
import subprocess
from target.boot_control import BCB, read_bcb, write_bcb
from target.qemu_runner import launch_qemu, wait_for_output, kill_qemu, send_command

BCB_PATH = "build/bcb.bin"

@pytest.fixture(autouse=True)
def setup_bcb():
    # Make sure BCB is initialized to defaults before each test
    os.makedirs("build", exist_ok=True)
    write_bcb(BCB_PATH, BCB(sequence=0, active_slot='A', pending_slot='0', boot_attempts=0, confirmed=1))
    yield

def test_normal_boot():
    # Verify active slot A boots successfully
    proc = launch_qemu()
    try:
        wait_for_output(proc, "Welcome to Spacecraft Linux (Slot A)", timeout_s=15)
        send_command(proc, "cat /etc/slot_id")
        wait_for_output(proc, "A", timeout_s=5)
    finally:
        kill_qemu(proc)

def test_pending_slot_confirmed():
    # Set pending slot B
    bcb = read_bcb(BCB_PATH)
    bcb.pending_slot = 'B'
    bcb.confirmed = 0
    bcb.boot_attempts = 0
    write_bcb(BCB_PATH, bcb)
    
    # First boot of pending slot B
    proc = launch_qemu()
    try:
        wait_for_output(proc, "Welcome to Spacecraft Linux (Slot B)", timeout_s=15)
        # Verify slot B was chosen
        send_command(proc, "cat /etc/slot_id")
        wait_for_output(proc, "B", timeout_s=5)
        
        # Simulating successful ground confirmation: mark slot B active and confirmed
        confirm_bcb = read_bcb(BCB_PATH)
        confirm_bcb.active_slot = 'B'
        confirm_bcb.pending_slot = '0'
        confirm_bcb.boot_attempts = 0
        confirm_bcb.confirmed = 1
        write_bcb(BCB_PATH, confirm_bcb)
    finally:
        kill_qemu(proc)
        
    # Subsequent boot should boot into Slot B natively
    proc2 = launch_qemu()
    try:
        wait_for_output(proc2, "Welcome to Spacecraft Linux (Slot B)", timeout_s=15)
    finally:
        kill_qemu(proc2)

def test_pending_slot_unconfirmed_reverts():
    # Set pending slot B, unconfirmed
    bcb = read_bcb(BCB_PATH)
    bcb.pending_slot = 'B'
    bcb.confirmed = 0
    bcb.boot_attempts = 0
    write_bcb(BCB_PATH, bcb)
    
    # 1st boot attempt: increments to 1, we simulate power cut (kill)
    proc = launch_qemu()
    try:
        wait_for_output(proc, "Welcome to Spacecraft Linux (Slot B)", timeout_s=15)
    finally:
        kill_qemu(proc)
    assert read_bcb(BCB_PATH).boot_attempts == 1
    
    # 2nd boot attempt: increments to 2, we simulate power cut (kill)
    proc = launch_qemu()
    try:
        wait_for_output(proc, "Welcome to Spacecraft Linux (Slot B)", timeout_s=15)
    finally:
        kill_qemu(proc)
    assert read_bcb(BCB_PATH).boot_attempts == 2
    
    # 3rd boot attempt: increments to 3, we simulate power cut (kill)
    proc = launch_qemu()
    try:
        wait_for_output(proc, "Welcome to Spacecraft Linux (Slot B)", timeout_s=15)
    finally:
        kill_qemu(proc)
    assert read_bcb(BCB_PATH).boot_attempts == 3
    
    # 4th boot attempt: exceeds 3 attempts, should automatically revert back to active A!
    proc = launch_qemu()
    try:
        wait_for_output(proc, "Welcome to Spacecraft Linux (Slot A)", timeout_s=15)
    finally:
        kill_qemu(proc)
        
    # Verify BCB is back to healthy A
    final_bcb = read_bcb(BCB_PATH)
    assert final_bcb.active_slot == 'A'
    assert final_bcb.pending_slot == '0'
    assert final_bcb.confirmed == 1

def test_simulated_power_cut_bcb_consistency():
    # Verify that if Copy 1 is corrupt/invalid, system still boots from Copy 0
    # First, write valid default
    bcb = BCB(sequence=10, active_slot='A', pending_slot='0', boot_attempts=0, confirmed=1)
    write_bcb(BCB_PATH, bcb)
    
    # Overwrite Copy 1 (offset 128) with pure garbage to simulate mid-write power cut
    with open(BCB_PATH, "r+b") as f:
        f.seek(128)
        f.write(b"GARBAGE" * 16)
        
    # Read BCB on host: should resolve to Copy 0 and be valid
    host_bcb = read_bcb(BCB_PATH)
    assert host_bcb.active_slot == 'A'
    assert host_bcb.sequence == 10
    
    # Now, test that QEMU still boots Slot A successfully using Copy 0
    proc = launch_qemu()
    try:
        wait_for_output(proc, "Welcome to Spacecraft Linux (Slot A)", timeout_s=15)
    finally:
        kill_qemu(proc)
