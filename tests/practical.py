"""Integration tests for the isolated account, storage and recovery exercises."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from linux_gym import cli
from linux_gym.catalog import TASKS


class PracticalExercises(unittest.TestCase):
    def exercise(self, exercise_id, *tools):
        for tool in tools:
            if not shutil.which(tool):
                self.skipTest(f'{tool} is unavailable')
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.object(cli, 'WORK', Path(directory)))
        template = next(t for t in TASKS if t['id'] == exercise_id)
        task = cli.prepare(template, 1, 0, None)
        self.assertFalse(self.grade(task))
        return task, Path(task['target'])

    def grade(self, task):
        try:
            return cli.expected(task)
        except (KeyError, OSError, ValueError):
            return False

    @staticmethod
    def command(*args, **kwargs):
        subprocess.run(args, check=True, capture_output=True, text=True, timeout=15, **kwargs)

    def test_account_creation(self):
        task, root = self.exercise('practical-accounts', 'groupadd', 'useradd')
        uid = str(23100 + task['number'])
        self.command('groupadd', '--prefix', str(root), '--gid', uid, 'gymdesk')
        self.assertFalse(self.grade(task))
        self.command('useradd', '--prefix', str(root), '--uid', uid, '--gid', 'gymdesk',
                     '--no-create-home', '--no-log-init', 'gymclerk')
        self.assertTrue(self.grade(task))

    def test_supplementary_group(self):
        task, root = self.exercise('practical-membership', 'usermod')
        self.command('usermod', '--prefix', str(root), '--append', '--groups', 'gymops', 'gymrunner')
        self.assertTrue(self.grade(task))
        self.command('usermod', '--prefix', str(root), '--gid', 'gymops', 'gymrunner')
        self.assertFalse(self.grade(task))

    def test_account_expiration(self):
        task, root = self.exercise('practical-expiry', 'usermod')
        self.command('usermod', '--prefix', str(root), '--expiredate', task['expires'], 'gymrunner')
        self.assertFalse(self.grade(task))
        self.command('usermod', '--prefix', str(root), '--inactive', str(task['number'] % 10 + 3),
                     'gymrunner')
        self.assertTrue(self.grade(task))

    def test_swap_image(self):
        task, root = self.exercise('practical-swap-image', 'mkswap', 'blkid')
        image = root / 'disk.img'
        with image.open('wb') as output:
            for _ in range(task['image_size']):
                output.write(bytes(1024 ** 2))
        image.chmod(0o600)
        self.command('mkswap', '-L', task['label'], str(image))
        self.assertTrue(self.grade(task))
        image.chmod(0o644)
        self.assertFalse(self.grade(task))

    def test_xfs_image(self):
        task, root = self.exercise('practical-xfs-image', 'mkfs.xfs', 'blkid')
        image = root / 'disk.img'
        self.command('mkfs.xfs', '-L', 'wrong', '-m', f'uuid={task["uuid"]}', str(image))
        self.assertFalse(self.grade(task))
        self.command('mkfs.xfs', '-f', '-L', task['label'], '-m', f'uuid={task["uuid"]}', str(image))
        self.assertTrue(self.grade(task))

    def test_gpt_image(self):
        task, root = self.exercise('practical-gpt-image', 'sfdisk')
        image = root / 'disk.img'
        self.command('sfdisk', str(image), input='label: gpt\nsize=8MiB\n')
        self.assertFalse(self.grade(task))
        self.command('sfdisk', str(image), input=f'label: gpt\nsize={task["number"]}MiB\n')
        self.assertTrue(self.grade(task))

    def test_boot_target(self):
        task, root = self.exercise('practical-boot-target', 'systemctl')
        self.command('systemctl', f'--root={root}', 'set-default', task['default'])
        self.assertTrue(self.grade(task))

    def test_service_enablement(self):
        task, root = self.exercise('practical-service-enable', 'systemctl')
        self.command('systemctl', f'--root={root}', 'enable', task['unit'])
        self.assertTrue(self.grade(task))
        self.command('systemctl', f'--root={root}', 'disable', task['unit'])
        self.assertFalse(self.grade(task))

    def test_tmpfiles_application(self):
        task, root = self.exercise('practical-tmpfiles-apply', 'systemd-tmpfiles')
        rule = root / 'etc/tmpfiles.d/staging.conf'
        rule.write_text(f'd /var/tmp/staging 0750 - - {task["retention"]}d\n')
        self.assertFalse(self.grade(task))
        self.command('systemd-tmpfiles', f'--root={root}', '--create', 'staging.conf')
        self.assertTrue(self.grade(task))

    def test_shared_directory(self):
        task, root = self.exercise('practical-shared-directory')
        shared = root / 'shared'
        shared.chmod(0o2770)
        self.assertFalse(self.grade(task))
        shared.chmod(0o3770)
        self.assertTrue(self.grade(task))

    def test_network_secondary_address(self):
        task, root = self.exercise('recovery-network-dual')
        path = root / 'repair.nmconnection'
        with path.open('a') as profile:
            profile.write(f'address2={task["secondary"]}\n')
        self.assertTrue(self.grade(task))
        path.chmod(0o644)
        self.assertFalse(self.grade(task))

    def test_network_route(self):
        task, root = self.exercise('recovery-network-route')
        path = root / 'repair.nmconnection'
        initial = path.read_text()
        path.write_text(initial + f'route1={task["destination"]},192.0.2.254\n')
        self.assertFalse(self.grade(task))
        path.write_text(initial + f'route1={task["destination"]},{task["gateway"]},50\n')
        self.assertTrue(self.grade(task))

    def test_default_round_prioritizes_networking(self):
        for _ in range(5):
            tasks = cli.choose_tasks(7, False)
            self.assertEqual(len({task['id'] for task in tasks}), 7)
            self.assertEqual(sum(task['group'] == 'network' for task in tasks), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
