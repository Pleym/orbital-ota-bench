import os
import shutil
import subprocess

def build_initramfs():
    base_dir = "/Users/dorian/orbital-ota-bench"
    build_dir = os.path.join(base_dir, "build")
    staging_dir = os.path.join(build_dir, "initramfs_staging")
    unpack_dir = os.path.join(build_dir, "unpack")
    
    # 1. Clean staging directory
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)
        
    # 2. Copy the entire official unpacked Alpine initramfs as our base!
    print("Copying Alpine initramfs base to staging...")
    shutil.copytree(unpack_dir, staging_dir, symlinks=True)
    
    # 3. Create required directories if they don't exist
    for d in ["sysroot", "mnt", "tmp", "proc", "sys", "dev"]:
        os.makedirs(os.path.join(staging_dir, d), exist_ok=True)
        
    # 4. Explicitly create symlinks under bin and sbin for our tools
    # All links should point to busybox
    tools = [
        "mount", "umount", "mkdir", "tar", "dd", "sha256sum", "hexdump", 
        "tr", "cut", "seq", "sync", "awk", "cat", "sleep", "reboot", 
        "touch", "ls", "grep", "sed", "find", "clear", "df", "chroot", "mdev", "chmod", "insmod",
        "basename", "switch_root"
    ]
    for tool in tools:
        # Some might go in /bin, some in /sbin. Let's put them in /bin
        link_path = os.path.join(staging_dir, "bin", tool)
        if os.path.exists(link_path):
            os.remove(link_path)
        os.symlink("busybox", link_path)
        
    # 5. Overwrite /init with our custom init_boot.sh
    init_src = os.path.join(base_dir, "target", "init_boot.sh")
    init_dst = os.path.join(staging_dir, "init")
    if os.path.exists(init_dst):
        os.remove(init_dst)
    shutil.copy(init_src, init_dst)
    os.chmod(init_dst, 0o755)
    
    # 6. Pack the staging directory into cpio.gz
    print("Packaging custom initramfs.cpio.gz...")
    initramfs_out = os.path.join(build_dir, "initramfs.cpio.gz")
    if os.path.exists(initramfs_out):
        os.remove(initramfs_out)
        
    cmd = "find . -print0 | cpio --null -o --format=newc | gzip -9 > ../initramfs.cpio.gz"
    subprocess.run(cmd, shell=True, cwd=staging_dir, check=True)
    
    print("initramfs.cpio.gz successfully created!")

if __name__ == "__main__":
    build_initramfs()
