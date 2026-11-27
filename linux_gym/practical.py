"""Independent, unprivileged practical exercises with outcome-based checks."""
import os
import random
import stat
import subprocess
from pathlib import Path

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
    else:
        raise ValueError('Unknown practical operation')
    t['description']=desc
    return t

def check(t):
    p=Path(t['target']); n=t['number']; op=t['operation']
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
