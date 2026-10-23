"""Run in project root: python3 tests/smoke.py. No root/network changes."""
import os, sys, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from linux_gym.catalog import TASKS
from linux_gym import cli
assert len(TASKS)>=100
assert len({x['id'] for x in TASKS})==len(TASKS)
assert len({x['kind'] for x in TASKS})>=40
assert not cli.SESSION.exists(), 'Sluit bestaande oefensessie voor smoke-test'
try:
    p=subprocess.run([str(ROOT/'gym.sh'),'start','--count','7'],capture_output=True,text=True)
    assert p.returncode==0, p.stdout+p.stderr
    ss=cli.load_json(cli.SESSION,None)
    assert ss and len(ss['tasks'])==7
    assert all('description' in t and t['description'] for t in ss['tasks'])
    p=subprocess.run([str(ROOT/'gym.sh'),'hint','1'],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    p=subprocess.run([str(ROOT/'gym.sh'),'check'],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    print('PASS: catalog, start, 7 tasks, hint, check')
finally:
    p=subprocess.run([str(ROOT/'gym.sh'),'reset'],capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr
    assert not cli.SESSION.exists()
print('PASS: reset')
