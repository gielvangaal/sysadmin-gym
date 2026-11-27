"""Independent, unprivileged practical exercises with outcome-based checks."""
import json
import os
import random
import stat
import subprocess
import uuid
from datetime import date, timedelta
from pathlib import Path

MIB = 1024 ** 2
LINUX_PARTITION = '0FC63DAF-8483-4772-8E79-3D69D8477DE4'
ACCOUNT_OPS = {'accounts', 'membership', 'expiry'}
STORAGE_OPS = {'swap_image', 'xfs_image', 'gpt_image'}


def write_account_database(directory, existing_user):
    directory.mkdir()
    passwd = 'root:x:0:0:root:/root:/bin/bash\n'
    group = 'root:x:0:\ngymops:x:22000:\n'
    shadow = 'root:!:20000:0:99999:7:::\n'
    if existing_user:
        passwd += 'gymrunner:x:22001:22001::/home/gymrunner:/bin/bash\n'
        group += 'gymrunner:x:22001:\n'
        shadow += 'gymrunner:!:20000:0:99999:7:::\n'
    (directory / 'passwd').write_text(passwd)
    (directory / 'group').write_text(group)
    shadow_file = directory / 'shadow'
    shadow_file.touch(mode=0o600)
    shadow_file.write_text(shadow)


def account_entry(root, table, name):
    entries = [
        entry for line in (root / 'etc' / table).read_text().splitlines()
        if (entry := line.split(':'))[0] == name
    ]
    entry, = entries
    return entry


def check_accounts(task, root):
    op = task['operation']
    if account_entry(root, 'passwd', 'root') != ['root', 'x', '0', '0', 'root', '/root', '/bin/bash']:
        return False
    if op == 'accounts':
        uid = str(23100 + task['number'])
        return (
            account_entry(root, 'group', 'gymdesk')[2] == uid
            and account_entry(root, 'passwd', 'gymclerk')[2:4] == [uid, uid]
            and account_entry(root, 'shadow', 'gymclerk')[1].startswith(('!', '*'))
        )
    if op == 'membership':
        return (
            account_entry(root, 'passwd', 'gymrunner')[2:4] == ['22001', '22001']
            and 'gymrunner' in account_entry(root, 'group', 'gymops')[3].split(',')
            and account_entry(root, 'group', 'gymops')[2] == '22000'
        )
    expires = date.fromisoformat(task['expires'])
    inactive = str(task['number'] % 10 + 3)
    shadow = account_entry(root, 'shadow', 'gymrunner')
    return shadow[1] == '!' and shadow[6:8] == [inactive, str((expires - date(1970, 1, 1)).days)]


def check_storage(task, image):
    info = image.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != task['image_size'] * MIB:
        return False
    op = task['operation']
    if op == 'gpt_image':
        result = subprocess.run(['sfdisk', '--json', str(image)], capture_output=True, text=True, timeout=5)
        if result.returncode:
            return False
        table = json.loads(result.stdout)['partitiontable']
        partitions = table['partitions']
        return (
            table['label'] == 'gpt'
            and len(partitions) == 1
            and partitions[0]['type'].upper() == LINUX_PARTITION
            and partitions[0]['size'] * table['sectorsize'] == task['number'] * MIB
        )
    result = subprocess.run(['blkid', '-p', '-o', 'export', str(image)], capture_output=True, text=True, timeout=5)
    if result.returncode:
        return False
    fields = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if fields.get('LABEL') != task['label']:
        return False
    if op == 'xfs_image':
        return fields.get('TYPE') == 'xfs' and fields.get('UUID') == task['uuid']
    return (
        fields.get('TYPE') == 'swap'
        and stat.S_IMODE(info.st_mode) == 0o600
        and info.st_blocks * 512 >= info.st_size
    )


def image_link_matches(root, link, unit):
    if not link.is_symlink():
        return False
    # Absolute symlinks in a system image resolve inside that image.
    target = Path(os.readlink(link))
    target = root / target.relative_to('/') if target.is_absolute() else link.parent / target
    return target.resolve() == root / 'usr/lib/systemd/system' / unit


