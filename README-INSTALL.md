# Sysadmin Gym — clean installation

Extract the complete distribution into a new directory. No Git checkout or engine upgrade is required on the practice VM.

Before replacing an old installation, finish or reset the active session and preserve your existing history. Copy the old `progress/events.jsonl` (or `history/events.jsonl` in v3) to `progress/events.jsonl` in the new installation. If you also have old counters in `progress.json` or `progress/legacy.json`, copy them to `progress/legacy.json`. Check the imported history with `./gym.sh stats` before removing your old installation.

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

To build a clean distribution from a Git checkout, run `./scripts/package.sh`.
The bundled training RPMs are built from `fixtures/gym-workload.spec`.
Rebuild them with `./scripts/build-rpm-fixtures.sh` when changing that source.
The build requires GnuPG, RPM build and signing tools, and createrepo_c.
The archive contains the public key and signed fixtures for this exercise.
