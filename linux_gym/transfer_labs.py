"""Disposable data copies with rsync and the OpenSSH SFTP subsystem."""
import stat
from pathlib import Path

OPERATIONS = {'rsync_mirror', 'sftp_transfer'}


def sftp_server():
    for path in (Path('/usr/libexec/openssh/sftp-server'), Path('/usr/lib/openssh/sftp-server')):
        if path.is_file():
            return path
    return None


def prepare(task, root):
    source = root / 'origin'
    source.mkdir()
    dest = root / 'destination'
    dest.mkdir()
    n = task['number']
    if task['operation'] == 'sftp_transfer':
        (source / 'parcel.txt').write_text(f'practice parcel {n}\n')
        return (f'Transfer {source / "parcel.txt"} to {dest / "received.txt"} using SFTP. Use '
                f'sftp -D {sftp_server()} to connect to the disposable local subsystem.')
    (source / 'metadata').mkdir()
    (source / 'metadata/manifest').write_text(f'station {n}\n')
    (source / 'metadata/manifest').chmod(0o640)
    (source / 'current').symlink_to('metadata/manifest')
    (dest / 'obsolete').write_text('stale\n')
    (dest / 'metadata').mkdir()
    (dest / 'metadata/manifest').write_text('old data\n')
    return (f'Mirror the contents of {source} into {dest}. Keep relative symlinks and file permissions '
            'and remove destination entries absent from the source. Preserve the source.')


def check(task, root):
    source = root / 'origin'
    dest = root / 'destination'
    n = task['number']
    if task['operation'] == 'sftp_transfer':
        received = dest / 'received.txt'
        return (stat.S_ISREG(received.lstat().st_mode)
                and received.read_text() == f'practice parcel {n}\n'
                and (source / 'parcel.txt').read_text() == received.read_text())
    expected = {'metadata', 'metadata/manifest', 'current'}
    for folder in (source, dest):
        if {str(path.relative_to(folder)) for path in folder.rglob('*')} != expected:
            return False
        link = folder / 'current'
        marker = folder / 'metadata/manifest'
        if (not link.is_symlink() or link.readlink() != Path('metadata/manifest')
                or not stat.S_ISREG(marker.lstat().st_mode)
                or stat.S_IMODE(marker.stat().st_mode) != 0o640
                or marker.read_text() != f'station {n}\n'):
            return False
    return True