def prepare(t):
    p=Path(t['target'])
    p.mkdir()
    n=random.randint(20,90)
    t['number']=n
    op=t['operation']
    if op=='script':
        (p/'input').write_text('alpha:12\nbeta:45\ngamma:2\n')
        desc=f'Create executable {p}/report.sh accepting a colon-separated input file as its first argument. Print the names whose numeric second field is greater than {n}, one per line in input order. The script must work with new inputs.'
    elif op=='links':
        (p/'original').write_text(f'payload {n}\n')
        desc=f'Create a hard link {p}/backup and a relative symbolic link {p}/current pointing to original. Preserve the original.'
    elif op=='retention':
        for i in range(6):
            f=p/f'log-{i}.log'
            f.write_text(str(i))
            os.utime(f,(100000+i*86400,100000+i*86400))
        desc=f'Keep only the three newest logs in {p}, based on modification time. Preserve their contents.'
    elif op=='sshkey':
        desc=f'Generate an Ed25519 SSH key pair at {p}/id_ed25519 without a passphrase for this disposable exercise. Restrict private key permissions to its owner.'
    elif op=='acl':
        (p/'shared').write_text('shared data\n')
        (p/'shared').chmod(0o600)
        desc=f'Grant the nobody account read-only access to {p}/shared using an ACL, without granting access to other users or the owning group.'
    elif op=='compress':
        (p/'data').write_text(f'payload {n}\n'*100)
        desc=f'Create {p}/data.xz containing a lossless xz-compressed copy of data. Preserve the original.'
    elif op=='sed':
        (p/'app.conf').write_text('enabled=no\nport=9999\n# keep this comment\n')
        desc=f'Repair {p}/app.conf: enable the application and set port to {18000+n}. Preserve the comment and avoid duplicate settings.'
    elif op=='fifo':
        desc=f'Create a named pipe at {p}/queue accessible only to its owner (read and write).'
    elif op=='sparse':
        desc=f'Create a sparse regular file {p}/disk.img of exactly {n} MiB, consuming less than 1 MiB of actual disk space.'
    elif op=='checksum':
        (p/'payload').write_text(f'payload {n}\n')
        desc=f'Create a SHA-256 checksum manifest {p}/SHA256SUMS for payload using a relative filename, so it can be verified from {p}.'
    elif op=='rpm':
        desc=f'Export the installed bash RPM package name, version and release as NAME VERSION RELEASE on one line in {p}/package.txt.'
    elif op=='cron':
        desc=f'Create a user crontab fragment {p}/job (do not install it) that runs /usr/bin/true at minute {n%60} of every hour.'
    elif op in ACCOUNT_OPS:
        write_account_database(p / 'etc', existing_user=op != 'accounts')
        if op == 'accounts':
            uid = 23100 + n
            desc = (f'Create group gymdesk with GID {uid} and locked user gymclerk with UID {uid} '
                    'and primary group gymdesk. Skip home directory creation and login log initialization.')
        elif op == 'membership':
            desc = 'Add gymrunner to the supplementary group gymops. Preserve its primary group and UID.'
        else:
            t['expires'] = (date.today() + timedelta(days=n)).isoformat()
            desc = (f'Set gymrunner to expire on {t["expires"]} and disable access '
                    f'{n % 10 + 3} days after password expiry. Keep the current password lock.')
        desc += f' Use the account database under {p} with the tools\' prefix option, as your regular user.'
    elif op in STORAGE_OPS:
        image = p / 'disk.img'
        t['image_size'] = 512 if op == 'xfs_image' else 128 if op == 'gpt_image' else 8 + n % 8
        t['label'] = f'gym{n}'
        if op == 'swap_image':
            desc = (f'Prepare {image} as a fully allocated {t["image_size"]} MiB swap file, '
                    f'with mode 0600 and label {t["label"]}. Leave it inactive.')
        else:
            with image.open('wb') as disk:
                disk.truncate(t['image_size'] * MIB)
            if op == 'gpt_image':
                desc = f'Create a GPT on {image} with exactly one {n} MiB Linux filesystem partition.'
            else:
                t['uuid'] = str(uuid.uuid4())
                desc = f'Format {image} as XFS with label {t["label"]} and UUID {t["uuid"]}.'
            desc += ' Work directly on the practice image file.'
    elif op in ('boot_target', 'service_enable'):
        units = p / 'usr/lib/systemd/system'
        units.mkdir(parents=True)
        for unit in ('graphical.target', 'multi-user.target'):
            (units / unit).write_text(f'[Unit]\nDescription=Practice {unit}\n')
        if op == 'boot_target':
            default = p / 'etc/systemd/system/default.target'
            default.parent.mkdir(parents=True)
            t['default'] = 'multi-user.target' if n % 2 else 'graphical.target'
            wrong = 'graphical.target' if n % 2 else 'multi-user.target'
            default.symlink_to(f'/usr/lib/systemd/system/{wrong}')
            desc = f'Set the default boot target to {t["default"]} for the offline system rooted at {p}.'
        else:
            t['unit'] = f'gym-audit-{n}.service'
            (units / t['unit']).write_text(
                '[Unit]\nDescription=Practice audit job\n'
                '[Service]\nType=oneshot\nExecStart=/usr/bin/true\n'
                '[Install]\nWantedBy=multi-user.target\n'
            )
            desc = f'Enable {t["unit"]} at multi-user.target in the offline system rooted at {p}.'
    elif op == 'tmpfiles_apply':
        config = p / 'etc/tmpfiles.d'
        config.mkdir(parents=True)
        (config / 'staging.conf').write_text('d /var/tmp/staging 0777 - - -\n')
        t['retention'] = n % 14 + 1
        desc = (f'Repair {config / "staging.conf"} so /var/tmp/staging has mode 0750 '
                f'and files are eligible for cleanup after {t["retention"]} days. '
                f'Apply the creation rule with systemd-tmpfiles in the offline root {p}.')
    elif op == 'shared_directory':
        shared = p / 'shared'
        shared.mkdir(mode=0o755)
        desc = (f'Configure {shared} for group collaboration. Give the owner and group full '
                'directory access, deny access to others, inherit the directory group on new '
                'entries, and restrict entry deletion to its owner or the directory owner.')
    else:
        raise ValueError('Unknown practical operation')
    t['description']=desc
    return t

