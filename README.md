# Sysadmin Gym v5 — Native RHEL

Practice actual RHCSA-style administration on a disposable RHEL 10 VM. Gym prepares the real system, presents English outcome-based exercises, checks the system state and records progress. The VM is the lab. There are no alternate account databases, offline configuration exercises or private namespace tasks in the active catalog.

## Setup

Use a dedicated VM and take a hypervisor snapshot. Install Python 3, sudo and the RHEL packages relevant to your exercises (NetworkManager, firewalld, policycoreutils-python-utils, httpd, lvm2, xfsprogs, e2fsprogs, parted, nfs-utils, autofs, rsyslog, chrony, tuned, cronie, openssh-server, curl, flatpak). Tasks whose required tools are missing are skipped. Internet access is needed for the Flatpak task and external time synchronization.

Attach a virtual network adapter and an additional virtual disk for networking and partitioning exercises. Use real device names from ip link and lsblk. Gym does not protect the selected device from destructive operations.

Run Gym as your regular user with sudo privileges:

```bash
./gym.sh start --interface enp7s0 --disk /dev/vdb
./gym.sh hint 1
./gym.sh check
./gym.sh stats
./gym.sh reset
```

With no interface or disk argument, ordinary rounds still include native administration, firewall, swap and tmpfs; physical interface and disk exercises are omitted. Supply both arguments for full practice. Seven tasks are selected by default using the existing adaptive history. More complex exercises may require more than 30 minutes or a reboot.

## Recovery

Preparation and your work modify the actual VM. Reset removes the workspace and records the round, but does not restore system configuration. Save progress/events.jsonl and progress/legacy.json outside the snapshot, then restore the VM snapshot when desired. After reboot, use check on the existing session. Use the VM console if network or SSH access is broken.

## Distribution

Run scripts/package.sh in a checkout of this branch to build dist/sysadmin-gym-v5.tar.gz. See README-INSTALL.md. Existing module layout and exercise history are retained; old simulation-only task definitions are removed from the active catalog. This release requires native VM testing.
