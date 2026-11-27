# RHCSA lab coverage

This inventory tracks the 27 labs supplied as references. The remaining-work
column identifies lab outcomes that still need practical exercises or live RHEL
validation. The same exercise can cover a skill in several reference labs.

| Reference | Current exercise or skill | Remaining work |
| --- | --- | --- |
| RH124 10 · Users and groups | `practical-accounts`, `practical-membership`, `practical-expiry` | Password initialization and policy, additional account lifecycle cases, scoped sudo |
| RH124 11 · File access | Permissions module, practical ACL, `practical-shared-directory` | Effective access checks across multiple users |
| RH124 12 · RPM | Repository fixtures and installed RPM query | Build a signed offline package fixture and practice install and upgrade |
| RH124 14 · Removable media | File audits and disk usage | Mount and unmount an isolated filesystem |
| RH124 15 · Processes | Process signaling | Identify and manage controlled CPU load |
| RH124 16 · Services | Recovery service fixture and `practical-service-enable` | Live start, stop and disable |
| RH124 18 · Network configuration | `recovery-network-dual` | Assign and verify multiple addresses on an isolated interface |
| RH124 19 · SSH | Ed25519 key generation and `recovery-ssh-policy` (effective daemon configuration) | Verify a live key-authenticated login on an isolated listener |
| RH124 20 · Manage a server | SSH key, effective SSH policy and repository fixtures | Verify live SSH login and perform package transactions |
| RH124 20 · Manage files | Files and shell modules | Cross-check all lab steps against existing exercise IDs |
| RH124 20 · Manage networks | Network diagnostics, resolver fixture and `recovery-network-route` | Static hostname, local name resolution and live isolated routing practice |
| RH124 20 · Users, permissions and processes | ACL, isolated account database exercises and process signaling | Controlled CPU load and further account lifecycle tasks |
| RH124 20 · Mount and find | File audits | Mount an isolated filesystem and audit its contents |
| RH134 1 · Shell scripting | Parameterized executable shell report | Add a loop and redirected-output scenario |
| RH134 5 · Logging | `recovery-journal`, `recovery-journal-rotation`, log retention | Timezone, live journal rotation and routing authentication events |
| RH134 6 · SELinux | Optional SELinux context task | Diagnose denial evidence and verify a scoped policy correction |
| RH134 8 · Transfer | SSH key generation | Local isolated rsync and SCP endpoints |
| RH134 9 · Tuning | Process observations | Tune a disposable process and practice profile selection |
| RH134 10 · Basic storage | `practical-gpt-image`, `practical-xfs-image`, `practical-swap-image`, `recovery-swap-fstab` | Partition-to-filesystem workflow, mounting and swap activation |
| RH134 11 · LVM | fstab fixture | Create and extend an isolated logical volume and filesystem |
| RH134 12 · Boot | `recovery-boot-mount`, `practical-boot-target` | Diagnose boot evidence and repair additional boot issues |
| RH134 13 · Superuser recovery | — | Practice recovery decisions on a mock boot transcript and isolated account state |
| RH134 14 · Network security | Firewalld zone fixture and optional port task | Combined web service, scoped firewall and SELinux troubleshooting |
| RH134 15 · Network storage | `recovery-nfs-mount`, `recovery-autofs-map` | Validate live NFS and autofs outcomes against an isolated export |
| RH134 19 · Boot and maintenance | `recovery-boot-mount`, `practical-boot-target`, `recovery-timer`, cron fragment | Run and verify a scheduled job |
| RH134 19 · Storage | `recovery-nfs-mount`, `recovery-swap-fstab`, `practical-swap-image`, `practical-tmpfiles-apply` | Live NFS mount, swap and LVM workflows |
| RH134 19 · Server security | SSH key, effective SSH policy, firewall and optional SELinux exercises | Live SSH authentication and SELinux boolean diagnostics |

The catalog total includes parameterized templates. Count distinct outcomes
separately when evaluating the exercise target.
