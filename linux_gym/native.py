"""Native RHEL exercises: prepare and grade the real VM, never an alternate root."""
import datetime
import os
import random
import secrets
import shlex
import subprocess
from pathlib import Path

def command(script, check=False):
    prefix=[] if os.geteuid()==0 else ['sudo']
    return subprocess.run(prefix+['/bin/bash','-e','-o','pipefail','-c',script], check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)

def render(text, values):
    # Shell blocks can contain awk and shell braces; substitute only named tokens.
    for key,value in values.items():
        text=text.replace('{'+key+'}',str(value))
    return text

def prepare(task, iface, disk):
    t=dict(task)
    today=datetime.date.today()+datetime.timedelta(days=45)
    values={'number':random.randint(11,48),'expiry':today.isoformat(),
            'expiry_days':(today-datetime.date(1970,1,1)).days,
            'password':'Gym-'+secrets.token_hex(5)+'Aa9',
            'fixture':str(Path(__file__).resolve().parents[1]/'fixtures'/'rpm'),
            'iface':iface or '', 'disk':disk or ''}
    # Explicit devices refer to real VM hardware. The VM snapshot is the rollback.
    if t.get('interface'):
        if not iface:
            raise ValueError('Specify --interface for native interface configuration')
        q=shlex.quote(iface)
        values['network_prepare']=f'nmcli con delete gym-lab 2>/dev/null || true; nmcli con add type ethernet ifname {q} con-name gym-lab ipv4.method manual ipv4.addresses 192.0.2.99/24 ipv4.never-default yes ipv6.method disabled; nmcli con up gym-lab'
    else:
        values['network_prepare']='true'
    shell_values={k:shlex.quote(str(v)) for k,v in values.items() if k!='network_prepare'}
    shell_values['network_prepare']=values['network_prepare']
    t['description']=render(t['description'],values)
    t['checks']=[render(s,shell_values) for s in t['checks']]
    setup=render(t.pop('setup'),shell_values)
    result=command(setup)
    if result.returncode:
        raise RuntimeError(f"Preparation failed for {t['id']}: {result.stderr.strip()}")
    return t

def check(task):
    return all(command(script).returncode==0 for script in task['checks'])
