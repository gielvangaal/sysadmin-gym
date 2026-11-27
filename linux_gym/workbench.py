"""RHEL practice against disposable processes, images and configuration roots."""
import json
import os
import random
import re
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from . import admin_files, namespace_labs, package_labs, storage_labs, transfer_labs, user_services

PROCESS_OPERATIONS = {'process_pause', 'process_resume', 'process_nice'}
WORKER = """
import os
import time
os.setsid()
deadline = time.monotonic() + 1800
while time.monotonic() < deadline:
    busy = time.monotonic() + 0.01
    while time.monotonic() < busy:
        pass
    time.sleep(0.19)
"""


def records(path):
    return [
        line.split('#', 1)[0].split()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    ]


def process_status(pid):
    if pid <= 1:
        raise ValueError('Invalid practice process ID')
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return fields[0], int(fields[16]), fields[19]


def launch_worker(root):
    pid = os.posix_spawn(
        sys.executable, [sys.executable, '-c', WORKER, str(root)], os.environ,
        file_actions=[
            (os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0),
            (os.POSIX_SPAWN_OPEN, 1, os.devnull, os.O_WRONLY, 0),
            (os.POSIX_SPAWN_OPEN, 2, os.devnull, os.O_WRONLY, 0),
        ],
    )
    try:
        _, nice, started = process_status(pid)
        identity = {'pid': pid, 'started': started}
        (root / '.worker.json').write_text(json.dumps(identity))
        return identity, nice
    except BaseException:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        raise


def stop_workers(workspace):
    for path in workspace.glob('ex[0-9][0-9]/.worker.json'):
        try:
            worker = json.loads(path.read_text())
            pid = worker['pid']
            with_pid = os.pidfd_open(pid)
            try:
                if process_status(pid)[2] == worker['started']:
                    command = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
                    if command[1:] == [b'-c', WORKER.encode(), os.fsencode(path.parent), b'']:
                        signal.pidfd_send_signal(with_pid, signal.SIGKILL)
                        try:
                            os.waitpid(pid, 0)
                        except ChildProcessError:
                            pass  # Reset usually runs in a separate CLI invocation.
            finally:
                os.close(with_pid)
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            continue


