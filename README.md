# Linux Gym v3 — English edition

Independent, outcome-oriented RHCSA-style command-line practice for a personal RHEL 10 virtual machine. Task scenarios are original and organized around RH124/RH134 subject areas; they are **not** copied Red Hat exam exercises.

## Requirements

- RHEL 10 VM with Python 3, Bash and standard system utilities.
- Optional `curl` for HTTP tasks and `semanage` (`policycoreutils-python-utils`) for SELinux labs.
- No registration, cloud account, AI service, or network API is required to run the application itself.
- An existing VM snapshot is strongly recommended before privileged system labs.

## Install

Transfer the zip to your VM and run:

```bash
unzip linux-gym-v3-en.zip
cd linux-gym-v3
./gym.sh list
./gym.sh start
```

If the VM does not have `unzip`, extract on the openSUSE host and transfer the entire directory with `scp -r` instead.

## Daily session (approximately 30 minutes)

```bash
./gym.sh start                # 7 tasks from several domains
./gym.sh hint 3               # one hint for task 3
./gym.sh check                # check the actual results
./gym.sh stats                # historical results
./gym.sh reset                # clean the practice workspace
```

Prompts describe desired outcomes rather than giving you the commands. Pass/fail reflects the result for each task. Some observational exercises use approximate checks; they are practice, not an official RHCSA grading system. Repeated failures increase a task's probability of being selected again.

## Optional system tasks

The VM has a management interface (`enp1s0`) and a secondary practice interface (`enp7s0`). You can practice on the latter, but both currently share a NAT network, so caution is still appropriate.

```bash
./gym.sh start --system --interface enp7s0
./gym.sh start --system --lab --interface enp7s0
```

System tasks include NetworkManager and firewalld. The extended lab adds persistent SELinux labeling and a tmpfs entry in `/etc/fstab`. These tasks change the actual VM configuration. **`./gym.sh reset` deliberately refuses to undo a system lab.** Restore the VM snapshot using virt-manager instead. Preserve `progress.json` outside the VM if you want to retain progress across snapshot reverts.

Run Gym as a regular user, not with `sudo`. Use `sudo` only where the task calls for administrative operations. Basic daily tasks write inside `workspace/`.

## Test

```bash
python3 tests/smoke.py
```

The smoke test checks the basic CLI workflow on the machine running it. It does not test privileged modifications to your RHEL VM.
