# Clean installation

Build the archive on the Git checkout with `./scripts/package.sh`, transfer dist/sysadmin-gym-v5.tar.gz to the dedicated RHEL 10 VM and extract into a new directory. Preserve the existing progress/ directory separately, then copy it into the new installation. Do not copy workspace/ or session.json from v4.

Take a VM snapshot before starting. Use the console and give your normal user sudo privileges.

```bash
./gym.sh stats
./gym.sh start --interface enp7s0 --disk /dev/vdb
./gym.sh check
./gym.sh reset
```

Replace the interface and disk with actual VM device names. Both arguments are optional but required for exercises involving those devices. Reset does not undo native system changes. Use snapshots to restore the machine; preserve progress outside the snapshot. No automatic system rollback is implemented.
