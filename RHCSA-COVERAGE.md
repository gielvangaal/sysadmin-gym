# Native RHEL practice coverage

The v5 active catalog uses the real RHEL installation. Existing shell, file, process and permission drills remain. Native exercises cover local accounts, password aging, sudo, hostnames, timezone, chrony, systemd services and timers, cron, journald, rsyslog, tmpfiles, SELinux, firewalld, IPv4/IPv6 addressing, routes and DNS, SSH server policy, real RPM transactions and DNF repositories, Flatpak, swap, tmpfs, XFS, ext4, LVM, NFS, autofs, TuneD, default target and persistent boot arguments.

Device exercises need --interface and --disk. Some tasks require optional packages or Internet access. The catalog is not a claim of exhaustive EX200 coverage. Interactive root password recovery, a genuinely boot-blocking fstab fault, full LVM extension and a multi-host SSH setup remain to be added as native scenarios. Real VM validation is required.
