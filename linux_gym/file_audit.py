"""Isolated file and capacity exercises; no privileged changes."""
import os
from pathlib import Path
import stat
import time

def prepare(t):
    root=Path(t['target'])
    root.mkdir()
    now=time.time()
    records=[]
    for i,(name,size,age,mode) in enumerate([
        ('app/current.log',4096,1,0o644),
        ('app/old.log',65536,14,0o666),
        ('app/archive.log',32768,30,0o640),
        ('cache/data.bin',131072,2,0o666),
        ('cache/old.bin',16384,21,0o600),
        ('db/export.sql',262144,10,0o640),
        ('db/config.ini',1024,1,0o644),
        ('backup/weekly.tar',524288,8,0o600),
        ('backup/old.log',8192,45,0o644),
    ]):
        p=root/name
        p.parent.mkdir(exist_ok=True)
        p.write_bytes(bytes([65+i])*size)
        p.chmod(mode)
        os.utime(p,(now-age*86400,now-age*86400))
        records.append(dict(path=str(p),size=size,age=age,mode=mode))
    t['fixture']=records
    op=t['operation']; threshold=t.get('threshold',0); result=t['result']
    if op=='size':
        wanted=[r['path'] for r in records if r['size']>threshold*1024]
        instruction=f'Find regular files strictly larger than {threshold} KiB.'
    elif op=='old_logs':
        wanted=[r['path'] for r in records if r['path'].endswith('.log') and r['age']>threshold]
        instruction=f'Find regular .log files modified more than {threshold} days ago.'
    elif op=='old_large':
        wanted=[r['path'] for r in records if r['age']>t['days'] and r['size']>threshold*1024]
        instruction=f'Find regular files larger than {threshold} KiB and modified more than {t["days"]} days ago.'
    elif op=='writable':
        wanted=[r['path'] for r in records if r['mode']&2]
        instruction='Find regular files writable by everyone (the other-write permission bit is set).'
    elif op=='top':
        wanted=[r['path'] for r in sorted(records,key=lambda r:-r['size'])[:threshold]]
        instruction=f'Identify the {threshold} largest regular files by apparent size, largest first.'
    elif op=='directory_usage':
        totals={}
        for r in records:
            parent=str(Path(r['path']).parent)
            totals[parent]=totals.get(parent,0)+r['size']
        wanted=sorted(totals,key=lambda p:(-totals[p],p))[:threshold]
        instruction=f'Identify the {threshold} immediate subdirectories with the largest combined apparent byte size of regular files, largest first. Ignore directory metadata.'
    elif op=='cleanup':
        wanted=[r['path'] for r in records if r['age']>threshold and r['path'].endswith('.log')]
        instruction=f'Remove only regular .log files modified more than {threshold} days ago. Preserve every other file.'
    else:
        raise ValueError('Unknown file audit operation')
    t['wanted']=wanted
    suffix='' if op=='cleanup' else f' Write absolute paths, one per line, to {result}.'+(' Sort alphabetically.' if op not in ('top','directory_usage') else '')
    t['description']=f'An application storage audit is required under {root}. {instruction}{suffix}'
    return t

def check(t):
    records=t['fixture']; wanted=t['wanted']; op=t['operation']
    for r in records:
        p=Path(r['path'])
        if op=='cleanup' and r['path'] in wanted:
            if p.exists() or p.is_symlink():return False
        elif not p.is_file() or p.is_symlink() or p.stat().st_size!=r['size'] or stat.S_IMODE(p.stat().st_mode)!=r['mode']:
            return False
    if op=='cleanup':return True
    result=Path(t['result'])
    if not result.is_file():return False
    actual=result.read_text().splitlines()
    return actual==(wanted if op in ('top','directory_usage') else sorted(wanted))
