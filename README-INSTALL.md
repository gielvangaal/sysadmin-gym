# Clean installation

Build the archive on the Git checkout with `./scripts/package.sh`, transfer dist/sysadmin-gym-v5-0-1.tar.gz to the dedicated RHEL 10 VM and extract into a new directory. Optionally copy the existing progress/ directory into the new installation to retain history; a fresh installation works without it. Do not copy workspace/ or session.json from v4.

Take a VM snapshot before starting. Use the console and give your normal user sudo privileges.

```bash
./gym.sh stats
./gym.sh start
./gym.sh check
./gym.sh reset
```

Gym discovers the interface and disk automatically. Attach an extra virtual disk if you want partitioning and LVM tasks; no arguments are required. Reset does not undo native system changes. Use snapshots to restore the machine; optionally preserve progress outside the snapshot. No automatic system rollback is implemented.
