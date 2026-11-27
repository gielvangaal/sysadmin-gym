"""Validate and load installed JSON exercise packs."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ENGINE_VERSION='3.2.2'
def version(s):
    parts=str(s).split('.')
    if len(parts)!=3 or any(not p.isdigit() for p in parts):raise ValueError('Invalid version: '+str(s))
    return tuple(map(int,parts))
def load_tasks(root=ROOT):
    tasks=[]; ids=set()
    for directory in sorted((root/'modules').iterdir()):
        if not directory.is_dir():continue
        manifest_path=directory/'manifest.json'
        if not manifest_path.exists():continue
        m=json.loads(manifest_path.read_text())
        if m['name']!=directory.name:raise ValueError('Module name mismatch: '+str(directory))
        if version(ENGINE_VERSION)<version(m['engine_min']) or version(ENGINE_VERSION)>=version(m['engine_max_exclusive']):
            raise ValueError('Incompatible module: '+m['name'])
        taskfile=m.get('task_file','tasks.json')
        if taskfile!='tasks.json':raise ValueError('Unsupported task file')
        entries=json.loads((directory/taskfile).read_text())
        if not isinstance(entries,list):raise ValueError('Expected a task list: '+m['name'])
        for t in entries:
            if not isinstance(t,dict) or not all(k in t for k in ('id','group','kind','description','hint')):raise ValueError('Malformed task in '+m['name'])
            if t['group']!=m['name'] or t['id'] in ids:raise ValueError('Wrong group or duplicate task id: '+str(t['id']))
            ids.add(t['id']);tasks.append(t)
    return tasks
