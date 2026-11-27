# RHCSA lab coverage

This inventory tracks the 27 labs supplied as references. "Partial" means the
catalog covers some skills or uses an offline fixture. The RHEL workflows in
the remaining-work column still need practical exercises and validation.

| Reference | Current exercise or skill | Remaining work |
| --- | --- | --- |
| RH124 10 · Users and groups | — | Account and group lifecycle, supplementary membership, passwords and aging, scoped sudo |
| RH124 11 · File access | Permissions module, practical ACL | Collaborative directory scenarios and effective access checks |
| RH124 12 · RPM | Repository fixtures and installed RPM query | Build a signed offline package fixture and practice install and upgrade |
| RH124 14 · Removable media | File audits and disk usage | Mount and unmount an isolated filesystem |
| RH124 15 · Processes | Process signaling | Identify and manage controlled CPU load |
| RH124 16 · Services | Recovery service fixture | Start, stop, enable and disable a disposable unit |
| RH124 18 · Network configuration | NetworkManager keyfile fixture | Assign and verify multiple addresses on isolated interfaces |
| RH124 19 · SSH | Ed25519 key generation | Verify key authentication and SSH daemon policy on an isolated listener |
| RH124 20 · Manage a server | SSH key and repository fixtures | Secure SSH login and perform package transactions |
| RH124 20 · Manage files | Files and shell modules | Cross-check all lab steps against existing exercise IDs |
| RH124 20 · Manage networks | Network diagnostics and resolver fixture | Static hostname, local name resolution, and isolated routing practice |
| RH124 20 · Users, permissions and processes | ACL and process signaling | Account lifecycle and controlled CPU load |
| RH124 20 · Mount and find | File audits | Mount an isolated filesystem and audit its contents |
| RH134 1 · Shell scripting | Parameterized executable shell report | Add a loop and redirected-output scenario |
| RH134 5 · Logging | `recovery-journal`, log retention | Timezone, journal rotation, and routing authentication events |
| RH134 6 · SELinux | Optional SELinux context task | Diagnose denial evidence and verify a scoped policy correction |
| RH134 8 · Transfer | SSH key generation | Local isolated rsync and SCP endpoints |
| RH134 9 · Tuning | Process observations | Tune a disposable process and practice profile selection |
| RH134 10 · Basic storage | `recovery-swap-fstab`, sparse image | Partition and format an isolated image and validate activation |
| RH134 11 · LVM | fstab fixture | Create and extend an isolated logical volume and filesystem |
| RH134 12 · Boot | `recovery-boot-mount` | Diagnose boot evidence and select a default target in a fixture |
| RH134 13 · Superuser recovery | — | Practice recovery decisions on a mock boot transcript and isolated account state |
| RH134 14 · Network security | Firewalld zone fixture and optional port task | Combined web service, scoped firewall and SELinux troubleshooting |
| RH134 15 · Network storage | `recovery-nfs-mount` | Implement an isolated NFS endpoint and autofs map scenario |
| RH134 19 · Boot and maintenance | `recovery-boot-mount`, `recovery-timer`, cron fragment | Validate default target and run a scheduled job |
| RH134 19 · Storage | `recovery-nfs-mount`, `recovery-swap-fstab`, `recovery-tmpfiles` | Validate live outcomes using disposable resources |
| RH134 19 · Server security | SSH key, firewall and optional SELinux exercises | Isolated SSH authentication and SELinux boolean diagnostics |

The catalog total includes parameterized templates. Count distinct outcomes
separately when evaluating the exercise target.
