"""Outcome and teardown checks for the workbench exercise pack."""
import os
import signal
import shutil
import subprocess
import time
import unittest
from pathlib import Path

import practical
from practical import cli


class WorkbenchExercises(practical.ExerciseCase):
    def exercise(self, name, *tools):
        return super().exercise('workbench-' + name, *tools)

    def test_process_pause(self):
        task, root = self.exercise('process-pause')
        self.addCleanup(cli.workbench.stop_workers, root.parent)
        pid = task['worker']['pid']
        os.kill(pid, signal.SIGSTOP)
        for _ in range(50):
            if self.grade(task):
                break
            time.sleep(0.01)
        self.assertTrue(self.grade(task))
        cli.workbench.stop_workers(root.parent)
        for _ in range(50):
            if not self.grade(task):
                break
            time.sleep(0.01)
        self.assertFalse(self.grade(task))

    def test_process_nice(self):
        task, root = self.exercise('process-nice')
        self.addCleanup(cli.workbench.stop_workers, root.parent)
        os.setpriority(os.PRIO_PROCESS, task['worker']['pid'], task['nice'])
        self.assertTrue(self.grade(task))

    def test_login_policy(self):
        task, root = self.exercise('login-policy')
        (root / 'login.defs').write_text(
            f'PASS_MIN_DAYS 2\nPASS_WARN_AGE 5\nPASS_MAX_DAYS {task["number"]}\n'
        )
        self.assertTrue(self.grade(task))

    def test_account_rotate(self):
        task, root = self.exercise('account-rotate', 'openssl')
        shadow = root / 'shadow'
        password = subprocess.check_output(
            ['openssl', 'passwd', '-6', '-salt', 'gymsalt', task['password']], text=True
        ).strip()
        shadow.write_text(f'gymintern:{password}:20000:0:99999:7:::\n')
        self.assertFalse(self.grade(task))
        shadow.write_text(f'gymintern:{password}:0:0:99999:7:::\n')
        self.assertTrue(self.grade(task))
        shadow.chmod(0o644)
        self.assertFalse(self.grade(task))

    def test_sudo_scope(self):
        task, root = self.exercise('sudo-scope', 'visudo')
        path = root / 'sudoers'
        path.write_text('%gym-audit ALL=(root) NOPASSWD: /usr/bin/systemctl is-active gym-reporter.service\n')
        self.assertFalse(self.grade(task))
        path.write_text('%gym-audit ALL=(root) /usr/bin/systemctl is-active gym-reporter.service\n')
        self.assertTrue(self.grade(task))

    def test_hosts(self):
        task, root = self.exercise('hosts')
        (root / 'hostname').write_text(task['hostname'] + '\n')
        short = task['hostname'].split('.')[0]
        (root / 'hosts').write_text(f'127.0.0.1 localhost\n{task["address"]} {task["hostname"]} {short}\n')
        self.assertTrue(self.grade(task))

    def test_timezone(self):
        task, root = self.exercise('timezone')
        path = root / 'localtime'
        path.unlink()
        path.symlink_to(Path('/usr/share/zoneinfo') / task['zone'])
        self.assertTrue(self.grade(task))

    def test_auth_log(self):
        task, root = self.exercise('auth-log')
        (root / 'auth.conf').write_text('authpriv.warning -/var/log/gym-auth-warning.log\n')
        self.assertFalse(self.grade(task))
        (root / 'auth.conf').write_text('authpriv.warning   /var/log/gym-auth-warning.log\n')
        self.assertTrue(self.grade(task))

    def test_selinux_context(self):
        task, root = self.exercise('selinux-context')
        path = root / 'file_contexts.local'
        path.write_text('/srv/.* system_u:object_r:httpd_sys_content_t:s0\n')
        self.assertFalse(self.grade(task))
        path.write_text('/srv/gym-content(/.*)? system_u:object_r:httpd_sys_content_t:s0\n')
        self.assertTrue(self.grade(task))

    def test_selinux_port(self):
        task, root = self.exercise('selinux-ports')
        (root / 'local.policy').write_text(f'port -a -p tcp -t http_port_t {task["port"]}\n')
        self.assertTrue(self.grade(task))

    def test_selinux_nfs(self):
        task, root = self.exercise('selinux-nfs')
        (root / 'local.policy').write_text('boolean -m --on use_nfs_home_dirs\n')
        self.assertTrue(self.grade(task))

    def test_firewall_source(self):
        task, root = self.exercise('firewall-source')
        (root / 'reports.xml').write_text(
            f'<zone><source address="{task["subnet"]}"/><port protocol="tcp" port="{task["port"]}"/></zone>'
        )
        self.assertTrue(self.grade(task))

    def test_lvm_layout(self):
        task, root = self.exercise('lvm-layout')
        (root / 'storage.ks').write_text(
            'part pv.01 --size=1024\nvolgroup gym_vg pv.01\n'
            f'logvol /srv/data --name=data --size={task["volume_size"]} --fstype=xfs --vgname=gym_vg\n'
            'logvol /srv/archive --name=archive --size=128 --fstype=xfs --vgname=gym_vg\n'
        )
        self.assertTrue(self.grade(task))

    def test_boot_uuid(self):
        task, root = self.exercise('boot-uuid')
        path = root / 'fstab'
        path.write_text(f'UUID={task["uuid"]} /srv/cache xfs defaults 0 0\n')
        self.assertFalse(self.grade(task))
        with path.open('a') as handle:
            handle.write('LABEL=system / xfs defaults 0 0\n')
        self.assertTrue(self.grade(task))

    def test_loop_report(self):
        task, root = self.exercise('loop-report')
        script = root / 'report.sh'
        script.write_text('#!/bin/sh\nprintf "checked: west\\n" > "$2/west.txt"\n')
        script.chmod(0o700)
        self.assertFalse(self.grade(task))
        script.write_text(
            '#!/bin/sh\nwhile IFS= read -r zone; do\n'
            '  [ -n "$zone" ] && printf "checked: %s\\n" "$zone" > "$2/$zone.txt"\n'
            'done < "$1"\n'
        )
        self.assertTrue(self.grade(task))


    def test_rpm_install(self):
        task, root = self.exercise('rpm-install', 'rpm', 'rpmkeys')
        package = root / 'repo/gym-workload-1.0-1.noarch.rpm'
        self.command('rpmkeys', '--dbpath', str(root / 'rpmdb'), '--checksig', str(package))
        rpm = cli.workbench.package_labs.rpm_command(root)
        self.command(*rpm, '-i', '--prefix', str(root / 'payload'), str(package))
        self.assertTrue(self.grade(task))

    def test_rpm_upgrade(self):
        task, root = self.exercise('rpm-upgrade', 'rpm', 'rpmkeys')
        package = root / 'repo/gym-workload-2.0-1.noarch.rpm'
        self.command('rpmkeys', '--dbpath', str(root / 'rpmdb'), '--checksig', str(package))
        self.command(*cli.workbench.package_labs.rpm_command(root), '-U',
                     '--prefix', str(root / 'payload'), str(package))
        self.assertTrue(self.grade(task))

    def test_rpm_remove(self):
        task, root = self.exercise('rpm-remove', 'rpm', 'rpmkeys')
        self.command(*cli.workbench.package_labs.rpm_command(root), '-e', 'gym-workload')
        self.assertTrue(self.grade(task))

    def test_dnf_repo(self):
        task, root = self.exercise('dnf-repo', 'dnf')
        path = root / 'repos/gym.repo'
        config = (
            '[gym-local]\nname=Gym packages\n'
            f'baseurl={(root / "repo").as_uri()}\nenabled=1\ngpgcheck=1\nrepo_gpgcheck=1\n'
            f'gpgkey={(root / "repo/KEY.asc").as_uri()}\n'
        )
        path.write_text(config.replace('repo_gpgcheck=1', 'repo_gpgcheck=0'))
        self.assertFalse(self.grade(task))
        path.write_text(config)
        self.assertTrue(self.grade(task))
        for directory in ('cache', 'persist'):
            shutil.rmtree(root / directory, ignore_errors=True)
        signature = root / 'repo/repodata/repomd.xml.asc'
        signature.write_text('broken signature\n')
        self.assertFalse(self.grade(task))

    def test_rsync_mirror(self):
        task, root = self.exercise('rsync-mirror', 'rsync')
        self.command('rsync', '-a', str(root / 'origin') + '/', str(root / 'destination'))
        self.assertFalse(self.grade(task))
        self.command('rsync', '-a', '--delete', str(root / 'origin') + '/', str(root / 'destination'))
        self.assertTrue(self.grade(task))

    def test_sftp_transfer(self):
        server = cli.workbench.transfer_labs.sftp_server()
        if server is None:
            self.skipTest('OpenSSH SFTP subsystem is unavailable')
        task, root = self.exercise('sftp-transfer', 'sftp')
        self.command('sftp', '-D', str(server), '-b', '-', input=(
            f'get "{root / "origin/parcel.txt"}" "{root / "destination/received.txt"}"\n'
        ))
        self.assertTrue(self.grade(task))

    def test_tmpfs_mount(self):
        if not cli.workbench.namespace_labs.available():
            self.skipTest('user mount namespaces are unavailable')
        task, root = self.exercise('tmpfs-mount', 'mount', 'findmnt', 'df')
        target = root / 'mount'
        (root / 'exercise.sh').write_text(
            f'mount -t tmpfs -o size={task["size"]}m,nosuid,nodev tmpfs "{target}"\n'
            f'printf "ready\\n" > "{target / "ready"}"\n'
        )
        self.assertTrue(self.grade(task))
        self.assertEqual(list(target.iterdir()), [])

    def test_ipv4_namespaces(self):
        if not cli.workbench.namespace_labs.available():
            self.skipTest('user network namespaces are unavailable')
        for operation in ('network_addrs', 'network_routing'):
            task, root = super().exercise('network-' + operation.replace('_', '-'), 'ip')
            commands = 'ip link set lo up\nip addr replace 127.0.0.1/8 dev lo\n'
            if operation == 'network_addrs':
                commands += '\n'.join(f'ip addr add {addr} dev lo' for addr in task['ipv4'])
            else:
                commands += f'ip addr add {task["ipv4"][0]} dev lo\n'
                commands += f'ip route add {task["subnet"]} dev lo src {task["ipv4"][0].split("/")[0]}'
            (root / 'exercise.sh').write_text(commands + '\n')
            self.assertTrue(self.grade(task))


    def test_process_resume(self):
        task, root = self.exercise('process-resume')
        self.addCleanup(cli.workbench.stop_workers, root.parent)
        os.kill(task['worker']['pid'], signal.SIGCONT)
        for _ in range(50):
            if self.grade(task):
                break
            time.sleep(0.01)
        self.assertTrue(self.grade(task))

    def test_acl_grader(self):
        from unittest.mock import patch
        task, _ = self.exercise('acl-inherit', 'getfacl')
        good = 'user::rwx\nuser:nobody:r-x\ndefault:user:nobody:r-x\n'
        with patch.object(cli.workbench.admin_files.subprocess, 'run') as run:
            run.return_value = subprocess.CompletedProcess([], 0, stdout=good)
            self.assertTrue(self.grade(task))
            run.return_value.stdout = good.replace(
                'user:nobody:r-x\n', 'user:nobody:r-x\t#effective:---\n', 1
            )
            self.assertFalse(self.grade(task))

    def test_offline_recovery_password(self):
        task, root = self.exercise('recovery-shadow', 'openssl')
        password = subprocess.check_output(
            ['openssl', 'passwd', '-6', '-salt', 'gymsalt', task['password']], text=True
        ).strip()
        (root / 'shadow').write_text(f'root:{password}:0:0:99999:7:::\n')
        self.assertTrue(self.grade(task))

    def test_inherited_acl(self):
        if not cli.workbench.admin_files.acl_available('/tmp'):
            self.skipTest('filesystem does not support named ACLs')
        task, root = self.exercise('acl-inherit', 'setfacl', 'getfacl')
        shared = root / 'shared'
        self.command('setfacl', '-m', 'u:nobody:r-x', str(shared))
        self.assertFalse(self.grade(task))
        self.command('setfacl', '-m', 'd:u:nobody:r-x', str(shared))
        self.assertTrue(self.grade(task))
        self.command('setfacl', '-m', 'm::---', str(shared))
        self.assertFalse(self.grade(task))

    def test_lvm_partition(self):
        task, root = self.exercise('lvm-partition', 'sfdisk')
        image = str(root / 'pv-disk.img')
        self.command('sfdisk', image, input=f'label: gpt\nsize={task["number"]}MiB\n')
        self.assertFalse(self.grade(task))
        self.command('sfdisk', image, input=f'label: gpt\nsize={task["number"]}MiB,type={cli.workbench.admin_files.LVM_TYPE}\n')
        self.assertTrue(self.grade(task))

    def test_persistent_lv_entry(self):
        task, root = self.exercise('lv-persistence')
        with (root / 'fstab').open('a') as handle:
            handle.write('/dev/mapper/gym_vg-reports /srv/reports xfs noatime,defaults 0 0\n')
        self.assertTrue(self.grade(task))

    def test_selinux_mode(self):
        task, root = self.exercise('selinux-mode')
        (root / 'config').write_text('SELINUX=enforcing\nSELINUXTYPE=targeted\n')
        self.assertTrue(self.grade(task))

    def test_nfs_export(self):
        task, root = self.exercise('nfs-export')
        (root / 'exports').write_text(f'/srv/reports {task["client"]}(ro,root_squash,sync)\n')
        self.assertTrue(self.grade(task))

    def test_tuning_profile(self):
        task, root = self.exercise('tuning-profile')
        (root / 'tuned.conf').write_text(f'[main]\ninclude=balanced\n[sysctl]\nvm.swappiness={task["number"]}\n')
        self.assertTrue(self.grade(task))

    def test_service_disable(self):
        task, root = self.exercise('unit-disable', 'systemctl')
        self.command('systemctl', f'--root={root}', 'disable', task['unit'])
        self.assertTrue(self.grade(task))

    def test_live_user_services(self):
        if not cli.workbench.user_services.available():
            self.skipTest('systemd user manager is unavailable')
        task, root = self.exercise('service-start', 'systemd-run')
        self.addCleanup(cli.workbench.user_services.cleanup, root.parent)
        self.command('systemd-run', '--user', '--unit', task['unit'], '--working-directory', str(root),
                     '/usr/bin/sleep', '1200')
        self.assertTrue(self.grade(task))
        task, root = self.exercise('service-stop', 'systemd-run')
        self.addCleanup(cli.workbench.user_services.cleanup, root.parent)
        self.command('systemctl', '--user', 'stop', task['unit'] + '.service')
        self.assertTrue(self.grade(task))

    def test_live_user_timer(self):
        if not cli.workbench.user_services.available():
            self.skipTest('systemd user manager is unavailable')
        task, root = self.exercise('timer-run', 'systemd-run')
        self.addCleanup(cli.workbench.user_services.cleanup, root.parent)
        self.command('systemd-run', '--user', '--unit', task['unit'], '--on-active=1s',
                     '/usr/bin/touch', str(root / 'fired'))
        for _ in range(60):
            if self.grade(task):
                break
            time.sleep(0.05)
        self.assertTrue(self.grade(task))


if __name__ == '__main__':
    unittest.main(verbosity=2)
