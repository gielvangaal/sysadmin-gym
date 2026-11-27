# RHCSA lab coverage

The 27 references below map to original Sysadmin Gym exercises. Use the exercise
IDs to find the templates in `modules/*/tasks.json`. A reference can map to
several short exercises, and a single skill can appear in several references.

## Validation on a single VM

Daily rounds use ordinary user permissions. They combine live files, processes,
local package transactions and protocol tools with offline configuration
fixtures. User namespaces and a running systemd user manager enable additional
live practice. Gym detects these capabilities before selecting exercises.

The optional storage round uses real loop devices, LVM, XFS and swap on the
RHEL VM. The opt-in system round uses the VM's secondary interface and lets
you practice live firewalld and SELinux. The cloud test suite covers the
storage grader and cleanup checks against representative kernel state. Run
the privileged exercise workflows on the practice VM.

## RH124

| Reference | Skills and exercise IDs or modules |
| --- | --- |
| 10 · Users and groups | Create a group and user, repair supplementary membership, set account expiration and inactivity, configure password aging and rotation, and validate constrained sudo. See `practical-accounts`, `practical-membership`, `practical-expiry`, `workbench-login-policy`, `workbench-account-rotate` and `workbench-sudo-scope`. |
| 11 · File access | Mode bits, umask, group inheritance, sticky directories and named/default ACLs. See `permissions`, `practical-shared-directory` and `workbench-acl-inherit`. |
| 12 · Software and RPM | Repair and query a signed DNF repository. Install, upgrade and remove original signed packages in an isolated RPM database. See `workbench-dnf-repo` and `workbench-rpm-install`, `workbench-rpm-upgrade` and `workbench-rpm-remove`. |
| 14 · Removable media | Attach and mount a loop-backed XFS volume, inspect disk usage and find files using compound predicates. See `storage-live-xfs`, `observe` and the file audits. |
| 15 · Processes | Find a controlled worker, suspend and resume it without replacing it, and terminate a disposable process. See `workbench-process-pause`, `workbench-process-resume` and `observe`. |
| 16 · Services | Start and stop transient user services and enable or disable system services in an isolated system root. See `workbench-service-start`, `workbench-service-stop`, `practical-service-enable`, `workbench-unit-disable`. |
| 18 · Network configuration | Configure two IPv4 addresses and a static route in a namespace, build an offline NetworkManager profile and practice live NetworkManager on a dedicated interface. See `network-network-addrs`, `network-network-routing`, `recovery-network-dual`, `recovery-network-route` and the system module. |
| 19 · SSH | Generate a disposable key pair and validate effective daemon policy for public-key authentication, root login and password login. See `practical-sshkey` and `recovery-ssh-policy`. The daemon policy is checked offline. |
| 20 · Manage a server | Combine SSH key and policy work with signed repository repair and package transactions. See chapters 12 and 19 above. |
| 20 · Manage files | Create and copy directory trees, capture output, edit text, and distinguish hard and symbolic links. See `files`, `shell`, `practical-links` and `practical-sed`. |
| 20 · Manage networks | Repair a hostname and hosts entries, test connectivity and troubleshoot profiles and routing. See `workbench-hosts`, `network` and `recovery-network-route`. |
| 20 · Users, permissions and processes | Combine local account databases, password policy, umask and collaborative permissions with controlled process management. See chapters 10, 11 and 15 above. |
| 20 · Mount and find | Mount an exercise filesystem and audit names, sizes and modes. See `storage-live-xfs` and the file audits in `files`. |

## RH134

| Reference | Skills and exercise IDs or modules |
| --- | --- |
| 1 · Shell scripting | Use positional arguments, loops, conditions, redirected reports and multiple test inputs. See `practical-script`, `workbench-loop-report` and `shell`. |
| 5 · Logging | Repair an offline timezone, persistent journald storage and rotation, and rsyslog facility/priority routing. Practice retention on real files. See `workbench-timezone`, `recovery-journal`, `recovery-journal-rotation`, `workbench-auth-log` and `practical-retention`. |
| 6 · SELinux | Diagnose an AVC and repair the persistent file-context mapping. The optional system module covers real file labeling. See `workbench-selinux-context` and the system module. |
| 8 · Transfer | Run rsync with preservation and reconciliation and use the OpenSSH SFTP subsystem in direct mode. See `workbench-rsync-mirror` and `workbench-sftp-transfer`. These use local endpoints. |
| 9 · Tuning | Use a real process's scheduling priority and repair a TuneD profile based on balanced. See `workbench-process-nice` and `workbench-tuning-profile`. |
| 10 · Basic storage | Create GPT partitions, format XFS, mount it, prepare and activate swap, and repair persistence. See `practical-gpt-image`, `practical-xfs-image`, `practical-swap-image`, `storage-live-xfs`, `storage-live-swap` and `recovery-swap-fstab`. |
| 11 · LVM | Mark a PV partition, plan PV/VG/LV layout, extend a live VG and LV, grow XFS, and repair mount persistence. See `workbench-lvm-partition`, `workbench-lvm-layout`, `storage-live-lvm` and `workbench-lv-persistence`. |
| 12 · Boot | Diagnose boot-blocking device references and optional mounts, then repair the default target in an isolated system root. See `workbench-boot-uuid`, `recovery-boot-mount` and `practical-boot-target`. |
| 13 · Superuser recovery | Restore access in a staged offline credential database and require rotation. See `workbench-recovery-shadow`. This deliberately uses an exercise disk state instead of rebooting the practice VM. |
| 14 · Network security | Diagnose the HTTP SELinux port denial, repair a constrained firewalld zone, and practice the live port rule in the system module. See `workbench-selinux-ports`, `workbench-firewall-source` and `system`. |
| 15 · Network storage | Repair NFS export scope, persistent mount settings and an indirect autofs map. See `workbench-nfs-export`, `recovery-nfs-mount` and `recovery-autofs-map`. These use offline client and server configuration fixtures. |
| 19 · Boot and maintenance | Diagnose boot, set its default target, write a cron schedule and run a real user timer. See `workbench-boot-uuid`, `practical-boot-target`, `practical-cron`, `recovery-timer` and `workbench-timer-run`. |
| 19 · Storage and filesystems | Combine real LVM and swap, a persistent NFS mount definition and temporary-directory rules. See the storage module, `recovery-nfs-mount`, `recovery-swap-fstab` and `practical-tmpfiles-apply`. |
| 19 · Server security | Validate effective SSH policy, source-scoped firewalld, SELinux enforcing mode, NFS-home boolean, file context and HTTP port correction. See `recovery-ssh-policy`, `workbench-firewall-source` and the four `workbench-selinux-*` exercises. |