def check(t):
    p=Path(t['target']); n=t['number']; op=t['operation']
    if op in ACCOUNT_OPS:
        return check_accounts(t, p)
    if op in STORAGE_OPS:
        return check_storage(t, p / 'disk.img')
    if op == 'boot_target':
        return image_link_matches(p, p / 'etc/systemd/system/default.target', t['default'])
    if op == 'service_enable':
        link = p / 'etc/systemd/system/multi-user.target.wants' / t['unit']
        return image_link_matches(p, link, t['unit'])
    if op == 'tmpfiles_apply':
        rule, = [
            line.split('#', 1)[0].split()
            for line in (p / 'etc/tmpfiles.d/staging.conf').read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')
        ]
        staged = (p / 'var/tmp/staging').lstat().st_mode
        return (
            rule[:2] == ['d', '/var/tmp/staging']
            and int(rule[2], 8) == 0o750
            and rule[3:6] == ['-', '-', f'{t["retention"]}d']
            and rule[6:] in ([], ['-'])
            and stat.S_ISDIR(staged)
            and stat.S_IMODE(staged) == 0o750
        )
    if op == 'shared_directory':
        mode = (p / 'shared').lstat().st_mode
        return stat.S_ISDIR(mode) and stat.S_IMODE(mode) == 0o3770
    if op=='script':
        script=p/'report.sh'
        if not script.is_file() or not os.access(script,os.X_OK):return False
        for rows in ([('one',n+1),('two',n),('three',n+5)],[('x',n-1),('y',n+2)]):
            f=p/'check-input'
            f.write_text(''.join(f'{name}:{v}\n' for name,v in rows))
            r=subprocess.run([str(script),str(f)],capture_output=True,text=True,timeout=5)
            if r.returncode or r.stdout.splitlines()!=[name for name,v in rows if v>n]:return False
        return True
    if op=='links':
        return (p/'original').read_text()==f'payload {n}\n' and not (p/'backup').is_symlink() and os.path.samefile(p/'original',p/'backup') and (p/'current').is_symlink() and os.readlink(p/'current')=='original'
    if op=='retention':
        return sorted(x.name for x in p.iterdir())==[f'log-{i}.log' for i in range(3,6)] and all((p/f'log-{i}.log').read_text()==str(i) for i in range(3,6))
    if op=='sshkey':
        key=p/'id_ed25519'
        if not key.is_file() or key.stat().st_mode&0o077:return False
        r=subprocess.run(['ssh-keygen','-y','-P','','-f',str(key)],capture_output=True,text=True,timeout=5)
        return r.returncode==0 and r.stdout.startswith('ssh-ed25519 ') and r.stdout.split()[:2]==(p/'id_ed25519.pub').read_text().split()[:2]
    if op=='acl':
        r=subprocess.run(['getfacl','-cp',str(p/'shared')],capture_output=True,text=True)
        return r.returncode==0 and {'user:nobody:r--','group::---','other::---','mask::r--'}<=set(r.stdout.splitlines())
    if op=='compress':
        import lzma
        return (p/'data').read_text()==f'payload {n}\n'*100 and lzma.decompress((p/'data.xz').read_bytes())==(p/'data').read_bytes()
    if op=='sed':
        return sorted((p/'app.conf').read_text().splitlines())==sorted(['enabled=yes',f'port={18000+n}','# keep this comment'])
    if op=='fifo':
        s=(p/'queue').lstat()
        return stat.S_ISFIFO(s.st_mode) and stat.S_IMODE(s.st_mode)==0o600
    if op=='sparse':
        s=(p/'disk.img').lstat()
        return stat.S_ISREG(s.st_mode) and s.st_size==n*1024**2 and s.st_blocks*512<1024**2
    if op=='checksum':
        import hashlib
        fields=(p/'SHA256SUMS').read_text().strip().split()
        return len(fields)==2 and fields[0]==hashlib.sha256(f'payload {n}\n'.encode()).hexdigest() and fields[1] in ('payload','*payload')
    if op=='rpm':
        r=subprocess.run(['rpm','-q','--qf','%{NAME} %{VERSION} %{RELEASE}\n','bash'],capture_output=True,text=True)
        return r.returncode==0 and (p/'package.txt').read_text().strip()==r.stdout.strip()
    if op=='cron':
        return (p/'job').read_text().split()==[str(n%60),'*','*','*','*','/usr/bin/true']
    return False
