# Sysadmin Gym v5.0.1 — Native RHEL

Practice actual RHCSA-style administration on a disposable RHEL 10 VM. Gym prepares the real system, presents English outcome-based exercises, checks the system state and records progress. The VM is the lab. There are no alternate account databases, offline configuration exercises or private namespace tasks in the active catalog.

## Setup

Use a dedicated VM and take a hypervisor snapshot. Install Python 3, sudo and the RHEL packages relevant to your exercises (NetworkManager, firewalld, policycoreutils-python-utils, httpd, lvm2, xfsprogs, e2fsprogs, parted, nfs-utils, autofs, rsyslog, chrony, tuned, cronie, openssh-server, curl, flatpak). Tasks whose required tools are missing are skipped. Internet access is needed for the Flatpak task and external time synchronization.

Attach a virtual network adapter and an additional virtual disk for networking and partitioning exercises. Gym automatically selects a physical VM interface (preferring a secondary one) and an unmounted disk. It does not prevent destructive operations by the trainee.

Run Gym as your regular user with sudo privileges:

```bash
./gym.sh start
./gym.sh hint 1
./gym.sh check
./gym.sh stats
./gym.sh reset
```

No device arguments are needed. If no suitable extra disk exists, Gym selects swap or tmpfs tasks instead. With only one physical NIC, networking tasks may change the primary connection; use the VM console. Seven tasks are selected by default using the existing adaptive history. Network rounds include address analysis (IPv4 or IPv6) alongside real interface exercises when available. More complex exercises may require more than 30 minutes or a reboot.

## Recovery

Preparation and your work modify the actual VM. Reset removes the workspace and records the round, but does not restore system configuration. History is optional and disposable: copy progress/ outside the snapshot only if you want to retain it. Restore the VM snapshot when desired. After reboot, use check on the existing session. Use the VM console if network or SSH access is broken.

## Distribution

Run scripts/package.sh in a checkout of this branch to build dist/sysadmin-gym-v5-0-1.tar.gz. See README-INSTALL.md. Existing module layout and exercise history are retained; old simulation-only task definitions are removed from the active catalog. This release requires native VM testing.
