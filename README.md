# Sysadmin Gym v4

Independent, outcome-oriented RHCSA-style command-line practice for a personal RHEL 10 virtual machine. Task scenarios are original and organized around RH124/RH134 subject areas; they are **not** copied Red Hat exam exercises.

## Requirements

- RHEL 10 VM with Python 3, Bash and standard system utilities.
- The practice catalog uses `shadow-utils`, `util-linux`, `xfsprogs`, `acl`, `openssh-clients` and OpenSSL where available. Exercises that require a missing tool are skipped during round selection.
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

Daily account tasks use databases under the exercise directory. Storage tasks use regular image files, and offline systemd tasks use a local system root. You can remove these resources with `./gym.sh reset`.

## Optional system tasks

Use a dedicated RHEL VM with a snapshot and a secondary practice interface. Replace `enp7s0` below with its interface name.

```bash
./gym.sh start --system --interface enp7s0
./gym.sh start --system --lab --interface enp7s0
```

System tasks include NetworkManager and firewalld. The extended lab adds persistent SELinux labeling and a tmpfs entry in `/etc/fstab`. These tasks change the actual VM configuration. Restore the VM snapshot after a system lab. Preserve `progress/` outside the VM to keep your history across snapshot restores.

Run Gym as a regular user, not with `sudo`. Use `sudo` only where the task calls for administrative operations. Basic daily tasks write inside `workspace/`.

## Test

```bash
python3 tests/smoke.py
python3 tests/practical.py
```

The smoke test covers the basic CLI workflow. The integration suite verifies isolated account, storage, networking and systemd exercises and reports any tool-dependent skips.
