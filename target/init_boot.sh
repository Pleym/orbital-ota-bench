#!/bin/sh

export PATH="/bin:/sbin:/usr/bin:/usr/sbin"

# Mount virtual filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev

# Mount tmpfs on /tmp for temporary files
mount -t tmpfs tmpfs /tmp

echo "=========================================="
echo "=== ORBITAL OTA BOOTLOADER ==="
echo "=========================================="

# Load virtio transport and block modules
echo "Loading virtio modules..."
insmod /lib/modules/6.6.110-0-lts/kernel/drivers/virtio/virtio.ko
insmod /lib/modules/6.6.110-0-lts/kernel/drivers/virtio/virtio_ring.ko
insmod /lib/modules/6.6.110-0-lts/kernel/drivers/virtio/virtio_pci.ko
insmod /lib/modules/6.6.110-0-lts/kernel/drivers/virtio/virtio_mmio.ko
insmod /lib/modules/6.6.110-0-lts/kernel/drivers/block/virtio_blk.ko

# Populate /dev nodes
mdev -s

# Define device paths
# In QEMU:
# /dev/vda -> BCB persistent block (128 bytes Copy 0, 128 bytes Copy 1)
# /dev/vdb -> Slot A tar archive
# /dev/vdc -> Slot B tar archive

BCB_DEV="/dev/vda"

# Helpers to read and write u64 / binary values
printf_u64() {
    val=$1
    b1=$((val & 255))
    b2=$(((val >> 8) & 255))
    b3=$(((val >> 16) & 255))
    b4=$(((val >> 24) & 255))
    b5=$(((val >> 32) & 255))
    b6=$(((val >> 40) & 255))
    b7=$(((val >> 48) & 255))
    b8=$(((val >> 56) & 255))
    printf "\\x$(printf %02x $b1)\\x$(printf %02x $b2)\\x$(printf %02x $b3)\\x$(printf %02x $b4)\\x$(printf %02x $b5)\\x$(printf %02x $b6)\\x$(printf %02x $b7)\\x$(printf %02x $b8)"
}

