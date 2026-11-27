# Sysadmin Gym — clean installation

Extract the complete distribution into a new directory. No Git checkout or engine upgrade is required on the practice VM.

Before replacing an old installation, finish or reset the active session and preserve your existing event history (`history/events.jsonl` in v3). Copy it to `progress/events.jsonl` in the new installation. Optionally copy the old `progress.json` to `progress/legacy.json`. Never delete an old installation until the backup is verified.

Run:
```bash
./gym.sh start
./gym.sh check
./gym.sh hint 1
./gym.sh reset
./gym.sh stats
```

The progress directory is user data and must not be included in distribution archives. Modules remain independently organized. Existing module-only updates remain supported for compatible exercise kinds.

Use a dedicated practice VM. Persistent system labs require explicit opt-in and a VM snapshot. Ordinary sessions must not change management connectivity or existing disks.