def prepare(task):
    root = Path(task['target'])
    root.mkdir()
    operation = task['operation']
    n = random.randint(11, 48)
    task['number'] = n
    if operation in storage_labs.OPERATIONS:
        goal = storage_labs.prepare(task, root)
    elif operation in user_services.OPERATIONS:
        goal = user_services.prepare(task, root)
    elif operation in admin_files.OPERATIONS:
        goal = admin_files.prepare(task, root)
    elif operation in namespace_labs.OPERATIONS:
        goal = namespace_labs.prepare(task, root)
    elif operation in transfer_labs.OPERATIONS:
        goal = transfer_labs.prepare(task, root)
    elif operation in package_labs.OPERATIONS:
        goal = package_labs.prepare(task, root)
    elif operation in PROCESS_OPERATIONS:
        worker, nice = launch_worker(root)
        task['worker'] = worker
        if operation == 'process_resume':
            os.kill(worker['pid'], signal.SIGSTOP)
            os.waitpid(worker['pid'], os.WUNTRACED)
            goal = f'Resume the stopped practice worker with PID {worker["pid"]}. Keep the original process running.'
        elif operation == 'process_pause':
            goal = f'Suspend the disposable worker with PID {worker["pid"]}. Keep the same process available for resuming.'
        else:
            task['nice'] = min(19, nice + 5)
            goal = f'Change the nice value of practice worker {worker["pid"]} to {task["nice"]}, keeping it running.'
    elif operation == 'login_policy':
        (root / 'login.defs').write_text('PASS_MAX_DAYS 99999\nPASS_MIN_DAYS 0\nPASS_WARN_AGE 7\n')
        goal = (f'Change the defaults in {root / "login.defs"} so new accounts have a maximum '
                f'password age of {n} days, minimum age of 2 days and a warning period of 5 days.')
    elif operation in ('account_rotate', 'recovery_shadow'):
        login = 'root' if operation == 'recovery_shadow' else 'gymintern'
        task['login'] = login
        if login == 'root':
            (root / 'console.log').write_text(
                'Offline disk image mounted for authorized maintenance. Root credential is locked.\n'
            )
        shadow = root / 'shadow'
        shadow.touch(mode=0o600)
        shadow.write_text(f'{login}:!:20000:0:99999:7:::\n')
        task['password'] = secrets.token_urlsafe(15)
        goal = (f'Restore access to {login} in the offline exercise database {shadow} with a salted SHA-512 '
                f'password hash for {task["password"]}. Flag the account to change its password '
                'at next login. Use the exercise database as your regular user.')
    elif operation == 'sudo_scope':
        (root / 'sudoers').write_text('# Offline policy for the gym-audit group\n')
        goal = (f'Write a scoped sudo rule in {root / "sudoers"} allowing group gym-audit '
                'to run /usr/bin/systemctl is-active gym-reporter.service as root, requiring '
                'authentication. Validate the offline file with visudo.')
    elif operation == 'hosts':
        task['hostname'] = f'build-{n}.gym.test'
        task['address'] = f'192.0.2.{n}'
        (root / 'hosts').write_text('127.0.0.1 localhost\n192.0.2.250 stale.gym.test\n')
        (root / 'hostname').write_text('stale.gym.test\n')
        goal = (f'Repair the offline hostname and hosts files under {root}. Set the static '
                f'hostname to {task["hostname"]}, map it and its short form to {task["address"]}, '
                'and preserve localhost. Remove the stale host record.')
    elif operation == 'timezone':
        task['zone'] = ('Europe/Amsterdam', 'America/New_York', 'Asia/Tokyo')[n % 3]
        (root / 'localtime').symlink_to('/usr/share/zoneinfo/UTC')
        goal = (f'Correct the timezone file at {root / "localtime"} for {task["zone"]} '
                'using the system timezone database. This file belongs to the offline image.')
    elif operation == 'auth_log':
        (root / 'auth.conf').write_text('authpriv.* /var/log/insecure-all.log\n')
        goal = (f'Correct {root / "auth.conf"} to route authpriv messages at warning priority '
                'and above to /var/log/gym-auth-warning.log. Use a traditional rsyslog selector.')
    elif operation == 'selinux_context':
        (root / 'audit.log').write_text(
            'type=AVC msg=audit(1726000300.012:201): avc: denied { read } '
            'for comm="httpd" path="/srv/gym-content/index.html" '
            'scontext=system_u:system_r:httpd_t:s0 tcontext=system_u:object_r:var_t:s0 tclass=file\n'
        )
        (root / 'file_contexts.local').write_text('/srv/gym-content system_u:object_r:var_t:s0\n')
        goal = (f'Inspect the SELinux denial in {root / "audit.log"}. Update the offline file '
                'context rule in file_contexts.local for /srv/gym-content and its descendants, '
                'making them readable by the web server through the standard web-content type.')
    elif operation == 'selinux_ports':
        task['port'] = 18100 + n
        (root / 'audit.log').write_text(
            f'type=AVC msg=audit(1726000400.001:202): avc: denied {{ name_bind }} '
            f'for comm="httpd" src={task["port"]} scontext=system_u:system_r:httpd_t:s0 '
            'tcontext=system_u:object_r:unreserved_port_t:s0 tclass=tcp_socket\n'
        )
        (root / 'local.policy').write_text('# Local semanage export\n')
        goal = (f'Inspect {root / "audit.log"} and add the port rule to the offline semanage '
                'export local.policy. Allow the existing web server domain to bind the affected '
                'TCP port using the standard HTTP port type.')
    elif operation == 'selinux_nfs':
        (root / 'local.policy').write_text('# Local semanage export\nboolean -m --off use_nfs_home_dirs\n')
        goal = (f'Update the persistent local boolean in {root / "local.policy"} to allow NFS '
                'home directories. Keep the policy in semanage export format.')
    elif operation == 'firewall_source':
        (root / 'reports.xml').write_text('<zone><source address="0.0.0.0/0"/><service name="http"/></zone>\n')
        task['subnet'] = f'198.51.100.{n // 16 * 16}/28'
        task['port'] = 18200 + n
        goal = (f'Repair the offline firewalld zone {root / "reports.xml"} so its only source '
                f'is {task["subnet"]} and only TCP port {task["port"]} is explicitly opened. '
                'Remove the existing HTTP service exception.')
    elif operation == 'lvm_layout':
        task['volume_size'] = n * 8
        (root / 'storage.ks').write_text(
            'part pv.01 --size=1024\nvolgroup gym_vg pv.01\n'
            'logvol /srv/data --vgname=gym_vg --name=data --size=64 --fstype=ext4\n'
        )
        goal = (f'Repair the Kickstart storage plan {root / "storage.ks"}. Keep the existing '
                f'PV and gym_vg, give data {task["volume_size"]} MiB of XFS storage mounted '
                'at /srv/data, and add a separate 128 MiB XFS LV named archive at /srv/archive.')
    elif operation == 'boot_uuid':
        task['uuid'] = str(uuid.uuid4())
        (root / 'boot.log').write_text('systemd: Dependency failed for /srv/cache.\n'
                                       'systemd: Timed out waiting for device LABEL=retired.\n')
        (root / 'blkid.txt').write_text(f'/dev/vdb1: UUID="{task["uuid"]}" TYPE="xfs" LABEL="cache"\n')
        (root / 'fstab').write_text('LABEL=retired /srv/cache xfs defaults 0 0\n'
                                   'LABEL=system / xfs defaults 0 0\n')
        goal = (f'Diagnose the failed mount in {root / "boot.log"} using blkid.txt. Replace its '
                'stale device identifier in fstab with the volume UUID, preserving the root '
                'entry and the mount type and options.')
    elif operation == 'loop_report':
        (root / 'zones').write_text('west\nnorth\n')
        goal = (f'Create an executable shell script {root / "report.sh"} accepting a file of '
                'zone names as its first argument and an output-directory path as its second. '
                'For every nonempty zone, write a separate <zone>.txt file containing '
                '"checked: <zone>" followed by a newline. The script must work with new inputs.')
    else:
        raise ValueError(f'Unknown workbench operation: {operation}')
    task['description'] = goal
    return task


