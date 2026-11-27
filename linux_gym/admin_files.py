"""Additional storage, policy and directory administration outcomes."""
import configparser
import json
import stat
import subprocess
import tempfile
from functools import lru_cache

OPERATIONS = {
    'acl_inherit', 'lvm_partition', 'lv_persistence', 'selinux_mode',
    'nfs_export', 'tuning_profile', 'unit_disable',
}
LVM_TYPE = 'E6D6D379-F507-44C2-A23C-238F2A3DF928'


@lru_cache(maxsize=2)
def acl_available(directory):
    try:
        with tempfile.TemporaryDirectory(dir=directory) as scratch:
            return subprocess.run(['setfacl', '-m', 'u:nobody:r-x', scratch],
                                  capture_output=True, timeout=3).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def prepare(task, root):
    op = task['operation']
    n = task['number']
    if op == 'acl_inherit':
        directory = root / 'shared'
        directory.mkdir(mode=0o700)
        return (f'Grant the practice account nobody read and traversal access to {directory} '
                'through a named access ACL. Make new children inherit a default named ACL for '
                'nobody with read and traversal rights. Preserve the directory owner permissions.')
    if op == 'lvm_partition':
        image = root / 'pv-disk.img'
        with image.open('wb') as disk:
            disk.truncate(128 * 1024**2)
        return (f'Create a GPT on {image} containing one {n} MiB Linux LVM partition. '
                'Use this disposable image as the disk.')
    if op == 'lv_persistence':
        (root / 'fstab').write_text('LABEL=system / xfs defaults 0 0\n')
        return (f'Add an entry in {root / "fstab"} for XFS logical volume '
                '/dev/gym_vg/reports mounted at /srv/reports with defaults and noatime, '
                'with both dump and pass set to zero. Preserve the root entry.')
    if op == 'selinux_mode':
        (root / 'config').write_text('SELINUX=disabled\nSELINUXTYPE=targeted\n')
        return (f'Restore enforcing mode on subsequent boots in the offline SELinux {root / "config"}. '
                'Keep the targeted policy.')
    if op == 'nfs_export':
        (root / 'exports').write_text('/srv/reports *(rw,no_root_squash)\n')
        task['client'] = f'192.0.2.{n}'
        return (f'Repair the offline NFS {root / "exports"} so only {task["client"]} can mount '
                '/srv/reports, with read-only access, synchronous writes and root squashing.')
    if op == 'tuning_profile':
        (root / 'tuned.conf').write_text('[main]\ninclude=throughput-performance\n'
                                        '[sysctl]\nvm.swappiness=60\n')
        return (f'Repair the offline TuneD profile {root / "tuned.conf"} to build on balanced '
                f'and set vm.swappiness to {n}.')
    units = root / 'usr/lib/systemd/system'
    wants = root / 'etc/systemd/system/multi-user.target.wants'
    units.mkdir(parents=True)
    wants.mkdir(parents=True)
    task['unit'] = f'gym-obsolete-{n}.service'
    path = units / task['unit']
    path.write_text('[Unit]\nDescription=Obsolete practice service\n'
                    '[Service]\nExecStart=/usr/bin/true\n'
                    '[Install]\nWantedBy=multi-user.target\n')
    (wants / task['unit']).symlink_to(f'/usr/lib/systemd/system/{task["unit"]}')
    return (f'Disable {task["unit"]} for future boots in the offline system rooted at {root}. '
            'Keep the service unit available for manual use.')


def normalized(path):
    return [line.split('#', 1)[0].strip() for line in path.read_text().splitlines()
            if line.split('#', 1)[0].strip()]


def check(task, root):
    op = task['operation']
    if op == 'acl_inherit':
        directory = root / 'shared'
        result = subprocess.run(['getfacl', '-cp', str(directory)],
                                capture_output=True, text=True, timeout=5)
        entries = set(result.stdout.splitlines())
        return result.returncode == 0 and {
            'user::rwx', 'user:nobody:r-x', 'default:user:nobody:r-x'
        } <= entries and not any(
            line.startswith(('user:nobody:', 'default:user:nobody:')) and 'effective:' in line
            for line in entries
        )
    if op == 'lvm_partition':
        image = root / 'pv-disk.img'
        if not stat.S_ISREG(image.lstat().st_mode) or image.stat().st_size != 128 * 1024**2:
            return False
        result = subprocess.run(['sfdisk', '--json', str(image)],
                                capture_output=True, text=True, timeout=5)
        if result.returncode:
            return False
        table = json.loads(result.stdout)['partitiontable']
        partition, = table['partitions']
        return (
            table['label'] == 'gpt' and partition['type'].upper() == LVM_TYPE
            and partition['size'] * table['sectorsize'] == task['number'] * 1024**2
        )
    if op == 'lv_persistence':
        lines = [line.split() for line in normalized(root / 'fstab')]
        fixed = ['LABEL=system', '/', 'xfs', 'defaults', '0', '0']
        if len(lines) != 2 or fixed not in lines:
            return False
        lines.remove(fixed)
        entry, = lines
        return (
            len(entry) == 6 and entry[0] in ('/dev/gym_vg/reports', '/dev/mapper/gym_vg-reports')
            and entry[1:3] == ['/srv/reports', 'xfs']
            and set(entry[3].split(',')) == {'defaults', 'noatime'} and entry[4:] == ['0', '0']
        )
    if op == 'selinux_mode':
        return set(normalized(root / 'config')) == {'SELINUX=enforcing', 'SELINUXTYPE=targeted'}
    if op == 'nfs_export':
        entry, = normalized(root / 'exports')
        path, client = entry.split()
        address, _, options = client.partition('(')
        return (path == '/srv/reports' and address == task['client'] and options.endswith(')')
                and set(options[:-1].split(',')) == {'ro', 'sync', 'root_squash'})
    if op == 'tuning_profile':
        config = configparser.ConfigParser()
        try:
            config.read_string((root / 'tuned.conf').read_text())
        except configparser.Error:
            return False
        return (
            config['main'].get('include') == 'balanced'
            and config['sysctl'].get('vm.swappiness') == str(task['number'])
        )
    service = task['unit']
    source = root / 'usr/lib/systemd/system' / service
    if not source.is_file():
        return False
    state = subprocess.run(['systemctl', f'--root={root}', 'is-enabled', service],
                           capture_output=True, text=True, timeout=5)
    return state.stdout.strip() == 'disabled'
