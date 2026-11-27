"""Verify storage outcomes and reset protection with kernel-state fixtures."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from practical import ExerciseCase, cli

labs = cli.workbench.storage_labs


class StorageLabTests(ExerciseCase):
    def fixture(self, exercise_id):
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        workspace = directory / 'workspace'
        workspace.mkdir()
        sysblock = directory / 'block'
        sysblock.mkdir()
        mountinfo = directory / 'mountinfo'
        mountinfo.touch()
        swaps = directory / 'swaps'
        swaps.write_text('Filename Type Size Used Priority\n')
        self.enterContext(patch.object(labs, 'SYS_BLOCK', sysblock))
        self.enterContext(patch.object(labs, 'MOUNTINFO', mountinfo))
        self.enterContext(patch.object(labs, 'SWAPS', swaps))
        self.enterContext(patch.object(cli, 'WORK', workspace))
        self.enterContext(patch.object(cli, 'SESSION', directory / 'missing-session.json'))
        template = next(task for task in cli.TASKS if task['id'] == exercise_id)
        task = cli.prepare(template, 1, 0, None)
        self.assertFalse(self.grade(task))
        return task, Path(task['target'])

    @staticmethod
    def attach(device, image):
        block = labs.SYS_BLOCK / device
        (block / 'loop').mkdir(parents=True)
        (block / 'loop/backing_file').write_text(str(image) + '\n')
        (block / 'dev').write_text('7:' + device.removeprefix('loop'))

    def test_xfs_mount_is_bound_to_practice_image(self):
        task, root = self.fixture('storage-live-xfs')
        self.attach('loop7', root / 'other.img')
        labs.MOUNTINFO.write_text(f'41 40 7:7 / {root / "mounted"} rw - xfs /dev/loop7 rw\n')
        self.assertFalse(self.grade(task))
        (labs.SYS_BLOCK / 'loop7/loop/backing_file').write_text(str(root / 'volume.img'))
        self.assertTrue(self.grade(task))
        with self.assertRaisesRegex(SystemExit, 'Release active practice storage'):
            cli.reset(None)
        self.assertTrue((root / 'volume.img').exists())

    def test_lvm_requires_both_pvs_and_grown_filesystem(self):
        task, root = self.fixture('storage-live-lvm')
        self.attach('loop8', root / 'disk-a.img')
        self.attach('loop9', root / 'disk-b.img')
        block = labs.SYS_BLOCK / 'dm-4'
        (block / 'dm').mkdir(parents=True)
        (block / 'slaves').mkdir()
        (block / 'dm/name').write_text(task['vg'] + '-' + task['lv'])
        (block / 'dev').write_text('253:4')
        (block / 'size').write_text(str(512 * 1024**2 // 512))
        (block / 'slaves/loop8').symlink_to(labs.SYS_BLOCK / 'loop8')
        labs.MOUNTINFO.write_text(f'41 40 253:4 / {root / "mounted"} rw - xfs /dev/dm-4 rw\n')
        with patch.object(labs.os, 'statvfs') as geometry:
            geometry.return_value = SimpleNamespace(f_blocks=131072, f_frsize=4096)
            self.assertFalse(self.grade(task))
            (block / 'slaves/loop9').symlink_to(labs.SYS_BLOCK / 'loop9')
            self.assertTrue(self.grade(task))
            geometry.return_value.f_blocks = 81920
            self.assertFalse(self.grade(task))

    def test_active_swap_and_reset_guard(self):
        task, root = self.fixture('storage-live-swap')
        swap = root / 'extra.swap'
        with swap.open('wb') as handle:
            handle.truncate(16 * 1024**2)
        swap.chmod(0o600)
        self.assertFalse(self.grade(task))
        labs.SWAPS.write_text(f'Filename Type Size Used Priority\n{swap} file 16380 0 -2\n')
        self.assertTrue(self.grade(task))
        self.assertIn(str(swap), labs.busy_resources(root.parent))
        with self.assertRaisesRegex(SystemExit, 'Release active practice storage'):
            cli.reset(None)

    def test_default_round_excludes_storage(self):
        for _ in range(4):
            self.assertNotIn('storage', {task['group'] for task in cli.choose_tasks(7, False)})


if __name__ == '__main__':
    unittest.main(verbosity=2)
