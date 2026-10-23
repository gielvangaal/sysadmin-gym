"""Safe, offline module update mechanism. Does not edit runtime data/config."""
import json, shutil, tarfile, tempfile, uuid
from pathlib import Path
from .module_loader import ROOT, ENGINE_VERSION, version, load_tasks

def _name(value):
    if not isinstance(value,str) or not value or any(ch not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for ch in value):
        raise ValueError('Invalid module name')
    return value

def install(archive, root=ROOT):
    root=Path(root);archive=Path(archive)
    if (root/'session.json').exists():raise ValueError('Finish/reset current session before updating modules')
    with tempfile.TemporaryDirectory(prefix='sysadmin-gym-update-') as tmp:
        tmp=Path(tmp)
        with tarfile.open(archive,'r:gz') as tar:
            members=tar.getmembers()
            if len(members)>10:raise ValueError('Too many archive members')
            paths={m.name for m in members}
            if paths!={'manifest.json','tasks.json'}:raise ValueError('Only manifest.json and tasks.json allowed')
            if any(not m.isfile() or m.size>2_000_000 for m in members):raise ValueError('Unsafe archive member')
            for m in members:
                with tar.extractfile(m) as source, (tmp/m.name).open('wb') as dest:shutil.copyfileobj(source,dest)
        manifest=json.loads((tmp/'manifest.json').read_text())
        name=_name(manifest['name']);version(manifest['version'])
        if manifest.get('task_file')!='tasks.json':raise ValueError('Expected tasks.json')
        if version(ENGINE_VERSION)<version(manifest['engine_min']) or version(ENGINE_VERSION)>=version(manifest['engine_max_exclusive']):
            raise ValueError('Incompatible engine version')
        tasks=json.loads((tmp/'tasks.json').read_text())
        if not isinstance(tasks,list) or not tasks:raise ValueError('Empty/invalid task list')
        olddir=root/'modules'/name
        if olddir.exists():
            old=json.loads((olddir/'manifest.json').read_text())
            if version(manifest['version'])<=version(old['version']):raise ValueError('New version must exceed installed version')
        others={t['id'] for t in load_tasks(root) if t['group']!=name}
        seen=set()
        for t in tasks:
            if not isinstance(t,dict) or not all(k in t for k in ('id','group','kind','description','hint')):raise ValueError('Malformed exercise')
            if t['group']!=name or t['id'] in seen or t['id'] in others:raise ValueError('Duplicate ID or incorrect group')
            # Existing engine supports these kinds; new kinds require an engine upgrade.
            supported={t['kind'] for t in load_tasks(root)}
            if t['kind'] not in supported:raise ValueError('Unknown exercise kind: '+str(t['kind'])+' (engine upgrade required)')
            seen.add(t['id'])
        newdir=root/'modules'/('.'+name+'.staged-'+uuid.uuid4().hex[:8])
        backup=None
        try:
            shutil.copytree(tmp,newdir)
            if olddir.exists():
                backup=root/'module-backups'/name/(old['version']+'-'+uuid.uuid4().hex[:8])
                backup.parent.mkdir(parents=True,exist_ok=True)
                olddir.rename(backup)
            newdir.rename(olddir)
            load_tasks(root)
        except Exception:
            if newdir.exists():shutil.rmtree(newdir)
            if backup and backup.exists():
                if olddir.exists():shutil.rmtree(olddir)
                backup.rename(olddir)
            elif olddir.exists() and not backup:shutil.rmtree(olddir)
            raise
        print(f'Installed module {name} v{manifest["version"]}'+(f'; previous version saved at {backup}' if backup else ''))

def rollback(name,root=ROOT):
    root=Path(root);name=_name(name)
    if (root/'session.json').exists():raise ValueError('Finish/reset current session first')
    olddir=root/'modules'/name;parent=root/'module-backups'/name
    backups=sorted((p for p in parent.iterdir() if p.is_dir()),key=lambda p:p.stat().st_mtime,reverse=True) if parent.exists() else []
    if not backups:raise ValueError('No previous module version found')
    backup=backups[0];discard=root/'module-backups'/name/('replaced-'+uuid.uuid4().hex[:8])
    if olddir.exists():olddir.rename(discard)
    try:
        backup.rename(olddir);load_tasks(root)
    except Exception:
        if olddir.exists():olddir.rename(backup)
        if discard.exists():discard.rename(olddir)
        raise
    print(f'Restored {name} from {backup.name}; replaced version kept at {discard}')
