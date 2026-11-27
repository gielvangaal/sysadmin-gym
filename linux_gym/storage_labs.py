"""Opt-in storage labs on disposable images. Gym itself stays unprivileged."""
import os
import re
import secrets
import stat
from pathlib import Path

OPERATIONS = {'live_xfs', 'live_lvm', 'live_swap'}
SYS_BLOCK = Path('/sys/class/block')
MOUNTINFO = Path('/proc/self/mountinfo')
SWAPS = Path('/proc/swaps')
MIB = 1024**2


def kernel_path(value):
    return re.sub(r'\\([0-7]{3})', lambda match: chr(int(match[1], 8)), value)


def under(path, root):
    return Path(path).is_relative_to(root)


def mounted_filesystems():
    for line in MOUNTINFO.read_text().splitlines():
        local, _, filesystem = line.partition(' - ')
        fields = local.split()
        fs, source, *_ = filesystem.split()
        yield kernel_path(fields[4]), fs, kernel_path(source), fields[2]


def active_swaps():
    for line in SWAPS.read_text().splitlines()[1:]:
        yield kernel_path(line.split()[0])


def loop_images():
    for block in SYS_BLOCK.glob('loop*'):
        try:
            yield block.name, Path(kernel_path((block / 'loop/backing_file').read_text().strip()))
        except OSError:
            # Detached and inaccessible devices cannot be matched to the workspace.
            continue


def busy_resources(workspace):
    workspace = workspace.resolve()
    return (
        [target for target, _, _, _ in mounted_filesystems() if under(target, workspace)]
        + [name for name, image in loop_images() if image.is_relative_to(workspace)]
        + [name for name in active_swaps() if under(name, workspace)]
    )


def prepare(task, root):
    op = task['operation']
    if op == 'live_swap':
        task['size'] = 16
        return (f'Create a fully allocated 16 MiB swap file at {root / "extra.swap"} with '
                'mode 0600, initialize it, and activate it. Keep existing swap unchanged. '
                'After grading, use swapoff on this exact file before resetting.')
    mount = root / 'mounted'
    mount.mkdir()
    if op == 'live_xfs':
        images = [root / 'volume.img']
        size = 512
        goal = f'Attach {images[0]} to a new loop device, format it as XFS, and mount it at {mount}.'
    else:
        images = [root / 'disk-a.img', root / 'disk-b.img']
        size = 384
        task['vg'] = 'gym_' + secrets.token_hex(6)
        task['lv'] = 'report'
        goal = (f'Use {images[0]} and {images[1]} as loop-backed PVs. Create volume group {task["vg"]} '
                f'on the first PV with a 320 MiB logical volume {task["lv"]}. Format it as XFS '
                f'and mount it at {mount}. Extend the VG to include the second PV, then grow the logical '
                'volume to 512 MiB and grow the mounted XFS filesystem. Scope each LVM command '
                'to the exercise loop devices with --devices.')
    for image in images:
        with image.open('wb') as disk:
            disk.truncate(size * MIB)
    cleanup = 'unmount the exercise mount and detach its loop devices'
    if op == 'live_lvm':
        cleanup = f'unmount the exercise mount, deactivate only {task["vg"]}, and detach its loop devices'
    return (f'{goal} Discover each loop device by its exact backing file before using it. '
            f'After grading, {cleanup} before resetting.')


def check(task, root):
    mount = root / 'mounted'
    op = task['operation']
    if op == 'live_swap':
        swap = root / 'extra.swap'
        info = swap.lstat()
        return (
            stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600
            and info.st_size == task['size'] * MIB
            and str(swap) in set(active_swaps())
        )
    matches = [entry for entry in mounted_filesystems() if entry[0] == str(mount)]
    if len(matches) != 1 or matches[0][1] != 'xfs':
        return False
    major_minor = matches[0][3]
    loops = {block: image for block, image in loop_images() if image.parent == root}
    if op == 'live_xfs':
        return any(
            image == root / 'volume.img' and (SYS_BLOCK / block / 'dev').read_text().strip() == major_minor
            for block, image in loops.items()
        )
    expected_name = f'{task["vg"]}-{task["lv"]}'
    for block in SYS_BLOCK.glob('dm-*'):
        if (block / 'dev').read_text().strip() != major_minor:
            continue
        if (block / 'dm/name').read_text().strip() != expected_name:
            return False
        slaves = {loops.get(path.name) for path in (block / 'slaves').iterdir()}
        size = int((block / 'size').read_text()) * 512
        geometry = os.statvfs(mount)
        return (
            slaves == {root / 'disk-a.img', root / 'disk-b.img'} and size == 512 * MIB
            and geometry.f_blocks * geometry.f_frsize >= 400 * MIB
        )
    return False