def verify_script(root):
    script = root / 'report.sh'
    if not script.is_file() or not os.access(script, os.X_OK):
        return False
    for names in (['mist', 'cloud'], ['forest', '', 'drift', 'bay']):
        with tempfile.TemporaryDirectory(dir=root) as directory:
            fixture = Path(directory)
            source = fixture / 'input'
            source.write_text('\n'.join(names) + '\n')
            output = fixture / 'out'
            output.mkdir()
            result = subprocess.run([str(script), str(source), str(output)], cwd=root,
                                    capture_output=True, timeout=5)
            produced = list(output.iterdir())
            if result.returncode or any(not stat.S_ISREG(path.lstat().st_mode) for path in produced):
                return False
            files = {path.name: path.read_text() for path in produced}
            expected = {f'{name}.txt': f'checked: {name}\n' for name in names if name}
            if files != expected:
                return False
    return True


def check(task):
    root = Path(task['target'])
    operation = task['operation']
    n = task['number']
    if operation in storage_labs.OPERATIONS:
        return storage_labs.check(task, root)
    if operation in user_services.OPERATIONS:
        return user_services.check(task, root)
    if operation in admin_files.OPERATIONS:
        return admin_files.check(task, root)
    if operation in namespace_labs.OPERATIONS:
        return namespace_labs.check(task, root)
    if operation in transfer_labs.OPERATIONS:
        return transfer_labs.check(task, root)
    if operation in package_labs.OPERATIONS:
        return package_labs.check(task, root)
    if operation in PROCESS_OPERATIONS:
        worker = task['worker']
        state, nice, started = process_status(worker['pid'])
        if started != worker['started']:
            return False
        if operation == 'process_pause':
            return state in ('T', 't')
        if operation == 'process_resume':
            return state in ('R', 'S')
        return state in ('R', 'S') and nice == task['nice']
    if operation == 'login_policy':
        return sorted(records(root / 'login.defs')) == sorted([
            ['PASS_MAX_DAYS', str(n)], ['PASS_MIN_DAYS', '2'], ['PASS_WARN_AGE', '5'],
        ])
    if operation in ('account_rotate', 'recovery_shadow'):
        shadow = root / 'shadow'
        login, password, changed, minimum, maximum, warning, inactive, expiry, reserve = (
            shadow.read_text().strip().split(':')
        )
        if (
            login != task['login'] or changed != '0'
            or (minimum, maximum, warning, inactive, expiry, reserve) != ('0', '99999', '7', '', '', '')
            or stat.S_IMODE(shadow.stat().st_mode) & 0o077
        ):
            return False
        match = re.fullmatch(r'\$6\$([a-zA-Z0-9./]{1,16})\$[a-zA-Z0-9./]{86}', password)
        if not match:
            return False
        result = subprocess.run(
            ['openssl', 'passwd', '-6', '-salt', match[1], '-stdin'],
            input=task['password'] + '\n', capture_output=True, text=True, check=True, timeout=5,
        )
        return secrets.compare_digest(password, result.stdout.strip())
    if operation == 'sudo_scope':
        path = root / 'sudoers'
        grants = [' '.join(line) for line in records(path)]
        if len(grants) != 1 or not re.fullmatch(
            r'%gym-audit\s+ALL\s*=\s*\(root\)\s*(?:PASSWD:\s*)?'
            r'/usr/bin/systemctl is-active gym-reporter\.service', grants[0]
        ):
            return False
        return subprocess.run(['visudo', '-c', '-f', str(path)],
                              capture_output=True, timeout=5).returncode == 0
    if operation == 'hosts':
        hostname = task['hostname']
        mappings = records(root / 'hosts')
        return (root / 'hostname').read_text().strip() == hostname and sorted(
            (entry[0], sorted(entry[1:])) for entry in mappings
        ) == [('127.0.0.1', ['localhost']), (task['address'], sorted([hostname, hostname.split('.')[0]]))]
    if operation == 'timezone':
        reference = Path('/usr/share/zoneinfo') / task['zone']
        return (root / 'localtime').read_bytes() == reference.read_bytes()
    if operation == 'auth_log':
        return records(root / 'auth.conf') == [['authpriv.warning', '/var/log/gym-auth-warning.log']]
    if operation == 'selinux_context':
        rule, = records(root / 'file_contexts.local')
        if len(rule) != 2 or rule[1] != 'system_u:object_r:httpd_sys_content_t:s0':
            return False
        if rule[0] not in ('/srv/gym-content(/.*)?', '^/srv/gym-content(/.*)?$'):
            return False
        pattern = re.compile(rule[0])
        return (
            all(pattern.fullmatch(path) for path in ('/srv/gym-content', '/srv/gym-content/index.html',
                                                    '/srv/gym-content/sub/file'))
            and not any(pattern.fullmatch(path) for path in ('/srv', '/srv/gym-content-other', '/etc/passwd'))
        )
    if operation == 'selinux_ports':
        line, = records(root / 'local.policy')
        return line[:2] == ['port', '-a'] and line[-1:] == [str(task['port'])] and sorted(
            zip(line[2:-1:2], line[3:-1:2])
        ) == [('-p', 'tcp'), ('-t', 'http_port_t')] and len(line) == 7
    if operation == 'selinux_nfs':
        return records(root / 'local.policy') in (
            [['boolean', '-m', '--on', 'use_nfs_home_dirs']],
            [['boolean', '-m', '-1', 'use_nfs_home_dirs']],
        )
    if operation == 'firewall_source':
        import xml.etree.ElementTree as ET
        try:
            zone = ET.parse(root / 'reports.xml').getroot()
        except ET.ParseError:
            return False
        return (
            zone.tag == 'zone' and zone.get('target', 'default') == 'default'
            and all(child.tag in {'short', 'description', 'source', 'port'} for child in zone)
            and [entry.attrib for entry in zone.findall('source')] == [{'address': task['subnet']}]
            and [entry.attrib for entry in zone.findall('port')] == [{'protocol': 'tcp', 'port': str(task['port'])}]
        )
    if operation == 'lvm_layout':
        directives = records(root / 'storage.ks')
        expected = [
            ['part', 'pv.01', '--size=1024'],
            ['volgroup', 'gym_vg', 'pv.01'],
            ['logvol', '/srv/data', '--vgname=gym_vg', '--name=data',
             f'--size={task["volume_size"]}', '--fstype=xfs'],
            ['logvol', '/srv/archive', '--vgname=gym_vg', '--name=archive', '--size=128', '--fstype=xfs'],
        ]
        return sorted(sorted(line) for line in directives) == sorted(sorted(line) for line in expected)
    if operation == 'boot_uuid':
        return sorted(records(root / 'fstab')) == sorted([
            [f'UUID={task["uuid"]}', '/srv/cache', 'xfs', 'defaults', '0', '0'],
            ['LABEL=system', '/', 'xfs', 'defaults', '0', '0'],
        ])
    if operation == 'loop_report':
        return verify_script(root)
    return False
