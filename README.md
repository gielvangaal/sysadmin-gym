# Sysadmin Gym v4

Independent, outcome-oriented RHCSA-style command-line practice for a personal RHEL 10 virtual machine. Task scenarios are original and organized around RH124/RH134 subject areas; they are **not** copied Red Hat exam exercises.

## Requirements

- RHEL 10 VM with Python 3, Bash and standard system utilities.
- Install `shadow-utils`, `util-linux`, `xfsprogs`, `acl`, `openssh-clients`, `openssh-server`, `rsync`, `rpm`, `dnf`, `sudo` and OpenSSL for the broadest daily catalog. Gym selects exercises it can run with the available tools and Linux capabilities.
- Optional `curl` for HTTP tasks and `semanage` (`policycoreutils-python-utils`) for SELinux labs.
- No registration, cloud account, AI service, or network API is required to run the application itself.
- An existing VM snapshot is strongly recommended before privileged system labs.

## Install

Transfer the distribution archive to your VM and extract it into a new directory.

```bash
mkdir sysadmin-gym
tar -xzf sysadmin-gym-v4.tar.gz -C sysadmin-gym
cd sysadmin-gym
./gym.sh list
./gym.sh start
```

See [installation and progress restoration](README-INSTALL.md) and the [RHCSA lab coverage inventory](RHCSA-COVERAGE.md).

## Daily session (approximately 30 minutes)

```bash
./gym.sh start                # 7 tasks from several domains
./gym.sh hint 3               # one hint for task 3
./gym.sh check                # check the actual results
./gym.sh stats                # historical results
./gym.sh reset                # clean the practice workspace
```

Prompts describe the expected outcomes. Progress uses the first check for each exercise in a round. Missed exercises appear more frequently, and the default round includes two networking exercises.

Daily account tasks use databases under the exercise directory. Storage tasks operate on regular image files, and offline systemd tasks use a local system root. Where supported, daily tasks can run in a private namespace or use disposable units in your existing systemd user manager. Gym cleans up these resources with `./gym.sh reset`. The bundled RPMs and DNF metadata are signed with a disposable lab key that is used inside the exercise.

## Optional system tasks

Use a dedicated RHEL VM with a snapshot and a secondary practice interface. Replace `enp7s0` below with its interface name.

```bash
./gym.sh start --system --interface enp7s0
./gym.sh start --system --lab --interface enp7s0
```

System tasks include NetworkManager and firewalld. The extended lab adds persistent SELinux labeling and a tmpfs entry in `/etc/fstab`. These tasks change the actual VM configuration. Restore the VM snapshot after a system lab. Preserve `progress/` outside the VM to keep your history across snapshot restores.

Run Gym as a regular user, not with `sudo`. Use `sudo` only where the task calls for administrative operations. Basic daily tasks write inside `workspace/`.

## Optional storage round

On the practice VM with `lvm2`, `xfsprogs` and `util-linux`, run
`./gym.sh start --storage-lab` to include loop-backed XFS, LVM and swap.
Run Gym as your regular user. Use administrative privileges only for the
storage operations shown in the exercise. For each image, match the loop
device to the exact backing file. Keep LVM scans scoped with `--devices`.
For exercise VGs, use `--config 'backup { backup=0 archive=0 }'` to keep
metadata backups out of the VM's LVM configuration directories.

After grading, unmount the exercise mount points, deactivate the named
exercise VG, detach its loop devices and disable the exercise swap file.
Reset checks for active storage before removing the workspace.

## Test

```bash
python3 tests/smoke.py
python3 tests/practical.py
python3 tests/workbench.py
python3 tests/storage.py
```

The smoke test covers the basic CLI workflow. The integration suites verify isolated outcomes, signed package transactions, protocol transfers and storage reset guards. They report capability-dependent skips. Use the dedicated RHEL 10 VM for the privileged workflows.