parse_le_hex() {
    hex=$1
    len=${#hex}
    val=0
    multiplier=1
    i=0
    while [ $i -lt $len ]; do
        byte=$(echo $hex | cut -c$((i+1))-$((i+2)))
        dec_val=$(printf "%d" 0x$byte)
        val=$((val + dec_val * multiplier))
        multiplier=$((multiplier * 256))
        i=$((i + 2))
    done
    echo $val
}

verify_copy() {
    copy_num=$1
    offset=$((copy_num * 128))
    
    # Extract 96 bytes of header data
    dd if=$BCB_DEV bs=1 skip=$offset count=96 of=/tmp/header_c${copy_num} 2>/dev/null
    
    # Verify we got 96 bytes and magic is BCB!
    magic=$(dd if=/tmp/header_c${copy_num} bs=1 count=4 2>/dev/null)
    if [ "$magic" != "BCB!" ]; then
        return 1
    fi
    
    # Compute SHA256 of header data
    computed=$(sha256sum /tmp/header_c${copy_num} | awk '{print $1}')
    
    # Extract 32 bytes of stored checksum
    stored=$(dd if=$BCB_DEV bs=1 skip=$((offset + 96)) count=32 2>/dev/null | hexdump -ve '1/1 "%02x"')
    
    if [ "$computed" = "$stored" ]; then
        return 0
    else
        return 1
    fi
}

write_copy() {
    offset=$1
    seq=$2
    active=$3
    pending=$4
    attempts=$5
    confirmed=$6
    
    # Generate 96-byte header
    (
        printf "BCB!"
        printf_u64 $seq
        printf "$active"
        printf "$pending"
        printf "\\x$(printf %02x $attempts)"
        printf "\\x$(printf %02x $confirmed)"
        # 80 bytes of zero padding
        for i in $(seq 1 80); do printf "\\x00"; done
    ) > /tmp/header_new
    
    # Compute SHA-256 of the 96 bytes
    hex_sha=$(sha256sum /tmp/header_new | awk '{print $1}')
    
    # Convert 32-byte hex string into binary bytes
    (
        for i in $(seq 0 31); do
            byte=$(echo $hex_sha | cut -c$((i*2+1))-$((i*2+2)))
            printf "\\x$byte"
        done
    ) > /tmp/checksum_new
    
    # Combine header and checksum (total 128 bytes)
    cat /tmp/header_new /tmp/checksum_new > /tmp/copy_new
    
    # Write to device at offset
    dd if=/tmp/copy_new of=$BCB_DEV bs=1 seek=$offset count=128 conv=notrunc 2>/dev/null
}

write_bcb_atomic() {
    seq=$1
    active=$2
    pending=$3
    attempts=$4
    confirmed=$5
    
    # Write Copy 0 (offset 0), fsync, then Copy 1 (offset 128), fsync
    write_copy 0 $seq "$active" "$pending" $attempts $confirmed
    sync
    write_copy 128 $seq "$active" "$pending" $attempts $confirmed
    sync
}

# Ensure BCB device exists
echo "=== Debug block devices ==="
ls -l /dev/vd*
ls -l /sys/block
cat /proc/partitions
echo "==========================="

if [ ! -b "$BCB_DEV" ] && [ ! -f "$BCB_DEV" ]; then
    echo "Warning: BCB device $BCB_DEV not found. Initializing virtual BCB file."
    touch $BCB_DEV
fi

# Read and verify BCB copies
verify_copy 0
c0_ok=$?
verify_copy 1
c1_ok=$?

if [ $c0_ok -eq 0 ] && [ $c1_ok -eq 0 ]; then
    # Both valid, read sequence hex and select highest sequence
    seq0_hex=$(hexdump -s 4 -n 8 -e '1/1 "%02x"' /tmp/header_c0 | tr -d ' ')
    seq1_hex=$(hexdump -s 4 -n 8 -e '1/1 "%02x"' /tmp/header_c1 | tr -d ' ')
    seq0=$(parse_le_hex $seq0_hex)
    seq1=$(parse_le_hex $seq1_hex)
    if [ $seq0 -ge $seq1 ]; then
        cp_selected=0
    else
        cp_selected=1
    fi
elif [ $c0_ok -eq 0 ] ; then
    cp_selected=0
elif [ $c1_ok -eq 0 ] ; then
    cp_selected=1
else
    # Initialize default BCB state (Slot A, sequence 0, pending '0', attempts 0, confirmed 1)
    echo "BCB invalid or uninitialized. Initializing to defaults (Slot A)."
    write_bcb_atomic 0 "A" "0" 0 1
    cp_selected=0
    verify_copy 0
fi

# Load state from selected copy header
hdr="/tmp/header_c${cp_selected}"
seq_hex=$(hexdump -s 4 -n 8 -e '1/1 "%02x"' $hdr | tr -d ' ')
seq=$(parse_le_hex $seq_hex)

active_slot=$(dd if=$hdr bs=1 skip=12 count=1 2>/dev/null)
pending_slot=$(dd if=$hdr bs=1 skip=13 count=1 2>/dev/null)

attempts_hex=$(hexdump -s 14 -n 1 -e '1/1 "%02x"' $hdr | tr -d ' ')
boot_attempts=$(printf "%d" 0x$attempts_hex)

confirmed_hex=$(hexdump -s 15 -n 1 -e '1/1 "%02x"' $hdr | tr -d ' ')
confirmed=$(printf "%d" 0x$confirmed_hex)

echo "Current BCB State:"
echo "  Sequence: $seq"
echo "  Active Slot: $active_slot"
echo "  Pending Slot: $pending_slot"
echo "  Boot Attempts: $boot_attempts"
echo "  Confirmed: $confirmed"

target_slot=""
revert_triggered=0

if [ "$pending_slot" = "A" ] || [ "$pending_slot" = "B" ]; then
    target_slot=$pending_slot
    boot_attempts=$((boot_attempts + 1))
    
    if [ $boot_attempts -gt 3 ]; then
        echo "WARNING: Boot attempts exceeded limit (3). Auto-reverting to active slot!"
        revert_triggered=1
        target_slot=$active_slot
        pending_slot="0"
        boot_attempts=0
        confirmed=1
    fi
else
    target_slot=$active_slot
    boot_attempts=0
    confirmed=1
fi

# Write updated state atomically
next_seq=$((seq + 1))
echo "Updating BCB state to target slot $target_slot (attempts: $boot_attempts)..."
write_bcb_atomic $next_seq "$active_slot" "$pending_slot" $boot_attempts $confirmed

# Select raw tar archive device based on target slot
# Slot A is on /dev/vdc, Slot B is on /dev/vdb
TAR_DEV=""
if [ "$target_slot" = "A" ]; then
    TAR_DEV="/dev/vdc"
else
    TAR_DEV="/dev/vdb"
fi

echo "Mounting tmpfs root filesystem..."
mkdir -p /sysroot
mount -t tmpfs tmpfs /sysroot

echo "Extracting Slot $target_slot rootfs from $TAR_DEV..."
TAR_DEV_NAME=$(basename $TAR_DEV)
if [ -f "/sys/block/$TAR_DEV_NAME/size" ]; then
    sectors=$(cat "/sys/block/$TAR_DEV_NAME/size")
    dd if=$TAR_DEV bs=512 count=$sectors 2>/dev/null | tar -xf - -C /sysroot
else
    tar -xf $TAR_DEV -C /sysroot
fi

if [ $? -ne 0 ] && [ ! -f /sysroot/sbin/init ]; then
    echo "ERROR: Failed to extract Slot $target_slot rootfs!"
    # Emergency shell or fallback
    /bin/sh
fi

# Ensure dev/proc/sys directories exist inside target rootfs
mkdir -p /sysroot/dev /sysroot/proc /sysroot/sys /sysroot/tmp

# Clean up and pivot
echo "Pivoting to Slot $target_slot userspace..."
mount --move /dev /sysroot/dev
mount --move /proc /sysroot/proc
mount --move /sys /sysroot/sys

exec switch_root /sysroot /sbin/init
